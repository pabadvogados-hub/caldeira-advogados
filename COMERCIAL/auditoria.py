"""
AUDITORIA DO ATENDIMENTO (Atende Direito) - rotina semanal.

Mede, por conversa de lead:
- tempo da PRIMEIRA RESPOSTA (media, mediana, 90% das conversas, dentro da meta);
- conversas SEM RESPOSTA;
- leads por ORIGEM (campanha/canal) com % qualificados e % fechados;
- por ATENDENTE (SDR) e por CLOSER: conversas, tempo de resposta, qualificados, fechados (quem fecha mais);
- FLUXO SEGUIDO: qualificado sem reuniao, reuniao sem resultado registrado, perdido sem motivo;
- chegada de leads por faixa de horario (para escala de atendimento).

De onde vem o dado (na ordem):
1. --csv EXPORT.csv  (planilha exportada do Atende Direito ou montada pela equipe; colunas em docs/POP_COMERCIAL.md)
2. API FLOW do Atende Direito (ATENDE_DIREITO_FLOW_TOKEN, https://api.atendedireito.app): conversas + mensagens
   com horario e tipo do remetente -> mede tudo. Nomes de campo tratados de forma defensiva: conferir no 1o uso.
3. API antiga (ATENDE_DIREITO_TOKEN, app.atendedireito.com.br): so lista contatos; NAO traz o historico das
   mensagens, entao NAO da para medir tempo de resposta. O relatorio sai parcial e avisa.
4. --exemplo: dados ficticios (exemplos/ATENDIMENTO_EXEMPLO.csv).
Somente leitura: nada e enviado nem alterado no Atende Direito.
"""
import csv
import json
import os
import statistics
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

import requests

import ambiente
from config_comercial import ATENDIMENTO
from html_util import cartoes, lista, numero, pagina, tabela

EXEMPLO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exemplos', 'ATENDIMENTO_EXEMPLO.csv')

ALIASES = {
    'contato': ['contato', 'nome', 'cliente', 'lead'],
    'telefone': ['telefone', 'phone', 'whatsapp', 'celular'],
    'origem': ['origem', 'canal', 'fonte', 'campanha', 'utm_source'],
    'atendente': ['atendente', 'sdr', 'responsavel', 'agente'],
    'closer': ['closer'],
    'inicio': ['primeira_mensagem', 'inicio', 'data_entrada', 'criado_em', 'created_at', 'data'],
    'resposta': ['primeira_resposta', 'respondido_em', 'first_response', 'resposta'],
    'qualificado': ['qualificado'],
    'reuniao': ['reuniao_agendada', 'reuniao'],
    'fechou': ['fechou', 'contrato', 'ganho'],
    'etiquetas': ['etiquetas', 'tags', 'etapa', 'status'],
    'motivo_perda': ['motivo_perda', 'motivo'],
}
FORMATOS = ('%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%y %H:%M')


def _norm(txt):
    txt = unicodedata.normalize('NFKD', str(txt or '')).encode('ascii', 'ignore').decode().lower().strip()
    return txt.replace(' ', '_').replace('-', '_')


def _data(v):
    v = str(v or '').strip()
    if not v:
        return None
    for f in FORMATOS:
        try:
            return datetime.strptime(v, f)
        except ValueError:
            pass
    try:
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
        return d.astimezone().replace(tzinfo=None) if d.tzinfo else d
    except ValueError:
        return None


def _sim(v):
    return _norm(v) in ('sim', 's', 'yes', 'y', 'true', '1', 'x', 'fechou', 'ganho')


def _tem_palavra(txt, palavras):
    t = _norm(txt).replace('_', ' ')
    return any(_norm(p).replace('_', ' ') in t for p in palavras)


# ============================================================
# FONTES
# ============================================================

def ler_csv(caminho):
    with open(caminho, encoding='utf-8-sig') as f:
        amostra = f.read(4096)
        f.seek(0)
        sep = ';' if amostra.count(';') > amostra.count(',') else ','
        leitor = csv.DictReader(f, delimiter=sep)
        mapa = {}
        for col in leitor.fieldnames or []:
            n = _norm(col)
            for campo, nomes in ALIASES.items():
                if n in nomes and campo not in mapa:
                    mapa[campo] = col
        conversas = []
        for linha in leitor:
            g = lambda c: (linha.get(mapa[c]) or '').strip() if c in mapa else ''  # noqa: E731
            etiquetas = g('etiquetas')
            conversas.append({
                'contato': g('contato'), 'telefone': g('telefone'), 'origem': g('origem') or 'sem origem',
                'atendente': g('atendente') or 'sem atendente', 'closer': g('closer'),
                'inicio': _data(g('inicio')), 'resposta': _data(g('resposta')),
                'qualificado': _sim(g('qualificado')) or _tem_palavra(etiquetas, ATENDIMENTO['palavras_qualificado']),
                'reuniao': _sim(g('reuniao')),
                'fechou': _sim(g('fechou')) or _tem_palavra(etiquetas, ATENDIMENTO['palavras_fechou']),
                'perdido': _tem_palavra(etiquetas, ['perdido', 'perdida', 'desistiu', 'sem interesse']),
                'motivo_perda': g('motivo_perda'), 'etiquetas': etiquetas,
            })
    faltando = [c for c in ('inicio', 'resposta', 'origem', 'atendente') if c not in mapa]
    return conversas, faltando


def _pega(d, *caminhos):
    for caminho in caminhos:
        v = d
        for parte in caminho.split('.'):
            v = v.get(parte) if isinstance(v, dict) else None
            if v is None:
                break
        if v not in (None, '', []):
            return v
    return None


def ler_api_flow(dias, max_conversas=400):
    """Atende Direito FLOW API (somente GET)."""
    base = 'https://api.atendedireito.app'
    h = {'X-Flow-Token': os.getenv('ATENDE_DIREITO_FLOW_TOKEN'), 'Content-Type': 'application/json'}
    corte = datetime.now() - timedelta(days=dias)

    def get(caminho, params=None):
        r = requests.get(base + caminho, headers=h, params=params, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f'Atende Direito {caminho}: HTTP {r.status_code} {r.text[:200]}')
        j = r.json()
        return j.get('data', j) if isinstance(j, dict) else j

    brutas, pagina_n = [], 1
    while len(brutas) < max_conversas and pagina_n <= 40:
        lote = get('/api/flow/conversations/filter', {'page': pagina_n, 'limit': 50}) or []
        if isinstance(lote, dict):
            lote = lote.get('items') or lote.get('conversations') or []
        if not lote:
            break
        brutas += lote
        datas = [_data(_pega(c, 'created_at', 'started_at')) for c in lote]
        if all(d and d < corte for d in datas):
            break
        pagina_n += 1

    conversas = []
    for c in brutas:
        inicio_conv = _data(_pega(c, 'created_at', 'started_at'))
        if inicio_conv and inicio_conv < corte:
            continue
        msgs = get(f"/api/flow/conversations/{c.get('id')}/messages", {'limit': 200}) or []
        if isinstance(msgs, dict):
            msgs = msgs.get('items') or msgs.get('messages') or []
        msgs = sorted(msgs, key=lambda m: _data(_pega(m, 'created_at', 'sent_at')) or datetime.max)
        primeira = next((m for m in msgs if m.get('sender_type') == 'contact'), None)
        t0 = _data(_pega(primeira, 'created_at', 'sent_at')) if primeira else inicio_conv
        resp = next((m for m in msgs if m.get('sender_type') in ('agent', 'bot')
                     and (_data(_pega(m, 'created_at', 'sent_at')) or datetime.min) >= (t0 or datetime.min)), None)
        tags = _pega(c, 'tags', 'contact.tags') or []
        nomes_tags = ', '.join(t.get('name', '') if isinstance(t, dict) else str(t) for t in tags)
        etapa = str(_pega(c, 'pipeline_stage.name', 'business.stage.name', 'stage.name') or '')
        rotulos = f'{nomes_tags} {etapa}'
        conversas.append({
            'contato': _pega(c, 'contact.name', 'contact_name') or '', 'telefone': _pega(c, 'contact.phone') or '',
            'origem': _pega(c, 'channel.name', 'source', 'origin') or 'sem origem',
            'atendente': _pega(c, 'assigned_agent.name', 'agent.name', 'attendant.name', 'agent_name') or 'sem atendente',
            'closer': '', 'inicio': t0, 'resposta': _data(_pega(resp, 'created_at', 'sent_at')) if resp else None,
            'resposta_robo': bool(resp and resp.get('sender_type') == 'bot'),
            'qualificado': _tem_palavra(rotulos, ATENDIMENTO['palavras_qualificado']),
            'reuniao': _tem_palavra(rotulos, ['reuniao', 'agendad']),
            'fechou': _tem_palavra(rotulos, ATENDIMENTO['palavras_fechou']),
            'perdido': _tem_palavra(rotulos, ['perdido', 'perdida', 'desistiu']), 'motivo_perda': '',
            'etiquetas': rotulos.strip(),
        })
    return conversas


def ler_api_antiga(dias):
    """API antiga: so contatos (sem mensagens). Devolve contatos novos no periodo, se houver data."""
    import atendedireito_integration as ad
    corte = datetime.now() - timedelta(days=dias)
    contatos, pag = [], 1
    while pag <= 50:
        subs, tem_mais = ad.listar_subscribers(page=pag)
        contatos += subs
        if not tem_mais:
            break
        pag += 1
    conversas = []
    for s in contatos:
        d = _data(_pega(s, 'created_at', 'subscribed', 'createdAt', 'last_interaction'))
        if d and d < corte:
            continue
        tags = _pega(s, 'tags') or []
        rotulos = ', '.join(t.get('name', '') if isinstance(t, dict) else str(t) for t in tags)
        conversas.append({
            'contato': _pega(s, 'name', 'first_name') or '', 'telefone': s.get('phone', ''),
            'origem': rotulos or 'sem origem', 'atendente': str(_pega(s, 'agent_name', 'agent_id') or 'sem atendente'),
            'closer': '', 'inicio': d, 'resposta': None, 'qualificado': _tem_palavra(rotulos, ATENDIMENTO['palavras_qualificado']),
            'reuniao': False, 'fechou': _tem_palavra(rotulos, ATENDIMENTO['palavras_fechou']), 'perdido': False,
            'motivo_perda': '', 'etiquetas': rotulos,
        })
    return conversas, len(contatos)


# ============================================================
# ANALISE
# ============================================================

def _min(c):
    if c['inicio'] and c['resposta'] and c['resposta'] >= c['inicio']:
        return (c['resposta'] - c['inicio']).total_seconds() / 60
    return None


def _resumo_tempos(tempos):
    if not tempos:
        return {'media': None, 'mediana': None, 'p90': None, 'no_sla': None, 'na_meta': None}
    t = sorted(tempos)
    return {
        'media': statistics.mean(t), 'mediana': statistics.median(t), 'p90': t[max(0, int(round(0.9 * len(t))) - 1)],
        'no_sla': 100.0 * sum(x <= ATENDIMENTO['sla_primeira_resposta_min'] for x in t) / len(t),
        'na_meta': 100.0 * sum(x <= ATENDIMENTO['meta_ideal_min'] for x in t) / len(t),
    }


def _fmt_min(m):
    if m is None:
        return '-'
    if m < 60:
        return f'{numero(m, 0)} min'
    if m < 1440:
        return f'{numero(m / 60, 1)} h'
    return f'{numero(m / 1440, 1)} dias'


def _faixa(d):
    if not d:
        return 'sem horário'
    if d.weekday() >= 5:
        return 'fim de semana'
    h = d.hour
    return 'madrugada (0-7h)' if h < 7 else 'manhã (7-12h)' if h < 12 else 'tarde (12-18h)' if h < 18 else 'noite (18-24h)'


def analisar(conversas, mede_tempo=True):
    agora = datetime.now()
    tempos = [t for t in (_min(c) for c in conversas) if t is not None]
    sem_resposta = [c for c in conversas if not c['resposta']] if mede_tempo else []
    perdidas = [c for c in sem_resposta if c['inicio'] and
                (agora - c['inicio']).total_seconds() / 3600 > ATENDIMENTO['horas_sem_resposta']]

    def grupo(chave):
        g = defaultdict(list)
        for c in conversas:
            g[c.get(chave) or f'sem {chave}'].append(c)
        saida = []
        for nome, cs in g.items():
            tt = [t for t in (_min(c) for c in cs) if t is not None]
            q, f = sum(c['qualificado'] for c in cs), sum(c['fechou'] for c in cs)
            saida.append({'nome': nome, 'conversas': len(cs), 'qualificados': q, 'fechados': f,
                          'pct_qualificados': 100.0 * q / len(cs), 'pct_fechados': 100.0 * f / len(cs),
                          'fechados_sobre_qualificados': (100.0 * f / q) if q else None,
                          'tempo_medio': statistics.mean(tt) if tt else None,
                          'sem_resposta': sum(1 for c in cs if not c['resposta']) if mede_tempo else None})
        return sorted(saida, key=lambda x: (x['fechados'], x['conversas']), reverse=True)

    fluxo = []
    for c in conversas:
        nome = c['contato'] or c['telefone'] or '(sem nome)'
        if c['qualificado'] and not c['reuniao'] and not c['fechou']:
            fluxo.append(f'{nome}: qualificado, mas sem reunião agendada registrada.')
        if c['reuniao'] and not c['fechou'] and not c['perdido']:
            fluxo.append(f'{nome}: reunião feita/agendada sem resultado registrado (fechou ou perdeu).')
        if c['perdido'] and not c['motivo_perda']:
            fluxo.append(f'{nome}: marcado como perdido sem motivo.')
    faixas = defaultdict(list)
    for c in conversas:
        faixas[_faixa(c['inicio'])].append(_min(c))
    por_faixa = [{'faixa': k, 'conversas': len(v),
                  'tempo_medio': statistics.mean([t for t in v if t is not None]) if any(t is not None for t in v) else None}
                 for k, v in sorted(faixas.items())]
    tem_closer = any(c['closer'] for c in conversas)
    datas = [c['inicio'] for c in conversas if c['inicio']]
    return {
        'total': len(conversas), 'qualificados': sum(c['qualificado'] for c in conversas),
        'fechados': sum(c['fechou'] for c in conversas), 'tempos': _resumo_tempos(tempos), 'mede_tempo': mede_tempo,
        'sem_resposta': len(sem_resposta), 'perdidas_sem_resposta': [c['contato'] or c['telefone'] for c in perdidas],
        'por_origem': grupo('origem'), 'por_atendente': grupo('atendente'),
        'por_closer': grupo('closer') if tem_closer else [], 'fluxo': fluxo, 'por_faixa': por_faixa,
        'de': min(datas).strftime('%d/%m/%Y') if datas else '-', 'ate': max(datas).strftime('%d/%m/%Y') if datas else '-',
    }


def _recomendacoes(a):
    rec, t = [], a['tempos']
    sla = ATENDIMENTO['sla_primeira_resposta_min']
    if t['mediana'] is not None and t['mediana'] > sla:
        rec.append(f"Primeira resposta demora {_fmt_min(t['mediana'])} (mediana). Meta: até {sla} min; "
                   f"ideal {ATENDIMENTO['meta_ideal_min']} min. Ligar o SDR de IA para responder na hora.")
    if a['perdidas_sem_resposta']:
        rec.append(f"{len(a['perdidas_sem_resposta'])} lead(s) ficaram sem resposta por mais de "
                   f"{ATENDIMENTO['horas_sem_resposta']}h: responder hoje e descobrir por que ficaram sem dono.")
    lentas = [f for f in a['por_faixa'] if f['tempo_medio'] and f['tempo_medio'] > sla and f['conversas'] >= 2]
    for f in lentas:
        rec.append(f"Leads que chegam de {f['faixa']} esperam em média {_fmt_min(f['tempo_medio'])}: rever escala "
                   'ou deixar o SDR de IA cobrindo esse horário.')
    if a['fluxo']:
        rec.append(f"{len(a['fluxo'])} conversa(s) com etapa do fluxo sem registro: atualizar o CRM (reunião, resultado, motivo).")
    origens = [o for o in a['por_origem'] if o['conversas'] >= 3]
    if origens:
        melhor = max(origens, key=lambda o: (o['pct_fechados'], o['pct_qualificados']))
        rec.append(f"Origem que mais converte: {melhor['nome']} ({numero(melhor['pct_fechados'])}% fecham, "
                   f"{numero(melhor['pct_qualificados'])}% qualificados). Comparar com o custo por lead no relatório do Meta.")
    if not a['mede_tempo']:
        rec.append('A API conectada não traz o horário das mensagens: para medir tempo de resposta, usar a API Flow '
                   '(ATENDE_DIREITO_FLOW_TOKEN) ou exportar o CSV das conversas.')
    return rec or ['Atendimento dentro das metas no período.']


def texto(a, fonte, rec, avisos):
    t = a['tempos']
    L = [f"AUDITORIA DO ATENDIMENTO - {a['de']} a {a['ate']} (fonte: {fonte})", '',
         f"Conversas: {a['total']} | Qualificados: {a['qualificados']} | Fechados: {a['fechados']}"]
    if a['mede_tempo']:
        L += [f"1ª resposta: média {_fmt_min(t['media'])} | mediana {_fmt_min(t['mediana'])} | 90% em até {_fmt_min(t['p90'])}",
              f"Dentro da meta de {ATENDIMENTO['sla_primeira_resposta_min']} min: "
              f"{numero(t['no_sla']) if t['no_sla'] is not None else '-'}% | até {ATENDIMENTO['meta_ideal_min']} min: "
              f"{numero(t['na_meta']) if t['na_meta'] is not None else '-'}%",
              f"Sem resposta: {a['sem_resposta']} (mais de {ATENDIMENTO['horas_sem_resposta']}h: {len(a['perdidas_sem_resposta'])})"]
    L += [''] + [f'AVISO: {x}' for x in avisos] + ([''] if avisos else [])
    L += ['O QUE FAZER'] + [f'  - {x}' for x in rec]
    for titulo, grupo in (('POR ORIGEM', a['por_origem']), ('POR ATENDENTE (SDR)', a['por_atendente']),
                          ('POR CLOSER', a['por_closer'])):
        if grupo:
            L += ['', titulo]
            for g in grupo:
                L.append(f"  {g['nome']}: {g['conversas']} conversas | {g['qualificados']} qualif. | {g['fechados']} fech. "
                         f"({numero(g['pct_fechados'])}%) | resposta média {_fmt_min(g['tempo_medio'])}")
    if a['fluxo']:
        L += ['', 'FLUXO NÃO SEGUIDO'] + [f'  - {x}' for x in a['fluxo']]
    return '\n'.join(L) + '\n'


def html(a, fonte, rec, avisos):
    t = a['tempos']
    kpis = [(str(a['total']), 'conversas'), (str(a['qualificados']), 'qualificados'), (str(a['fechados']), 'fechados')]
    if a['mede_tempo']:
        kpis += [(_fmt_min(t['mediana']), '1ª resposta (mediana)'),
                 (f"{numero(t['no_sla'])}%" if t['no_sla'] is not None else '-',
                  f"respondidas em até {ATENDIMENTO['sla_primeira_resposta_min']} min"),
                 (str(a['sem_resposta']), 'sem resposta')]

    def tab(grupo):
        return tabela(['Nome', 'Conversas', 'Qualificados', 'Fechados', '% fechados', 'Fech./qualif.', 'Resposta média'], [
            [g['nome'], (str(g['conversas']), g['conversas']), (str(g['qualificados']), g['qualificados']),
             (str(g['fechados']), g['fechados']), (f"{numero(g['pct_fechados'])}%", round(g['pct_fechados'], 1)),
             (f"{numero(g['fechados_sobre_qualificados'])}%" if g['fechados_sobre_qualificados'] is not None else '-',
              g['fechados_sobre_qualificados'] or 0),
             (_fmt_min(g['tempo_medio']), g['tempo_medio'] or 0)] for g in grupo])

    blocos = [(None, cartoes(kpis))]
    if avisos:
        blocos.append(('Avisos', lista(avisos, 'alerta')))
    blocos += [('O que fazer', lista(rec)), ('Por origem', tab(a['por_origem'])),
               ('Por atendente (SDR)', tab(a['por_atendente']))]
    if a['por_closer']:
        blocos.append(('Por Closer (quem fecha mais)', tab(a['por_closer'])))
    blocos.append(('Chegada dos leads por horário', tabela(['Faixa', 'Conversas', 'Resposta média'], [
        [f['faixa'], (str(f['conversas']), f['conversas']), (_fmt_min(f['tempo_medio']), f['tempo_medio'] or 0)]
        for f in a['por_faixa']])))
    blocos.append(('Fluxo não seguido', lista(a['fluxo'] or ['Nenhuma pendência de registro.'])))
    return pagina('Auditoria do Atendimento', f"{a['de']} a {a['ate']} - fonte: {fonte}", blocos,
                  'Somente leitura: nada foi enviado nem alterado no Atende Direito.')


def relatorio(dias=None, csv_path=None, exemplo=False, saida=None):
    print('\n=== AUDITORIA DO ATENDIMENTO ===')
    avisos, mede_tempo = [], True
    if exemplo or csv_path:
        caminho = EXEMPLO if exemplo else csv_path
        conversas, faltando = ler_csv(caminho)
        fonte = 'EXEMPLO FICTÍCIO' if exemplo else f'CSV {os.path.basename(caminho)}'
        if faltando:
            avisos.append('Colunas não encontradas no CSV: ' + ', '.join(faltando) + ' (ver docs/POP_COMERCIAL.md).')
            mede_tempo = 'inicio' not in faltando and 'resposta' not in faltando
        if dias:
            corte = datetime.now() - timedelta(days=dias)
            conversas = [c for c in conversas if not c['inicio'] or c['inicio'] >= corte]
    elif ambiente.tem_credencial('ATENDE_DIREITO_FLOW_TOKEN'):
        dias = dias or 7
        print(f'   Atende Direito (API Flow), ultimos {dias} dias...')
        conversas = ler_api_flow(dias)
        fonte = 'Atende Direito (API Flow)'
        avisos.append('Primeiro uso com a API Flow: conferir por amostragem 3 conversas no painel.')
    elif ambiente.tem_credencial('ATENDE_DIREITO_TOKEN'):
        dias = dias or 7
        print(f'   Atende Direito (API antiga), ultimos {dias} dias...')
        conversas, total = ler_api_antiga(dias)
        fonte, mede_tempo = 'Atende Direito (API antiga, só contatos)', False
        avisos.append(f'A API antiga só lista contatos ({total} no total); não traz as mensagens, então tempo de '
                      'resposta e conversas sem resposta não são medidos. Use --csv ou a API Flow.')
    else:
        raise SystemExit('Sem credencial do Atende Direito (ATENDE_DIREITO_FLOW_TOKEN ou ATENDE_DIREITO_TOKEN). '
                         'Use --csv EXPORT.csv ou --exemplo.')
    if not conversas:
        raise SystemExit('Nenhuma conversa no período.')
    a = analisar(conversas, mede_tempo)
    rec = _recomendacoes(a)
    pasta = saida or ambiente.pasta_saida('auditoria_atendimento')
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, datetime.now().strftime('%Y-%m-%d') + '_auditoria_atendimento' + ('_EXEMPLO' if exemplo else ''))
    txt = texto(a, fonte, rec, avisos)
    with open(base + '.txt', 'w', encoding='utf-8') as f:
        f.write(txt)
    with open(base + '.html', 'w', encoding='utf-8') as f:
        f.write(html(a, fonte, rec, avisos))
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'fonte': fonte, 'avisos': avisos, 'recomendacoes': rec, 'analise': a}, f,
                  ensure_ascii=False, indent=1, default=str)
    print(txt)
    print(f'Arquivos: {base}.txt | .html | .json')
    return base

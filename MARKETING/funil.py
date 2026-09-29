"""
FUNIL DO MES - do real gasto no Meta ao contrato assinado (cada numero com a sua fonte).

  gasto (Meta Ads) -> conversas iniciadas (Meta) -> leads de anuncio no atendimento -> qualificados (SDR)
  -> reunioes (Closer) -> contratos fechados (CONTRATACAO, pela data do contrato) -> receita (se houver valor)
  Indicadores: custo por conversa (CPL), por qualificado, por reuniao, por contrato (CAC) e ROI,
  e a comparacao com a agencia antiga (R$ 2.200/mes).

De onde vem cada numero:
  - gasto e conversas: Meta Ads (so leitura) ou --gasto informado a mao;
  - atendimento: --csv (mesmas colunas da auditoria do comercial, docs/POP_COMERCIAL.md) ou API Flow do
    Atende Direito (ATENDE_DIREITO_FLOW_TOKEN);
  - contratos: casos da CONTRATACAO (caso.json, campo data_contrato) - a coluna "fechou" do CSV serve de conferencia;
  - origem paga: textos como "Meta", "Facebook", "anuncio", "trafego" ou o codigo "MKT-XXXXX" dos links do
    trafego.py utm (o SDR registra o codigo que vem no fim da mensagem). "Instagram organico" nao conta.
Numero que nao existe sai como "sem dado" - nunca como zero inventado.

Uso: python MARKETING/trafego.py funil [--mes MM/AAAA] [--csv ARQ.csv] [--gasto VALOR] [--exemplo]
"""
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402  (carrega .env e caminhos)

AQUI = os.path.dirname(os.path.abspath(__file__))
COMERCIAL = os.path.join(ambiente.RAIZ, 'COMERCIAL')
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
if COMERCIAL not in sys.path:
    sys.path.append(COMERCIAL)

from config.escritorio import ESCRITORIO  # noqa: E402
from html_util import cartoes, lista, numero, pagina, reais, tabela  # noqa: E402

EXEMPLO = os.path.join(AQUI, 'exemplos', 'TRAFEGO_FUNIL_EXEMPLO.json')
EXEMPLO_CSV = os.path.join(AQUI, 'exemplos', 'TRAFEGO_FUNIL_ATENDIMENTO_EXEMPLO.csv')

# Referencia de antes do sistema (informada pelo escritorio na contratacao, 09/2026)
AGENCIA_ANTERIOR_MENSAL = 2200.0
CONTRATOS_MES_ANTES = '5 a 6 contratos por mês, somando todas as origens'

_PAGO = re.compile(r'\b(meta|facebook|fb|instagram|anuncio|anuncios|trafego|ads|impulsionad\w*|patrocinad\w*)\b|mkt-[a-z0-9]{5}')
_ORGANICO = re.compile(r'organic|organico|indicac|indicad')
_CODIGO = re.compile(r'MKT-[A-Z2-7]{5}')


def _sem_acento(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', str(txt or '')) if unicodedata.category(c) != 'Mn').lower()


def eh_pago(origem):
    o = _sem_acento(origem)
    return bool(_PAGO.search(o)) and not _ORGANICO.search(o)


def _valor(v):
    """'R$ 12.000,00' / '12000' / 12000 -> 12000.0 ; None se nao der para ler."""
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    s = re.sub(r'[^\d,.]', '', str(v or ''))
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif s.count('.') > 1 or re.search(r'\.\d{3}$', s):
        s = s.replace('.', '')
    try:
        f = float(s)
    except ValueError:
        return None
    return f if f > 0 else None


def periodo_mes(mes=None, hoje=None):
    """'MM/AAAA' -> (inicio, fim). Padrao: mes anterior. Mes corrente vai ate ontem."""
    hoje = hoje or date.today()
    if mes:
        m = re.fullmatch(r'\s*(\d{1,2})/(\d{4})\s*', mes)
        if not m or not 1 <= int(m.group(1)) <= 12:
            raise SystemExit(f'Mês inválido: {mes!r} (use MM/AAAA, ex.: 09/2026)')
        inicio = date(int(m.group(2)), int(m.group(1)), 1)
    else:
        inicio = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
    fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    if fim >= hoje:
        fim = hoje - timedelta(days=1)
    if fim < inicio:
        raise SystemExit('O mês ainda não tem nenhum dia fechado.')
    return inicio, fim


# ============================================================
# FONTES
# ============================================================

def dados_meta(inicio, fim):
    import meta_ads_integration as meta
    if not meta.configurado():
        return None, 'Meta Ads não configurado (META_ACCESS_TOKEN e META_AD_ACCOUNT_ID)'
    try:
        conta = meta.insights(level='account', desde=inicio.isoformat(), ate=fim.isoformat())
        camps = meta.insights(level='campaign', desde=inicio.isoformat(), ate=fim.isoformat())
    except meta.ErroMeta as e:
        return None, f'erro na Meta API: {e}'
    return {'conta': conta, 'campanhas': camps}, 'Meta Ads (API, só leitura)'


def dados_atendimento(inicio, fim, csv_path=None):
    """(conversas do mes, fonte). conversas = lista no formato de COMERCIAL/auditoria.py, ou None."""
    import auditoria
    if csv_path:
        conversas, _ = auditoria.ler_csv(csv_path)
        fonte = f'CSV {os.path.basename(csv_path)}'
    elif ambiente.tem_credencial('ATENDE_DIREITO_FLOW_TOKEN'):
        dias = (date.today() - inicio).days + 1
        try:
            conversas = auditoria.ler_api_flow(dias)
        except Exception as e:  # noqa: BLE001
            return None, f'Atende Direito indisponível ({e})'
        fonte = 'Atende Direito (API Flow)'
    else:
        return None, 'sem export do atendimento (--csv) e sem ATENDE_DIREITO_FLOW_TOKEN'
    no_mes = [c for c in conversas if c.get('inicio') and inicio <= c['inicio'].date() <= fim]
    return no_mes, fonte


def casos_contratacao():
    """[(base, caso)] da CONTRATACAO. Vazio se a pasta dos clientes nao estiver acessivel."""
    sys.path.insert(0, os.path.join(ambiente.RAIZ, 'CONTRATACAO'))
    try:
        import pasta_cliente
        return pasta_cliente.listar_casos()
    except Exception:  # noqa: BLE001
        return []


def _nome_curto(nome):
    partes = [p for p in re.sub(r'\[[^\]]*\]', '', str(nome or '')).split() if p]
    if not partes:
        return '(sem nome)'
    return partes[0].title() + (f' {partes[-1][0].upper()}.' if len(partes) > 1 else '')


def contratos_do_mes(casos, inicio, fim):
    saida = []
    for caso in casos:
        try:
            d = datetime.fromisoformat(str(caso.get('data_contrato'))[:10]).date()
        except ValueError:
            continue
        if not inicio <= d <= fim:
            continue
        cad, q = caso.get('cadastro') or {}, caso.get('qualificacao') or {}
        valor = None
        for fonte in (caso, cad):
            for chave in ('valor', 'valor_contrato', 'valor_honorarios', 'honorarios_total'):
                valor = valor or _valor(fonte.get(chave))
        origem = cad.get('origem') or q.get('origem') or ''
        saida.append({'cliente': _nome_curto(q.get('nome') or cad.get('nome')), 'data': d, 'origem': origem or '(sem origem)',
                      'pago': eh_pago(origem), 'sem_origem': not origem, 'valor': valor,
                      'codigo': (_CODIGO.search(origem.upper()) or [None])[0]})
    return sorted(saida, key=lambda x: x['data'])


# ============================================================
# CALCULO
# ============================================================

def _div(a, b):
    return a / b if a is not None and b else None


def calcular(meta, gasto_manual, conversas, contratos, codigos):
    from meta_ads import metricas
    m = metricas((meta or {}).get('conta', [{}])[0] if meta and meta.get('conta') else {}) if meta else None
    gasto = m['gasto'] if m else gasto_manual
    fonte_gasto = 'Meta Ads' if m else ('informado à mão (--gasto)' if gasto_manual is not None else None)
    leads_meta = m['leads'] if m else None

    pagas = [c for c in conversas or [] if eh_pago(c.get('origem'))]
    at = None
    if conversas is not None:
        at = {'total': len(conversas), 'pagas': len(pagas),
              'qualificados': sum(1 for c in pagas if c.get('qualificado')),
              'reunioes': sum(1 for c in pagas if c.get('reuniao')),
              'fechou': sum(1 for c in pagas if c.get('fechou')),
              'fechou_total': sum(1 for c in conversas if c.get('fechou'))}

    ct_pagos = [c for c in contratos if c['pago']]
    sem_origem = [c for c in contratos if c['sem_origem']]
    if contratos and len(sem_origem) < len(contratos):
        n_contratos, base_cac = len(ct_pagos), 'contratos da CONTRATACAO com origem de anúncio'
    elif at and at['fechou']:
        n_contratos, base_cac = at['fechou'], 'coluna "fechou" do atendimento (origem de anúncio)'
    elif contratos:
        n_contratos, base_cac = len(contratos), 'TODOS os contratos do mês (a origem não foi registrada nos casos)'
    else:
        n_contratos, base_cac = 0, 'nenhum contrato registrado no mês'

    receita_itens = [c['valor'] for c in ct_pagos if c['valor']]
    receita = sum(receita_itens) if receita_itens else None
    base_leads = leads_meta if leads_meta else (at['pagas'] if at else None)
    ind = {
        'cpl': _div(gasto, base_leads),
        'custo_qualificado': _div(gasto, at['qualificados'] if at else None),
        'custo_reuniao': _div(gasto, at['reunioes'] if at else None),
        'cac': _div(gasto, n_contratos),
        'receita': receita, 'receita_parcial': bool(receita_itens) and len(receita_itens) < len(ct_pagos),
        'roi': _div((receita - gasto) if (receita is not None and gasto is not None) else None, gasto),
    }

    # por origem (todas) e por codigo de anuncio
    por_origem = OrderedDict()
    for c in conversas or []:
        chave = 'anúncio (Meta)' if eh_pago(c.get('origem')) else (c.get('origem') or 'sem origem')
        g = por_origem.setdefault(chave, {'conversas': 0, 'qualificados': 0, 'reunioes': 0, 'fechou': 0})
        g['conversas'] += 1
        g['qualificados'] += bool(c.get('qualificado'))
        g['reunioes'] += bool(c.get('reuniao'))
        g['fechou'] += bool(c.get('fechou'))
    por_codigo = OrderedDict()
    for c in pagas:
        cod = (_CODIGO.search(str(c.get('origem') or '').upper()) or [None])[0]
        if not cod:
            continue
        info = codigos.get(cod) or {}
        g = por_codigo.setdefault(cod, {'anuncio': info.get('anuncio', '(código sem cadastro)'),
                                        'conjunto': info.get('conjunto', ''), 'conversas': 0,
                                        'qualificados': 0, 'reunioes': 0, 'fechou': 0})
        g['conversas'] += 1
        g['qualificados'] += bool(c.get('qualificado'))
        g['reunioes'] += bool(c.get('reuniao'))
        g['fechou'] += bool(c.get('fechou'))

    campanhas = []
    for linha in (meta or {}).get('campanhas') or []:
        x = metricas(linha)
        x['nome'] = linha.get('campaign_name', '')
        campanhas.append(x)
    return {'gasto': gasto, 'fonte_gasto': fonte_gasto, 'meta': m, 'leads_meta': leads_meta, 'atendimento': at,
            'contratos': contratos, 'contratos_pagos': len(ct_pagos), 'n_contratos_cac': n_contratos,
            'base_cac': base_cac, 'ind': ind, 'por_origem': por_origem, 'por_codigo': por_codigo,
            'campanhas': campanhas}


def comparacao_agencia(r):
    L = [f'Antes: agência a {reais(AGENCIA_ANTERIOR_MENSAL)} por mês (só a taxa, fora a verba de mídia) e '
         f'{CONTRATOS_MES_ANTES} (informado pelo escritório).']
    if r['gasto'] is not None:
        L.append(f"Agora: taxa de agência R$ 0,00; verba de mídia do mês {reais(r['gasto'])}.")
        dif = AGENCIA_ANTERIOR_MENSAL - r['gasto']
        L.append(f'A verba do mês ficou {reais(abs(dif))} ' + ('abaixo' if dif >= 0 else 'acima')
                 + ' do que se pagava só de taxa à agência.')
    else:
        L.append('Agora: gasto do mês sem dado (conectar o Meta ou informar --gasto).')
    cac = r['ind']['cac']
    if cac:
        L.append(f"Custo por contrato vindo de anúncio neste mês: {reais(cac)}. Com esse custo, os "
                 f"{reais(AGENCIA_ANTERIOR_MENSAL)} da taxa antiga equivalem a {numero(AGENCIA_ANTERIOR_MENSAL / cac, 1)} "
                 'contrato(s) a mais por mês se virassem verba.')
    n = len(r['contratos'])
    if r['contratos']:
        L.append(f"Contratos do mês (todas as origens, pela CONTRATACAO): {n}; de anúncio: {r['contratos_pagos']}.")
    return L


# ============================================================
# SAIDAS
# ============================================================

def _f(v, tipo='reais'):
    if v is None:
        return 'sem dado'
    return reais(v) if tipo == 'reais' else (f'{numero(100 * v)}%' if tipo == 'pct' else numero(v))


def etapas(r):
    at = r['atendimento'] or {}
    tem_at = r['atendimento'] is not None

    def taxa(a, b):
        return f'{numero(100 * a / b)}%' if a is not None and b else '-'
    linhas = [
        ('Gasto em anúncios', _f(r['gasto']), r['fonte_gasto'] or 'sem dado', '-'),
        ('Conversas iniciadas (Meta)', _f(r['leads_meta'], 'n'), 'Meta Ads' if r['meta'] else 'sem dado', '-'),
        ('Leads de anúncio no atendimento', _f(at.get('pagas') if tem_at else None, 'n'),
         'atendimento' if tem_at else 'sem dado', taxa(at.get('pagas'), r['leads_meta'])),
        ('Qualificados (SDR)', _f(at.get('qualificados') if tem_at else None, 'n'), 'atendimento' if tem_at else 'sem dado',
         taxa(at.get('qualificados'), at.get('pagas'))),
        ('Reuniões (Closer)', _f(at.get('reunioes') if tem_at else None, 'n'), 'atendimento' if tem_at else 'sem dado',
         taxa(at.get('reunioes'), at.get('qualificados'))),
        ('Contratos (de anúncio)', numero(r['n_contratos_cac']), r['base_cac'], taxa(r['n_contratos_cac'], at.get('reunioes'))),
    ]
    return linhas


def indicadores(r):
    i = r['ind']
    return [
        ('Custo por conversa (CPL)', _f(i['cpl'])), ('Custo por qualificado', _f(i['custo_qualificado'])),
        ('Custo por reunião', _f(i['custo_reuniao'])), ('Custo por contrato (CAC)', _f(i['cac'])),
        ('Receita dos contratos de anúncio', _f(i['receita']) + (' (parcial: nem todo caso tem valor)'
                                                                  if i['receita_parcial'] else '')),
        ('ROI (receita - gasto) ÷ gasto', _f(i['roi'], 'pct')),
    ]


def avisos(r, fontes):
    L = []
    if r['gasto'] is None:
        L.append('Gasto sem dado: conectar o Meta Ads (META_ACCESS_TOKEN, META_AD_ACCOUNT_ID) ou rodar com --gasto VALOR.')
    if r['atendimento'] is None:
        L.append(f"Atendimento sem dado ({fontes['atendimento']}): rodar com --csv EXPORT.csv.")
    elif r['atendimento']['total'] and not r['atendimento']['pagas']:
        L.append('Nenhuma conversa do mês foi marcada como vinda de anúncio: o SDR precisa registrar a ORIGEM '
                 '(ex.: "Meta - ref. MKT-XXXXX", o código que vem no fim da mensagem).')
    sem = [c for c in r['contratos'] if c['sem_origem']]
    if sem:
        L.append(f'{len(sem)} contrato(s) sem origem registrada no cadastro: preencher o campo "origem" na contratação.')
    if not r['contratos']:
        L.append('Nenhum contrato do mês na CONTRATACAO (conferir PASTA_CLIENTES_RAIZ).')
    if r['ind']['receita'] is None and r['contratos_pagos']:
        L.append('Receita sem dado: os casos não têm o campo "valor" (cadastro). O ROI fica em branco.')
    return L


def salvar_html(caminho, r, inicio, fim, fontes, exemplo):
    i = r['ind']
    blocos = [
        (None, cartoes([(_f(r['gasto']), 'gasto no mês'), (_f(r['leads_meta'], 'n'), 'conversas (Meta)'),
                        (numero(r['n_contratos_cac']), 'contratos de anúncio'), (_f(i['cac']), 'custo por contrato'),
                        (_f(i['roi'], 'pct'), 'ROI')])),
        ('Funil do anúncio ao contrato', tabela(['Etapa', 'Quantidade', 'Fonte', 'Passagem da etapa anterior'],
                                                [list(x) for x in etapas(r)])),
        ('Indicadores', tabela(['Indicador', 'Valor'], [list(x) for x in indicadores(r)])),
        ('Comparação com a agência antiga', lista(comparacao_agencia(r))),
    ]
    av = avisos(r, fontes)
    if av:
        blocos.insert(1, ('O que falta para o funil ficar completo', lista(av, 'alerta')))
    if r['por_origem']:
        blocos.append(('Todas as origens (atendimento)', tabela(['Origem', 'Conversas', 'Qualificados', 'Reuniões', 'Fechou'], [
            [o, (str(g['conversas']), g['conversas']), (str(g['qualificados']), g['qualificados']),
             (str(g['reunioes']), g['reunioes']), (str(g['fechou']), g['fechou'])] for o, g in r['por_origem'].items()])))
    if r['por_codigo']:
        blocos.append(('Por anúncio (código ref. da mensagem)', tabela(
            ['Código', 'Anúncio', 'Conjunto', 'Conversas', 'Qualificados', 'Reuniões', 'Fechou'], [
                [cod, g['anuncio'], g['conjunto'], (str(g['conversas']), g['conversas']),
                 (str(g['qualificados']), g['qualificados']), (str(g['reunioes']), g['reunioes']),
                 (str(g['fechou']), g['fechou'])] for cod, g in r['por_codigo'].items()])))
    if r['campanhas']:
        blocos.append(('Campanhas do Meta no mês', tabela(['Campanha', 'Gasto', 'Conversas', 'CPL'], [
            [c['nome'], (reais(c['gasto']), c['gasto']), (str(c['leads']), c['leads']),
             (reais(c['cpl']) if c['cpl'] else '-', c['cpl'] or 999999)] for c in r['campanhas']])))
    if r['contratos']:
        blocos.append(('Contratos do mês (CONTRATACAO)', tabela(['Data', 'Cliente', 'Origem', 'De anúncio?', 'Valor'], [
            [c['data'].strftime('%d/%m/%Y'), c['cliente'], c['origem'], 'sim' if c['pago'] else 'não',
             (reais(c['valor']) if c['valor'] else 'sem valor', c['valor'] or 0)] for c in r['contratos']])))
    blocos.append(('Fontes', lista([f"Gasto: {fontes['meta']}", f"Atendimento: {fontes['atendimento']}",
                                    f"Contratos: {fontes['contratos']}"], 'nota')))
    sub = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}" + (' - DADOS DE EXEMPLO' if exemplo else '')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(pagina('Funil do tráfego pago', sub, blocos, 'Números sem fonte aparecem como "sem dado".'))


def salvar_docx(caminho, r, inicio, fim, fontes, exemplo):
    from docx_caldeira import lista as dlista
    from docx_caldeira import novo_documento, paragrafo, secao, tabela as dtabela, titulo
    doc = novo_documento()
    titulo(doc, f"Funil do tráfego pago - {inicio.strftime('%m/%Y')}")
    if exemplo:
        paragrafo(doc, 'DADOS DE EXEMPLO: todos os números deste relatório são fictícios.', negrito=True)
    paragrafo(doc, f"{ESCRITORIO['nome']} - período de {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}. "
                   'Números sem fonte aparecem como "sem dado" (nunca como zero).')
    av = avisos(r, fontes)
    if av:
        secao(doc, 'O que falta para o funil ficar completo')
        dlista(doc, av)
    secao(doc, '1. Funil do anúncio ao contrato')
    dtabela(doc, ['Etapa', 'Quantidade', 'Fonte', 'Passagem'], [list(x) for x in etapas(r)],
            larguras_cm=[5.2, 2.8, 6.5, 2.5])
    secao(doc, '2. Indicadores')
    dtabela(doc, ['Indicador', 'Valor'], [list(x) for x in indicadores(r)], larguras_cm=[8, 9])
    secao(doc, '3. Comparação com a agência antiga')
    dlista(doc, comparacao_agencia(r))
    if r['por_codigo']:
        secao(doc, '4. Por anúncio (código ref.)')
        dtabela(doc, ['Código', 'Anúncio', 'Conversas', 'Qualif.', 'Reuniões', 'Fechou'], [
            [cod, g['anuncio'], str(g['conversas']), str(g['qualificados']), str(g['reunioes']), str(g['fechou'])]
            for cod, g in r['por_codigo'].items()], larguras_cm=[2.4, 6.6, 2, 2, 2, 2])
    if r['contratos']:
        secao(doc, '5. Contratos do mês')
        dtabela(doc, ['Data', 'Cliente', 'Origem', 'Anúncio?', 'Valor'], [
            [c['data'].strftime('%d/%m/%Y'), c['cliente'], c['origem'], 'sim' if c['pago'] else 'não',
             reais(c['valor']) if c['valor'] else 'sem valor'] for c in r['contratos']],
            larguras_cm=[2.3, 3.5, 6, 2, 3.2])
    secao(doc, 'Fontes')
    dlista(doc, [f"Gasto: {fontes['meta']}", f"Atendimento: {fontes['atendimento']}", f"Contratos: {fontes['contratos']}"])
    doc.save(caminho)


def gerar(mes=None, exemplo=False, csv_path=None, gasto_manual=None, saida=None):
    if exemplo:
        ex = json.load(open(EXEMPLO, encoding='utf-8'))
        mes = mes or ex['mes']
        inicio, fim = periodo_mes(mes, hoje=date(2100, 1, 1))
        meta = {'conta': ex['meta_conta'], 'campanhas': ex['meta_campanhas']}
        fontes = {'meta': 'exemplo (fictício)', 'atendimento': 'exemplo (fictício)', 'contratos': 'exemplo (fictício)'}
        import auditoria
        conversas = [c for c in auditoria.ler_csv(csv_path or EXEMPLO_CSV)[0]
                     if c.get('inicio') and inicio <= c['inicio'].date() <= fim]
        casos = ex['casos']
        codigos = ex['codigos']
        print('   usando dados FICTICIOS (MARKETING/exemplos/TRAFEGO_FUNIL_*)')
    else:
        inicio, fim = periodo_mes(mes)
        meta, fontes_meta = dados_meta(inicio, fim)
        conversas, fontes_at = dados_atendimento(inicio, fim, csv_path)
        casos = [c for _, c in casos_contratacao()]
        fontes = {'meta': fontes_meta if meta else (f'informado à mão ({fontes_meta})' if gasto_manual is not None
                                                    else fontes_meta),
                  'atendimento': fontes_at,
                  'contratos': f'CONTRATACAO ({len(casos)} caso(s) na pasta dos clientes)'}
        try:
            from trafego import ler_codigos
            codigos = ler_codigos()
        except Exception:  # noqa: BLE001
            codigos = {}
    print(f"\n=== FUNIL DO TRÁFEGO {inicio.strftime('%m/%Y')} ({inicio:%d/%m} a {fim:%d/%m}) ===")
    contratos = contratos_do_mes(casos, inicio, fim)
    r = calcular(meta, gasto_manual, conversas, contratos, codigos)

    pasta = os.path.join(saida, 'funil') if saida else ambiente.pasta_saida('marketing', 'funil')
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, f"funil_{inicio.strftime('%Y-%m')}" + ('_EXEMPLO' if exemplo else ''))
    salvar_html(base + '.html', r, inicio, fim, fontes, exemplo)
    salvar_docx(base + '.docx', r, inicio, fim, fontes, exemplo)
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'mes': inicio.strftime('%m/%Y'), 'fontes': fontes, 'resultado': r}, f, ensure_ascii=False, indent=1,
                  default=str)

    for nome, qtd, fonte, taxa in etapas(r):
        print(f'  {nome:34} {qtd:>14}   {taxa:>6}   ({fonte})')
    print()
    for nome, v in indicadores(r):
        print(f'  {nome:34} {v}')
    for x in avisos(r, fontes):
        print(f'  ! {x}')
    print(f'\nArquivos:\n  {base}.docx\n  {base}.html\n  {base}.json')
    return base


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Funil do tráfego pago (mês)')
    ap.add_argument('--mes')
    ap.add_argument('--csv')
    ap.add_argument('--gasto', type=float)
    ap.add_argument('--exemplo', action='store_true')
    ap.add_argument('--saida')
    a = ap.parse_args()
    gerar(a.mes, a.exemplo, a.csv, a.gasto, a.saida)

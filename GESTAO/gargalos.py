"""
GARGALOS - varredura historica das tarefas do ADVBOX (padrao: 90 dias).

  - por pessoa: total, concluidas, abertas, % no prazo, tempo medio/mediano, atraso medio;
  - por tipo de tarefa: o mesmo recorte;
  - tarefas abertas ha muito tempo (mais de 30 dias);
  - quem acumula mais tarefas abertas;
  - "peca pronta sem protocolo": tarefa de peca concluida e o protocolo do mesmo processo
    ainda aberto (o gargalo citado na reuniao);
  - sugestoes objetivas a partir dos numeros (regras simples, sem IA).
Sai: DOCX no timbrado + CSV (pessoas e tipos) + texto curto em SAIDA/gestao/gargalos/.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coleta  # noqa: E402
from collections import defaultdict  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from docx.shared import Pt  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402

PECA = re.compile(r'pe[cç]a|minuta|elabor|inicial|r[eé]plica|recurso|contesta|agravo|apela|embarg|notifica', re.I)
PROTOCOLO = re.compile(r'protocol', re.I)
ABERTA_HA_MUITO = 30


def _stats(pares, hoje):
    """pares = [(tarefa, participacao)] -> numeros do grupo."""
    concl = [(t, p) for t, p in pares if p['concluida_em']]
    abertas = [(t, p) for t, p in pares if not p['concluida_em']]
    com_prazo = [(t, p) for t, p in concl if coleta.data(t['prazo'])]
    no_prazo = [1 for t, p in com_prazo if coleta.concluida_em(p) <= coleta.data(t['prazo'])]
    atrasos = [(coleta.concluida_em(p) - coleta.data(t['prazo'])).days for t, p in com_prazo
               if coleta.concluida_em(p) > coleta.data(t['prazo'])]
    tempos = [coleta.dias_para_concluir(t, p) for t, p in concl]
    abertas_atrasadas = [1 for t, _ in abertas if coleta.data(t['prazo']) and coleta.data(t['prazo']) < hoje]
    return {'total': len(pares), 'concluidas': len(concl), 'abertas': len(abertas),
            'abertas_atrasadas': len(abertas_atrasadas),
            'pct_no_prazo': round(100 * len(no_prazo) / len(com_prazo)) if com_prazo else None,
            'tempo_medio': coleta.media(tempos), 'tempo_mediano': coleta.mediana(tempos),
            'atraso_medio': coleta.media(atrasos), 'sem_prazo': sum(1 for t, _ in pares if not t['prazo'])}


def levantar(dias=90, exemplo=False):
    hoje = coleta.hoje()
    inicio = hoje - timedelta(days=dias)
    tarefas = coleta.tarefas(exemplo, created_start=inicio.isoformat(), created_end=hoje.isoformat())
    tarefas = [t for t in tarefas if (coleta.data(t['criada_em']) or hoje) >= inicio]
    pessoas = {rot: _stats(pares, hoje) for rot, pares in coleta.por_pessoa(tarefas, exemplo).items()}
    por_tipo = defaultdict(list)
    for t in tarefas:
        for p in t['pessoas']:
            por_tipo[t['tipo']].append((t, p))
    tipos = {k: _stats(v, hoje) for k, v in por_tipo.items()}
    geral = _stats([(t, p) for t in tarefas for p in t['pessoas']], hoje)

    antigas = []
    for t in tarefas:
        criada = coleta.data(t['criada_em'])
        pend = [p for p in t['pessoas'] if not p['concluida_em']]
        if pend and criada and (hoje - criada).days > ABERTA_HA_MUITO:
            antigas.append({'dias': (hoje - criada).days, 'tipo': t['tipo'], 'cliente': t['cliente'],
                            'prazo': t['prazo'], 'quem': ', '.join(coleta.comum.rotulo_pessoa(p['id'], p['nome'], exemplo)
                                                                   for p in pend)})
    antigas.sort(key=lambda a: -a['dias'])

    # peca pronta sem protocolo (mesmo processo)
    por_processo = defaultdict(list)
    for t in tarefas:
        por_processo[str(t['processo_id'])].append(t)
    sem_protocolo = []
    for pid, ts in por_processo.items():
        pecas = [t for t in ts if PECA.search(t['tipo']) and all(p['concluida_em'] for p in t['pessoas'])]
        protocolos = [t for t in ts if PROTOCOLO.search(t['tipo']) and any(not p['concluida_em'] for p in t['pessoas'])]
        for pr in protocolos:
            pronta = max((coleta.concluida_em(p) for t in pecas for p in t['pessoas'] if coleta.concluida_em(p)),
                         default=None)
            if pronta and (hoje - pronta).days >= 2:
                sem_protocolo.append({'cliente': pr['cliente'], 'processo': pr['processo'], 'peca_pronta': pronta,
                                      'dias': (hoje - pronta).days, 'prazo_protocolo': pr['prazo'],
                                      'quem': ', '.join(p['nome'] for p in pr['pessoas'] if not p['concluida_em'])})
    sem_protocolo.sort(key=lambda s: -s['dias'])
    return {'hoje': hoje, 'inicio': inicio, 'dias': dias, 'tarefas': tarefas, 'pessoas': pessoas, 'tipos': tipos,
            'geral': geral, 'antigas': antigas, 'sem_protocolo': sem_protocolo,
            'sem_advbox': not coleta.comum.tem_advbox() and not exemplo}


def sugestoes(d):
    s = []
    total_abertas = sum(v['abertas'] for v in d['pessoas'].values())
    for rot, v in sorted(d['pessoas'].items(), key=lambda kv: -kv[1]['abertas']):
        if total_abertas >= 5 and v['abertas'] >= 3 and v['abertas'] / total_abertas > 0.35:
            s.append(f"Redistribuir: {rot} concentra {round(100 * v['abertas'] / total_abertas)}% das tarefas abertas "
                     f"({v['abertas']}).")
        if v['concluidas'] >= 4 and v['pct_no_prazo'] is not None and v['pct_no_prazo'] < 80:
            s.append(f"{rot} cumpre {v['pct_no_prazo']}% no prazo: revisar a carga e trabalhar pelo prazo interno (D-3).")
    media_geral = d['geral']['tempo_medio'] or 0
    for tipo, v in d['tipos'].items():
        if media_geral and v['concluidas'] >= 2 and (v['tempo_medio'] or 0) > 2 * media_geral:
            s.append(f"O tipo '{tipo}' leva {v['tempo_medio']} dias em média (geral {media_geral}): criar modelo/"
                     "checklist ou dividir a tarefa em etapas.")
    if len(d['antigas']) >= 3:
        s.append(f"{len(d['antigas'])} tarefas abertas há mais de {ABERTA_HA_MUITO} dias: mutirão de baixa (concluir no "
                 "ADVBOX o que já foi feito; a API não conclui tarefas) e redefinir prazo do resto.")
    if d['sem_protocolo']:
        s.append(f"{len(d['sem_protocolo'])} peça(s) pronta(s) aguardando protocolo: protocolar ou baixar a tarefa no "
                 "mesmo dia em que a peça fica pronta.")
    g = d['geral']
    if g['total'] and g['sem_prazo'] / g['total'] > 0.2:
        s.append(f"{round(100 * g['sem_prazo'] / g['total'])}% das tarefas estão sem prazo: toda tarefa deve ter data "
                 "limite no ADVBOX (sem prazo não entra na pauta nem na auditoria).")
    return s or ['Nenhum gargalo claro nos números do período.']


def gerar(dias=90, exemplo=False):
    print(f'\n=== GESTÃO: GARGALOS (últimos {dias} dias) ===')
    d = levantar(dias, exemplo)
    sug = sugestoes(d)
    doc = novo_documento()
    titulo(doc, 'Gargalos da Operação')
    paragrafo(doc, f"Tarefas do ADVBOX criadas de {coleta.br(d['inicio'])} a {coleta.br(d['hoje'])}"
                   + (' · DADOS FICTÍCIOS' if exemplo else ''), tamanho=10).alignment = 1
    if d['sem_advbox']:
        paragrafo(doc, 'ADVBOX sem credencial: sem tarefas para analisar. [CONFERIR]', tamanho=10)
    g = d['geral']
    secao(doc, '1. O que fazer (sugestões objetivas)')
    lista(doc, sug)
    secao(doc, '2. Visão geral')
    tabela(doc, ['Tarefas', 'Concluídas', 'Abertas', 'Abertas atrasadas', '% no prazo', 'Tempo médio (dias)'],
           [[str(g['total']), str(g['concluidas']), str(g['abertas']), str(g['abertas_atrasadas']),
             f"{g['pct_no_prazo']}%" if g['pct_no_prazo'] is not None else '-', str(g['tempo_medio'] or '-')]],
           [2.4, 2.5, 2.4, 3, 2.4, 3], tamanho=9)
    secao(doc, '3. Por pessoa (quem acumula mais primeiro)')
    cab = ['Pessoa', 'Total', 'Abertas', 'Atrasadas', '% no prazo', 'Tempo médio', 'Atraso médio']
    tabela(doc, cab, [[rot, str(v['total']), str(v['abertas']), str(v['abertas_atrasadas']),
                       f"{v['pct_no_prazo']}%" if v['pct_no_prazo'] is not None else '-',
                       str(v['tempo_medio'] or '-'), str(v['atraso_medio'] or '-')]
                      for rot, v in sorted(d['pessoas'].items(), key=lambda kv: -kv[1]['abertas'])],
           [5.3, 1.4, 1.6, 1.8, 1.9, 1.9, 1.8], tamanho=8)
    secao(doc, '4. Por tipo de tarefa (mais lento primeiro)')
    tabela(doc, ['Tipo', 'Total', 'Abertas', '% no prazo', 'Tempo médio', 'Mediana'],
           [[k, str(v['total']), str(v['abertas']), f"{v['pct_no_prazo']}%" if v['pct_no_prazo'] is not None else '-',
             str(v['tempo_medio'] or '-'), str(v['tempo_mediano'] or '-')]
            for k, v in sorted(d['tipos'].items(), key=lambda kv: -(kv[1]['tempo_medio'] or 0))],
           [5.5, 1.6, 1.8, 2.2, 2.4, 2.2], tamanho=8)
    secao(doc, '5. Peça pronta aguardando protocolo')
    if d['sem_protocolo']:
        tabela(doc, ['Cliente', 'Processo', 'Peça pronta em', 'Dias', 'Com quem'],
               [[s['cliente'][:30], s['processo'], coleta.br(s['peca_pronta']), str(s['dias']), s['quem']]
                for s in d['sem_protocolo']], [3.8, 3.8, 2.6, 1.3, 4.2], tamanho=8)
    else:
        paragrafo(doc, 'Nenhuma peça concluída com protocolo em aberto no mesmo processo.')
    secao(doc, f'6. Tarefas abertas há mais de {ABERTA_HA_MUITO} dias')
    if d['antigas']:
        tabela(doc, ['Dias', 'Tipo', 'Cliente', 'Prazo', 'Com quem'],
               [[str(a['dias']), a['tipo'], a['cliente'][:30], coleta.br(a['prazo']), a['quem']]
                for a in d['antigas'][:40]], [1.3, 3.2, 3.9, 2.3, 5], tamanho=8)
    else:
        paragrafo(doc, 'Nenhuma.')
    p = paragrafo(doc, 'Tempo de conclusão = da criação da tarefa até a baixa no ADVBOX. Tarefa feita e não baixada '
                       'conta como aberta: a baixa em dia é parte do controle.', tamanho=9)
    p.paragraph_format.space_before = Pt(12)

    pasta = coleta.pasta_gestao('gargalos')
    carimbo = datetime.now().strftime('%Y-%m-%d_%H%M') + ('_EXEMPLO' if exemplo else '')
    docx = os.path.join(pasta, f'{carimbo} - Gargalos {dias} dias.docx')
    doc.save(docx)
    coleta.comum.salvar_csv(os.path.join(pasta, f'{carimbo} - Gargalos por pessoa.csv'),
                            [dict(pessoa=k, **v) for k, v in d['pessoas'].items()])
    coleta.comum.salvar_csv(os.path.join(pasta, f'{carimbo} - Gargalos por tipo.csv'),
                            [dict(tipo=k, **v) for k, v in d['tipos'].items()])
    txt = '\n'.join([f"GARGALOS ({dias} dias): {g['total']} tarefas, {g['abertas']} abertas "
                     f"({g['abertas_atrasadas']} atrasadas), {g['pct_no_prazo'] if g['pct_no_prazo'] is not None else '-'}% "
                     f"no prazo, tempo médio {g['tempo_medio'] or '-'} dias", ''] + [f'- {x}' for x in sug])
    with open(os.path.join(pasta, f'{carimbo} - Gargalos - WhatsApp.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)
    print(f'\n   Documento: {docx}')
    return docx, txt, d

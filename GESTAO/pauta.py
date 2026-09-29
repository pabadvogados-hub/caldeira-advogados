"""
PAUTA DE SEGUNDA - o que cada um faz na semana.

  - por pessoa/cargo: tarefas atrasadas e tarefas que vencem na semana (ADVBOX /posts);
  - prazos fatais, audiencias e pericias da semana (varreduras do DJEN + tarefas de prazo);
  - casos em cada fase (contratacao / extrajudicial / judicial) pelas pastas (caso.json);
  - documentos pendentes dos clientes;
  - notificacoes (15 dias) e iniciais (60 dias) perto do limite ou estouradas.
Sai: DOCX no timbrado + texto curto para o WhatsApp da equipe (SAIDA/gestao/pauta/).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coleta  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from docx.shared import Pt  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402


def levantar(exemplo=False):
    hoje = coleta.hoje()
    seg, sex = coleta.semana_de_trabalho(hoje)
    tarefas = coleta.tarefas(exemplo, deadline_start=(hoje - timedelta(days=180)).isoformat(),
                             deadline_end=sex.isoformat())
    pessoas = {}
    for rot, lista_tp in coleta.por_pessoa(tarefas, exemplo).items():
        atrasadas, semana = [], []
        for t, p in lista_tp:
            if p['concluida_em']:
                continue
            prazo = coleta.data(t['prazo'])
            if not prazo:
                continue
            if prazo < hoje:
                atrasadas.append((t, p))
            elif prazo <= sex:
                semana.append((t, p))
        if atrasadas or semana:
            pessoas[rot] = {'atrasadas': sorted(atrasadas, key=lambda x: x[0]['prazo']),
                            'semana': sorted(semana, key=lambda x: x[0]['prazo'])}

    # prazos e eventos da semana (DJEN classificado + tarefas de prazo)
    prazos = []
    for i in coleta.publicacoes(hoje - timedelta(days=60), hoje, exemplo):
        f = coleta.data(i.get('fatal_iso'))
        if f and hoje <= f <= sex and i.get('prazo_nosso') != 'NÃO' and i['categoria'] != 'AUDIENCIA':
            prazos.append({'data': f, 'o_que': f"{i['rotulo']} (fatal; interno {i['interno']})",
                           'processo': i['processo'], 'cliente': i['cliente'], 'quem': i['responsavel']})
        ev = coleta.data(i.get('evento_data'))
        if ev and hoje <= ev <= sex + timedelta(days=7):
            prazos.append({'data': ev, 'o_que': f"{i['evento_tipo'].title()} {i.get('evento_hora') or ''}".strip(),
                           'processo': i['processo'], 'cliente': i['cliente'], 'quem': i['responsavel']})
    for t in tarefas:
        prazo = coleta.data(t['prazo'])
        pend = [p for p in t['pessoas'] if not p['concluida_em']]
        if pend and prazo and hoje <= prazo <= sex and 'PRAZO' in t['tipo'].upper():
            prazos.append({'data': prazo, 'o_que': f"{t['tipo']} (tarefa ADVBOX)", 'processo': t['processo'],
                           'cliente': t['cliente'], 'quem': ', '.join(p['nome'] for p in pend)})
    prazos.sort(key=lambda x: x['data'])

    casos = coleta.casos(exemplo)
    fases = Counter()
    por_fase, docs, marcos = {}, [], []
    for base, caso in casos:
        fase = coleta.comum.fase_do_caso(caso)
        fases[fase] += 1
        inicio = coleta.data(caso.get('data_contrato'))
        por_fase.setdefault(fase, []).append({'cliente': coleta.comum.nome_do_caso(caso),
                                              'dias': (hoje - inicio).days if inicio else '',
                                              'etapa': caso.get('etapa') or ''})
        falta = coleta.comum.documentos_faltando(caso)
        if falta:
            docs.append({'cliente': coleta.comum.nome_do_caso(caso), 'faltando': ', '.join(s['nome'] for s in falta),
                         'regua': 'esgotada' if caso.get('alerta_gestor_em') else
                         f"{len(caso.get('toques_documentos') or [])} de 3 mensagens"})
        for mc in coleta.comum.marcos_do_caso(caso, hoje):
            if mc['situacao'] in ('ESTOUROU', 'PERTO DO LIMITE') or (not mc['feito_em'] and mc['limite'] <= sex):
                marcos.append({'cliente': coleta.comum.nome_do_caso(caso),
                               'marco': 'Notificação (15 dias)' if mc['marco'] == 'notificacao' else 'Inicial (60 dias)',
                               'limite': mc['limite'], 'situacao': mc['situacao'], 'dias': mc['dias_restantes']})
    marcos.sort(key=lambda m: m['limite'])
    return {'hoje': hoje, 'seg': seg, 'sex': sex, 'pessoas': pessoas, 'prazos': prazos, 'fases': fases,
            'por_fase': por_fase, 'docs': docs, 'marcos': marcos, 'sem_advbox': not coleta.comum.tem_advbox() and not exemplo}


def texto_whatsapp(d):
    tot_sem = sum(len(v['semana']) for v in d['pessoas'].values())
    tot_atr = sum(len(v['atrasadas']) for v in d['pessoas'].values())
    linhas = [f"PAUTA DA SEMANA {coleta.br(d['seg'])[:5]} a {coleta.br(d['sex'])[:5]}",
              f"Prazos/audiências: {len(d['prazos'])} | Tarefas da semana: {tot_sem} | Atrasadas: {tot_atr}", '',
              'Por pessoa:']
    for rot in sorted(d['pessoas'], key=coleta.ordem_pessoa):
        v = d['pessoas'][rot]
        linhas.append(f"- {rot}: {len(v['semana'])} na semana, {len(v['atrasadas'])} atrasada(s)")
    if not d['pessoas']:
        linhas.append('- (nenhuma tarefa do ADVBOX com prazo nesta semana ou atrasada)')
    alertas = [f"- {m['marco']} de {coleta.comum.nome_proprio(m['cliente'])}: {'ESTOUROU' if m['situacao'] == 'ESTOUROU' else 'vence ' + coleta.br(m['limite'])}"
               for m in d['marcos']]
    alertas += [f"- {p['o_que']} {coleta.dia_semana(p['data'])} {coleta.br(p['data'])[:5]}: {coleta.comum.nome_proprio(p['cliente'][:30])}"
                for p in d['prazos'][:8]]
    if alertas:
        linhas += ['', 'Atenção:'] + alertas[:14]
    fases = ', '.join(f'{k.lower()} {v}' for k, v in d['fases'].most_common())
    if fases:
        linhas += ['', f'Casos nas pastas: {fases}.']
    linhas += ['', 'Detalhe no documento da pauta.']
    return '\n'.join(linhas)


def gerar(exemplo=False):
    print('\n=== GESTÃO: PAUTA DE SEGUNDA ===')
    d = levantar(exemplo)
    doc = novo_documento()
    titulo(doc, 'Pauta da Semana')
    paragrafo(doc, f"Reunião de segunda · semana de {coleta.br(d['seg'])} a {coleta.br(d['sex'])}"
                   + (' · DADOS FICTÍCIOS' if exemplo else ''), tamanho=10).alignment = 1
    if d['sem_advbox']:
        paragrafo(doc, 'ADVBOX sem credencial: tarefas não entraram nesta pauta. [CONFERIR]', tamanho=10)

    secao(doc, '1. Resumo')
    tot_sem = sum(len(v['semana']) for v in d['pessoas'].values())
    tot_atr = sum(len(v['atrasadas']) for v in d['pessoas'].values())
    tabela(doc, ['Tarefas da semana', 'Tarefas atrasadas', 'Prazos e audiências', 'Marcos 15/60 em alerta',
                 'Clientes com documento faltando'],
           [[str(tot_sem), str(tot_atr), str(len(d['prazos'])), str(len(d['marcos'])), str(len(d['docs']))]],
           [3.1, 3.1, 3.1, 3.2, 3.2], tamanho=10)

    secao(doc, '2. Prazos fatais, audiências e perícias')
    if d['prazos']:
        tabela(doc, ['Quando', 'O quê', 'Processo', 'Cliente', 'Quem'],
               [[f"{coleta.dia_semana(p['data'])} {coleta.br(p['data'])}", p['o_que'], p['processo'],
                 p['cliente'][:28], p['quem'][:30]] for p in d['prazos']], [2.4, 4.3, 3.6, 2.8, 2.6], tamanho=8)
    else:
        paragrafo(doc, 'Nenhum prazo fatal ou audiência encontrado para a semana (conferir a varredura do DJEN).')

    secao(doc, '3. Por pessoa')
    if not d['pessoas']:
        paragrafo(doc, 'Nenhuma tarefa com prazo na semana ou atrasada.')
    for rot in sorted(d['pessoas'], key=coleta.ordem_pessoa):
        v = d['pessoas'][rot]
        p = paragrafo(doc, f"{len(v['semana'])} na semana · {len(v['atrasadas'])} atrasada(s)", rotulo=rot, espaco=1.0)
        p.paragraph_format.space_before = Pt(6)
        linhas = [['ATRASADA', coleta.br(t['prazo']), t['tipo'], t['cliente'][:30], t['processo']]
                  for t, _ in v['atrasadas']]
        linhas += [[coleta.dia_semana(coleta.data(t['prazo'])), coleta.br(t['prazo']), t['tipo'], t['cliente'][:30],
                    t['processo']] for t, _ in v['semana']]
        tabela(doc, ['Situação', 'Prazo', 'Tarefa', 'Cliente', 'Processo'], linhas, [2.2, 2.3, 4.2, 3.6, 3.4], tamanho=8)

    secao(doc, '4. Casos em cada fase (pastas dos clientes)')
    if d['fases']:
        tabela(doc, ['Fase', 'Casos', 'Clientes (dias desde o contrato)'],
               [[f, str(n), '; '.join(f"{coleta.comum.nome_proprio(c['cliente'])} ({c['dias']}d)" for c in d['por_fase'][f][:12])]
                for f, n in d['fases'].most_common()], [3.8, 1.6, 10.3], tamanho=9)
    else:
        paragrafo(doc, 'Nenhum caso nas pastas (PASTA_CLIENTES_RAIZ).')

    secao(doc, '5. Notificações (15 dias) e iniciais (60 dias)')
    if d['marcos']:
        tabela(doc, ['Cliente', 'Marco', 'Limite', 'Situação'],
               [[coleta.comum.nome_proprio(m['cliente']), m['marco'], coleta.br(m['limite']),
                 m['situacao'] + ('' if m['situacao'] == 'ESTOUROU' else f" ({m['dias']} dias)")] for m in d['marcos']],
               [5.2, 3.8, 2.6, 4.1], tamanho=9)
    else:
        paragrafo(doc, 'Nenhum marco perto do limite.')

    secao(doc, '6. Documentos pendentes dos clientes')
    if d['docs']:
        tabela(doc, ['Cliente', 'Faltando', 'Cobrança automática'],
               [[coleta.comum.nome_proprio(x['cliente']), x['faltando'], x['regua']] for x in d['docs']], [4.2, 8.3, 3.2], tamanho=9)
    else:
        paragrafo(doc, 'Nenhum documento pendente.')

    secao(doc, '7. Decisões da reunião')
    lista(doc, ['Quem: ______________   O quê: ________________________________   Até: ___/___'] * 4)
    p = paragrafo(doc, 'Pauta montada automaticamente a partir do ADVBOX, das varreduras do DJEN e das pastas dos '
                       'clientes. Prazos fatais são cálculo preliminar da Controladoria: conferir no processo.',
                  tamanho=9)
    p.paragraph_format.space_before = Pt(12)

    pasta = coleta.pasta_gestao('pauta')
    carimbo = f"{d['seg']:%Y-%m-%d}" + ('_EXEMPLO' if exemplo else '')
    docx = os.path.join(pasta, f'Pauta da Semana {carimbo}.docx')
    doc.save(docx)
    txt = texto_whatsapp(d)
    with open(os.path.join(pasta, f'Pauta da Semana {carimbo} - WhatsApp.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)
    print(f'\n   Documento: {docx}')
    return docx, txt, d

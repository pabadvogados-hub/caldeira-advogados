"""
AUDITORIA DE SEXTA - fez? protocolou? prazos cumpridos?

  - por pessoa: tarefas que venciam na semana concluidas x nao concluidas, concluidas com atraso;
  - tempo medio de conclusao por pessoa e por tipo de tarefa (criada -> concluida);
  - casos que estouraram 15 dias (notificacao) ou 60 dias (inicial);
  - indicadores dos manuais: liminares obtidas/negadas, decisoes favoraveis, zero prazo perdido,
    antecedencia nos protocolos, rapidez da inicial, notificacao em 15 dias, extrajudicial em 60 dias;
  - comercial: novos contratos (leads e tempo de atendimento nao vem pela API usada hoje).
Sai: DOCX no timbrado + texto curto (SAIDA/gestao/auditoria/).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coleta  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from datetime import timedelta  # noqa: E402

from docx.shared import Pt  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402

PROTOCOLO = re.compile(r'protocol|prazo|peticion|recurso|replica|réplica|agravo|apela|contesta', re.I)


def _pct(a, b):
    return f'{round(100 * a / b)}%' if b else '-'


def levantar(exemplo=False):
    hoje = coleta.hoje()
    seg, sex = coleta.semana_de_trabalho(hoje - timedelta(days=2) if hoje.weekday() >= 5 else hoje)
    fim = min(sex, hoje)
    vencendo = coleta.tarefas(exemplo, deadline_start=seg.isoformat(), deadline_end=sex.isoformat())
    concluidas = coleta.tarefas(exemplo, completed_start=seg.isoformat(), completed_end=fim.isoformat())
    atrasadas_antigas = coleta.tarefas(exemplo, deadline_start=(hoje - timedelta(days=60)).isoformat(),
                                       deadline_end=(seg - timedelta(days=1)).isoformat())

    # 1. por pessoa: o que vencia na semana
    pessoas = defaultdict(lambda: {'previstas': 0, 'feitas': 0, 'nao_feitas': [], 'com_atraso': [],
                                   'tempos': [], 'antecedencia': []})
    for rot, lista_tp in coleta.por_pessoa(vencendo, exemplo).items():
        for t, p in lista_tp:
            prazo = coleta.data(t['prazo'])
            if not prazo or not (seg <= prazo <= sex):
                continue
            pessoas[rot]['previstas'] += 1
            if p['concluida_em']:
                pessoas[rot]['feitas'] += 1
            elif prazo <= fim:
                pessoas[rot]['nao_feitas'].append(t)
    # concluidas na semana: atraso, tempo, antecedencia
    tipos = defaultdict(list)
    for rot, lista_tp in coleta.por_pessoa(concluidas, exemplo).items():
        for t, p in lista_tp:
            quando = coleta.concluida_em(p)
            if not quando or not (seg <= quando <= fim):
                continue
            prazo = coleta.data(t['prazo'])
            dias = coleta.dias_para_concluir(t, p)
            pessoas[rot]['tempos'].append(dias)
            tipos[t['tipo']].append(dias)
            if prazo and quando > prazo:
                pessoas[rot]['com_atraso'].append((t, (quando - prazo).days))
            if prazo and PROTOCOLO.search(t['tipo']):
                pessoas[rot]['antecedencia'].append((prazo - quando).days)

    # 2. prazo perdido? tarefa de prazo vencida e nao concluida
    perdidos = []
    for t in vencendo + atrasadas_antigas:
        prazo = coleta.data(t['prazo'])
        pend = [p for p in t['pessoas'] if not p['concluida_em']]
        if pend and prazo and prazo < hoje and ('PRAZO' in t['tipo'].upper() or '[CONTROLADORIA]' in t['texto']):
            perdidos.append(t)
    vistos = set()
    perdidos = [t for t in perdidos if not (t['id'] in vistos or vistos.add(t['id']))]

    # 3. publicacoes da semana (DJEN)
    pubs = coleta.publicacoes(seg, fim, exemplo)
    cat = Counter(i['categoria'] for i in pubs)

    # 4. casos 15/60 dias e comercial
    estouros, marcos_todos, rapidez, novos = [], [], [], []
    for base, caso in coleta.casos(exemplo):
        nome = coleta.comum.nome_proprio(coleta.comum.nome_do_caso(caso))
        contrato = coleta.data(caso.get('data_contrato'))
        if contrato and seg <= contrato <= fim:
            novos.append(nome)
        for mc in coleta.comum.marcos_do_caso(caso, hoje):
            marcos_todos.append(mc)
            if mc['situacao'] == 'ESTOUROU' or (mc['situacao'] == 'CUMPRIDO COM ATRASO'
                                                 and mc['feito_em'] and seg <= mc['feito_em'] <= fim):
                estouros.append({'cliente': nome, 'marco': 'Notificação (15 dias)' if mc['marco'] == 'notificacao'
                                 else 'Inicial (60 dias)', 'limite': mc['limite'], 'situacao': mc['situacao']})
        protocolo = coleta.comum.inicial_protocolada_em(caso)
        if protocolo and contrato:
            rapidez.append((protocolo - contrato).days)

    def taxa(marco):
        devidos = [m for m in marcos_todos if m['marco'] == marco and (m['feito_em'] or m['situacao'] == 'ESTOUROU')]
        no_prazo = [m for m in devidos if m['situacao'] == 'CUMPRIDO NO PRAZO']
        return len(no_prazo), len(devidos)

    ant = [a for v in pessoas.values() for a in v['antecedencia']]
    kpis = [
        ('Zero prazo perdido', 'SIM' if not perdidos else f'NÃO: {len(perdidos)} tarefa(s) de prazo vencida(s) '
                                                          'sem conclusão (conferir se foi protocolado)'),
        ('Liminares obtidas x negadas (semana)',
         f"{cat['LIMINAR_DEFERIDA']} x {cat['LIMINAR_INDEFERIDA']} "
         f"(índice {_pct(cat['LIMINAR_DEFERIDA'], cat['LIMINAR_DEFERIDA'] + cat['LIMINAR_INDEFERIDA'])})"),
        ('Decisões favoráveis x desfavoráveis (sentenças)',
         f"{cat['SENTENCA_FAVORAVEL']} x {cat['SENTENCA_DESFAVORAVEL']}"
         + (f" (+{cat['SENTENCA']} a conferir)" if cat['SENTENCA'] else '')),
        ('Antecedência média nos protocolos', f"{coleta.media(ant)} dia(s) antes do prazo" if ant else '-'),
        ('Rapidez da inicial (contrato → protocolo)', f"{coleta.media(rapidez)} dias em média" if rapidez else '-'),
        ('Notificação em até 15 dias do onboarding', '{} de {} ({})'.format(*taxa('notificacao'), _pct(*taxa('notificacao')))),
        ('Fase extrajudicial em até 60 dias (inicial)', '{} de {} ({})'.format(*taxa('inicial'), _pct(*taxa('inicial')))),
        ('Novos contratos na semana', f"{len(novos)}" + (f": {', '.join(novos[:6])}" if novos else '')),
        ('Leads e tempo de atendimento', '[PREENCHER na reunião: a API do Atende Direito usada hoje não traz esses '
                                         'números]'),
    ]
    return {'hoje': hoje, 'seg': seg, 'sex': sex, 'fim': fim, 'pessoas': dict(pessoas), 'tipos': tipos,
            'perdidos': perdidos, 'pubs': pubs, 'cat': cat, 'estouros': estouros, 'kpis': kpis,
            'sem_advbox': not coleta.comum.tem_advbox() and not exemplo}


def texto_whatsapp(d):
    prev = sum(v['previstas'] for v in d['pessoas'].values())
    feitas = sum(v['feitas'] for v in d['pessoas'].values())
    linhas = [f"AUDITORIA DA SEMANA {coleta.br(d['seg'])[:5]} a {coleta.br(d['fim'])[:5]}",
              f"Tarefas que venciam: {prev} | concluídas: {feitas} ({_pct(feitas, prev)})", '', 'Por pessoa:']
    for rot in sorted(d['pessoas'], key=coleta.ordem_pessoa):
        v = d['pessoas'][rot]
        if not (v['previstas'] or v['tempos']):
            continue
        linhas.append(f"- {rot}: {v['feitas']} de {v['previstas']} concluída(s), {len(v['nao_feitas'])} vencida(s) sem "
                      f"conclusão, {len(v['com_atraso'])} feita(s) com atraso, tempo médio "
                      f"{coleta.media(v['tempos']) or '-'} dia(s)")
    linhas += ['', 'Indicadores:'] + [f'- {k}: {v}' for k, v in d['kpis'][:7]]
    if d['estouros']:
        linhas += ['', 'Estouraram 15/60 dias:'] + [f"- {e['cliente']}: {e['marco']}" for e in d['estouros']]
    return '\n'.join(linhas)


def gerar(exemplo=False):
    print('\n=== GESTÃO: AUDITORIA DE SEXTA ===')
    d = levantar(exemplo)
    doc = novo_documento()
    titulo(doc, 'Auditoria da Semana')
    paragrafo(doc, f"Reunião de sexta · {coleta.br(d['seg'])} a {coleta.br(d['fim'])}"
                   + (' · DADOS FICTÍCIOS' if exemplo else ''), tamanho=10).alignment = 1
    if d['sem_advbox']:
        paragrafo(doc, 'ADVBOX sem credencial: as tarefas não entraram nesta auditoria. [CONFERIR]', tamanho=10)

    secao(doc, '1. Indicadores dos manuais')
    tabela(doc, ['Indicador', 'Semana'], [[k, v] for k, v in d['kpis']], [6.2, 9.5], tamanho=9)

    secao(doc, '2. Concluído x não concluído, por pessoa')
    linhas = []
    for rot in sorted(d['pessoas'], key=coleta.ordem_pessoa):
        v = d['pessoas'][rot]
        if not (v['previstas'] or v['tempos']):
            continue
        linhas.append([rot, str(v['previstas']), str(v['feitas']), str(len(v['nao_feitas'])),
                       str(len(v['com_atraso'])), str(coleta.media(v['tempos']) or '-')])
    if linhas:
        tabela(doc, ['Pessoa', 'Venciam', 'Concluídas', 'Pendentes', 'Com atraso', 'Tempo médio (dias)'], linhas,
               [5.2, 1.8, 2, 2, 2, 2.7], tamanho=9)
    else:
        paragrafo(doc, 'Sem tarefas do ADVBOX na semana.')
    pend = [(rot, t) for rot, v in d['pessoas'].items() for t in v['nao_feitas']]
    if pend:
        p = paragrafo(doc, 'tarefas que venciam na semana e não foram concluídas', rotulo='Pendentes', espaco=1.0)
        p.paragraph_format.space_before = Pt(6)
        tabela(doc, ['Pessoa', 'Tarefa', 'Prazo', 'Cliente'],
               [[rot, t['tipo'], coleta.br(t['prazo']), t['cliente'][:34]] for rot, t in pend], [5, 3.5, 2.4, 4.8],
               tamanho=8)
    atraso = [(rot, t, dias) for rot, v in d['pessoas'].items() for t, dias in v['com_atraso']]
    if atraso:
        paragrafo(doc, 'concluídas nesta semana depois do prazo', rotulo='Com atraso', espaco=1.0)
        tabela(doc, ['Pessoa', 'Tarefa', 'Prazo', 'Dias de atraso', 'Cliente'],
               [[rot, t['tipo'], coleta.br(t['prazo']), str(dias), t['cliente'][:30]] for rot, t, dias in atraso],
               [4.6, 3.3, 2.3, 1.9, 3.6], tamanho=8)

    secao(doc, '3. Tempo médio de conclusão por tipo de tarefa')
    if d['tipos']:
        tabela(doc, ['Tipo de tarefa', 'Concluídas', 'Tempo médio (dias)', 'Mediana (dias)'],
               [[k, str(len(v)), str(coleta.media(v) or '-'), str(coleta.mediana(v) or '-')]
                for k, v in sorted(d['tipos'].items(), key=lambda kv: -(coleta.media(kv[1]) or 0))],
               [7, 2.6, 3.1, 3], tamanho=9)
    else:
        paragrafo(doc, 'Nenhuma tarefa concluída na semana.')

    secao(doc, '4. Prazos: algum perdido?')
    if d['perdidos']:
        tabela(doc, ['Tarefa', 'Prazo', 'Cliente', 'Com quem'],
               [[t['tipo'], coleta.br(t['prazo']), t['cliente'][:32],
                 ', '.join(p['nome'] for p in t['pessoas'] if not p['concluida_em'])] for t in d['perdidos']],
               [3.6, 2.4, 5, 4.7], tamanho=8)
        paragrafo(doc, 'Tarefa de prazo vencida sem conclusão no ADVBOX: conferir no PJe se foi protocolado '
                       '(se sim, concluir a tarefa; se não, tratar como prazo perdido).', tamanho=9)
    else:
        paragrafo(doc, 'Nenhuma tarefa de prazo vencida sem conclusão. Zero prazo perdido na semana.')

    secao(doc, '5. Casos que estouraram 15 dias (notificação) ou 60 dias (inicial)')
    if d['estouros']:
        tabela(doc, ['Cliente', 'Marco', 'Limite', 'Situação'],
               [[e['cliente'], e['marco'], coleta.br(e['limite']), e['situacao']] for e in d['estouros']],
               [5.3, 4, 2.6, 3.8], tamanho=9)
    else:
        paragrafo(doc, 'Nenhum caso estourou os prazos internos.')

    secao(doc, '6. Publicações da semana (DJEN)')
    if d['cat']:
        tabela(doc, ['Tipo', 'Qtd.'], [[coleta.saidas_varredura.rotulos_categorias()[k], str(v)]
                                      for k, v in d['cat'].most_common()], [12.5, 3.2], tamanho=9)
    else:
        paragrafo(doc, 'Nenhuma varredura do DJEN salva na semana (rodar a Controladoria diariamente).')

    secao(doc, '7. Encaminhamentos')
    lista(doc, ['Quem: ______________   O quê: ________________________________   Até: ___/___'] * 3)
    p = paragrafo(doc, 'Auditoria montada automaticamente (ADVBOX, varreduras do DJEN e pastas dos clientes). '
                       'A API do ADVBOX não conclui tarefas: o que foi feito e não baixado aparece como pendente.',
                  tamanho=9)
    p.paragraph_format.space_before = Pt(12)

    pasta = coleta.pasta_gestao('auditoria')
    carimbo = f"{d['seg']:%Y-%m-%d}" + ('_EXEMPLO' if exemplo else '')
    docx = os.path.join(pasta, f'Auditoria da Semana {carimbo}.docx')
    doc.save(docx)
    txt = texto_whatsapp(d)
    with open(os.path.join(pasta, f'Auditoria da Semana {carimbo} - WhatsApp.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)
    print(f'\n   Documento: {docx}')
    return docx, txt, d

"""
PROCESSOS PARADOS - lista para o Coordenador Juridico destravar.

Processo ativo no ADVBOX, com numero, SEM movimentacao nos ultimos N dias (uma varredura
so de /last_movements numa janela de 2N dias: quem mexeu entre N e 2N mostra ha quantos
dias; quem nao mexeu nem assim aparece como "mais de 2N dias").

Para cada um, a possivel causa: tarefa aberta de custas/juntada/emenda/protocolo, ultima
publicacao classificada (ex.: custas) e a fase. Mais: casos ainda antes da acao que
travaram (regua de documentos esgotada, notificacao ou inicial fora do prazo interno).

Sai: DOCX no timbrado + CSV em SAIDA/controladoria/parados/.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classificador  # noqa: E402
import comum  # noqa: E402
import saidas_varredura  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402

TRAVA_TAREFA = re.compile(r'custa|juntad|emend|protocol|guia|document|pericia|honorario', re.I)

CAUSA_FASE = [
    (r'inicial|distribu|liminar', 'Inicial sem andamento: conferir custas, emenda, citação e se a liminar foi apreciada.'),
    (r'contest|replica', 'Conferir se a réplica foi protocolada e se falta intimação/decisão de saneamento.'),
    (r'instru|pericia|prova', 'Fase de provas: conferir honorários periciais, quesitos e se a perícia foi agendada.'),
    (r'senten|conclus', 'Concluso para sentença: se passar de 100 dias, avaliar petição pedindo julgamento.'),
    (r'recurs|tribunal|apela|agravo', 'No Tribunal: normal demorar; conferir contrarrazões e se há pauta.'),
    (r'execu|cumprimento', 'Execução/cumprimento parado: conferir penhora, embargos e suspensão por prejudicialidade.'),
]


def causa_pela_fase(fase):
    t = classificador.norm(fase)
    for rx, txt in CAUSA_FASE:
        if re.search(rx, t):
            return txt
    return 'Conferir no PJe o último ato e o que o processo espera.'


def tarefas_abertas(exemplo):
    hoje = comum.hoje()
    lista_t = comum.tarefas(exemplo, date_start=(hoje - timedelta(days=365)).isoformat(),
                            date_end=(hoje + timedelta(days=60)).isoformat())
    abertas = defaultdict(list)
    for t in lista_t or []:
        pend = [p for p in t['pessoas'] if not p['concluida_em']]
        if pend:
            t['pendentes'] = pend
            abertas[str(t['processo_id'])].append(t)
    return abertas


def levantar(dias, exemplo=False):
    hoje = comum.hoje()
    procs = comum.processos(exemplo)
    if procs is None:
        comum.aviso_sem_advbox('a lista de processos judiciais')
        return None, []
    ativos = [p for p in procs if comum.processo_ativo(p) and comum.digitos(p.get('process_number'))]
    movs = comum.movimentacoes(hoje - timedelta(days=2 * dias), hoje, exemplo) or []
    ultima = {}
    for m in movs:
        k = str(m['processo_id'])
        if k not in ultima or m['data'] > ultima[k]['data']:
            ultima[k] = m
    abertas = tarefas_abertas(exemplo)
    publicacoes = defaultdict(list)
    for i in saidas_varredura.historico(hoje - timedelta(days=2 * dias), hoje, exemplo):
        if i.get('advbox_processo_id'):
            publicacoes[str(i['advbox_processo_id'])].append(i)

    parados = []
    for p in ativos:
        k = str(p['id'])
        m = ultima.get(k)
        pubs_k = [comum.data(i['data_disponibilizacao']) for i in publicacoes.get(k, [])]
        pubs_k = [d for d in pubs_k if d]
        if pubs_k and (not m or max(pubs_k) > m['data']):  # publicacao no DJEN tambem e movimento
            m = {'data': max(pubs_k), 'descricao': 'publicação no DJEN'}
        parado_ha = (hoje - m['data']).days if m else None
        if m and parado_ha < dias:
            continue
        travas = [t for t in abertas.get(k, []) if TRAVA_TAREFA.search(t['tipo'] + ' ' + t['texto'])]
        causas = [f"Tarefa aberta: {t['tipo']} desde {comum.br(t['criada_em'])} "
                  f"({', '.join(x['nome'] for x in t['pendentes'])})" for t in travas]
        pubs = sorted(publicacoes.get(k, []), key=lambda i: comum.data(i['data_disponibilizacao']) or hoje)
        if pubs:
            causas.append(f"Última publicação: {pubs[-1]['rotulo']} em {pubs[-1]['data_disponibilizacao']}")
        causas.append(causa_pela_fase(p.get('stage') or ''))
        parados.append({
            'dias_parado': parado_ha if parado_ha is not None else f'mais de {2 * dias}',
            'ordem': parado_ha if parado_ha is not None else 10 ** 6,
            'processo': p.get('process_number'), 'cliente': comum.cliente_do_processo(p),
            'fase': p.get('stage') or '', 'responsavel': p.get('responsible') or '',
            'ultima_movimentacao': (f"{comum.br(m['data'])} - {m['descricao'][:80]}" if m else '-'),
            'tarefas_abertas': len(abertas.get(k, [])),
            'possivel_causa': ' | '.join(causas),
            'advbox_processo_id': p.get('id'),
        })
    parados.sort(key=lambda x: -x['ordem'])

    travados = []
    for base, caso in comum.casos(exemplo):
        motivos = []
        for mc in comum.marcos_do_caso(caso, hoje):
            if mc['situacao'] == 'ESTOUROU':
                motivos.append(f"{'Notificação' if mc['marco'] == 'notificacao' else 'Inicial'} fora do prazo "
                               f"interno (limite {comum.br(mc['limite'])})")
        if caso.get('alerta_gestor_em'):
            motivos.append('Régua de cobrança de documentos esgotada (3 mensagens)')
        falta = comum.documentos_faltando(caso)
        if falta and motivos:
            motivos.append(f'Faltam {len(falta)} documento(s)')
        if motivos:
            travados.append({'cliente': comum.nome_do_caso(caso), 'fase': comum.fase_do_caso(caso),
                             'contrato': caso.get('data_contrato_br') or comum.br(caso.get('data_contrato')),
                             'motivos': '; '.join(motivos), 'pasta': base})
    return parados, travados


def gerar(dias=30, exemplo=False):
    print(f'\n=== PROCESSOS PARADOS (sem movimentação há {dias}+ dias) ===')
    parados, travados = levantar(dias, exemplo)
    if parados is None:
        parados = []
    pasta = comum.pasta_saida('controladoria', 'parados')
    carimbo = datetime.now().strftime('%Y-%m-%d_%H%M') + ('_EXEMPLO' if exemplo else '')
    csv_ = comum.salvar_csv(os.path.join(pasta, f'{carimbo} - Parados.csv'), parados,
                            ['dias_parado', 'processo', 'cliente', 'fase', 'responsavel', 'ultima_movimentacao',
                             'tarefas_abertas', 'possivel_causa', 'advbox_processo_id'])

    doc = novo_documento()
    titulo(doc, 'Processos parados · para destravar')
    paragrafo(doc, f"{comum.br(comum.hoje())}{' (EXEMPLO FICTÍCIO)' if exemplo else ''} · critério: sem "
                   f"movimentação há {dias} dias ou mais", rotulo='Data', espaco=1.0)
    secao(doc, f'1. Processos judiciais parados ({len(parados)})')
    if parados:
        tabela(doc, ['Dias', 'Processo', 'Cliente', 'Fase', 'Responsável', 'Possível causa / o que conferir'],
               [[str(p['dias_parado']), p['processo'], p['cliente'][:30], p['fase'][:25], p['responsavel'][:22],
                 p['possivel_causa']] for p in parados], [1.1, 3.3, 2.6, 2.2, 2, 4.5], tamanho=8)
    else:
        paragrafo(doc, 'Nenhum processo parado (ou ADVBOX sem credencial: ver o aviso na tela).')
    secao(doc, f'2. Casos antes da ação travados ({len(travados)})')
    if travados:
        tabela(doc, ['Cliente', 'Fase', 'Contrato', 'Motivo'],
               [[t['cliente'], t['fase'], t['contrato'], t['motivos']] for t in travados], [4, 3.3, 2.2, 6.2], tamanho=9)
    else:
        paragrafo(doc, 'Nenhum caso travado nas pastas dos clientes.')
    lista(doc, ['Falta de custas e de juntada são as causas mais comuns: o Coordenador confere no PJe e distribui.',
                'Processo em fase de sentença ou no Tribunal pode estar parado por fila do Judiciário: '
                'registrar no ADVBOX quando foi conferido.'], tamanho=10)
    docx = os.path.join(pasta, f'{carimbo} - Parados.docx')
    doc.save(docx)

    for p in parados[:15]:
        print(f"   {str(p['dias_parado']):>8} dias | {p['processo']} | {p['cliente'][:28]} | {p['possivel_causa'][:70]}")
    for t in travados:
        print(f"   ANTES DA AÇÃO | {t['cliente'][:28]} | {t['motivos'][:90]}")
    print(f'\n   {len(parados)} processo(s) parado(s); {len(travados)} caso(s) travado(s) antes da ação.')
    print(f'   Relatório: {docx}\n   Planilha:  {csv_}')
    return parados, travados

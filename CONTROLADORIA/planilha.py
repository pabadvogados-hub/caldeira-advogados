"""
PLANILHA DE ATUALIZACAO INDIVIDUAL DE CLIENTES (reuniao operacional).

Uma linha por processo ativo do ADVBOX + uma por caso ainda antes da acao (pastas dos
clientes). Colunas: cliente, processo, banco, fase, gravidade, travado?, motivo, proxima
acao, responsavel, prazos, ultima movimentacao, tarefas abertas, documentos faltando.

Criterios (tambem na aba LEGENDA):
  ALTA  = prazo fatal/interno em ate 5 dias uteis, tarefa atrasada, ou publicacao grave recente
          (liminar negada, execucao/penhora, sentenca desfavoravel), ou marco 15/60 dias estourado;
  MEDIA = travado ou algo vencendo em ate 15 dias;  BAIXA = o resto.
  TRAVADO = sem movimentacao ha DIAS_PARADO dias, tarefa de custas/juntada aberta, tarefa
          atrasada ha mais de 10 dias, regua de documentos esgotada ou marco estourado.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum  # noqa: E402
import parados  # noqa: E402
import prazos  # noqa: E402
import saidas_varredura  # noqa: E402
from avisos import nome_proprio  # noqa: E402
from configuracao import DIAS_PARADO, VISUAL_PLANILHA  # noqa: E402

GRAVES = ('LIMINAR_INDEFERIDA', 'EXECUCAO_PENHORA', 'SENTENCA_DESFAVORAVEL', 'SENTENCA', 'CUSTAS_EMENDA')
COLUNAS = [('Cliente', 30), ('Processo', 27), ('Banco', 26), ('Fase', 24), ('Gravidade', 10), ('Travado?', 9),
           ('Motivo da trava', 38), ('Próxima ação', 46), ('Responsável', 24), ('Prazo interno', 12),
           ('Prazo fatal', 12), ('Última movimentação', 34), ('Dias sem mov.', 10), ('Tarefas abertas', 10),
           ('Documentos faltando', 34), ('Origem', 14)]


def _linhas(exemplo=False):
    hoje = comum.hoje()
    procs = comum.processos(exemplo)
    if procs is None:
        comum.aviso_sem_advbox('os processos judiciais (a planilha sai só com os casos das pastas)')
        procs = []
    ativos = [p for p in procs if comum.processo_ativo(p)]
    movs = comum.movimentacoes(hoje - timedelta(days=2 * DIAS_PARADO), hoje, exemplo) or []
    ultima = {}
    for m in movs:
        k = str(m['processo_id'])
        if k not in ultima or m['data'] > ultima[k]['data']:
            ultima[k] = m
    abertas = parados.tarefas_abertas(exemplo) if procs else defaultdict(list)
    pubs = defaultdict(list)
    for i in saidas_varredura.historico(hoje - timedelta(days=90), hoje, exemplo):
        if i.get('advbox_processo_id'):
            pubs[str(i['advbox_processo_id'])].append(i)
    casos = comum.casos(exemplo)
    caso_por_proc = {str((c.get('advbox') or {}).get('processo_id')): (b, c) for b, c in casos
                     if (c.get('advbox') or {}).get('processo_id')}

    linhas = []
    usados = set()
    for p in ativos:
        k = str(p['id'])
        if not comum.digitos(p.get('process_number')) and k in caso_por_proc:
            continue  # ainda antes da acao: entra pela pasta do cliente, com os marcos 15/60
        caso = caso_por_proc.get(k, (None, {}))[1]
        if caso:
            usados.add(id(caso))
        m = ultima.get(k)
        publicadas = sorted(pubs.get(k, []), key=lambda i: i.get('data_disponibilizacao') or '')
        if publicadas:
            d_pub = comum.data(publicadas[-1]['data_disponibilizacao'])
            if d_pub and (not m or d_pub > m['data']):
                m = {'data': d_pub, 'descricao': f"DJEN: {publicadas[-1]['rotulo']}"}
        dias_sem = (hoje - m['data']).days if m else None
        tarefas = abertas.get(k, [])
        atrasadas = [t for t in tarefas if t['prazo'] and comum.data(t['prazo']) < hoje]
        motivos = []
        if dias_sem is None or dias_sem >= DIAS_PARADO:
            motivos.append(f"sem movimentação há {dias_sem if dias_sem is not None else f'+{2 * DIAS_PARADO}'} dias")
        for t in tarefas:
            if parados.TRAVA_TAREFA.search(t['tipo']) and t in atrasadas:
                motivos.append(f"{t['tipo'].lower()} atrasada desde {comum.br(t['prazo'])}")
        if any((hoje - comum.data(t['prazo'])).days > 10 for t in atrasadas):
            motivos.append('tarefa atrasada há mais de 10 dias')
        # proxima acao = o que vence primeiro (tarefa aberta ou publicacao com prazo)
        candidatos = [(comum.data(t['prazo']) or hoje + timedelta(days=999), f"{t['tipo']} (tarefa ADVBOX)", None,
                       ', '.join(x['nome'] for x in t['pendentes'])) for t in tarefas]
        for i in publicadas:
            if i.get('interno_iso') and i.get('prazo_nosso') != 'NÃO':
                candidatos.append((comum.data(i['interno_iso']), f"{i['rotulo']}: {i['peca'] or i['providencia'][:60]}",
                                   comum.data(i['fatal_iso']), i['responsavel']))
        candidatos.sort(key=lambda c: c[0])
        prox = candidatos[0] if candidatos else None
        restantes = prazos.dias_uteis_entre(hoje, prox[0]) if prox and prox[0] else None
        grave = any(i['categoria'] in GRAVES for i in publicadas[-3:])
        if (restantes is not None and restantes <= 5) or atrasadas or grave:
            gravidade = 'ALTA'
        elif motivos or (restantes is not None and restantes <= 15):
            gravidade = 'MEDIA'
        else:
            gravidade = 'BAIXA'
        banco = p.get('parte_contraria') or next((i['parte_contraria'] for i in publicadas if i.get('parte_contraria')), '')
        if not banco and caso:
            banco = ', '.join(sorted({o.get('banco') for o in (caso.get('triagem') or {}).get('operacoes') or []
                                      if o.get('banco')}))
        falta = [s['nome'] for s in comum.documentos_faltando(caso)] if caso else []
        linhas.append([
            comum.cliente_do_processo(p), p.get('process_number') or '', nome_proprio(banco), p.get('stage') or '',
            gravidade, 'SIM' if motivos else 'NÃO', '; '.join(dict.fromkeys(motivos)),
            prox[1] if prox else '[PREENCHER: próxima ação]', (prox[3] if prox and prox[3] else p.get('responsible') or ''),
            comum.br(prox[0]) if prox and prox[0] and prox[0].year < 2900 else '',
            comum.br(prox[2]) if prox and prox[2] else '',
            f"{comum.br(m['data'])} - {m['descricao'][:60]}" if m else '-',
            dias_sem if dias_sem is not None else f'+{2 * DIAS_PARADO}', len(tarefas), '; '.join(falta), 'ADVBOX'])

    for base, caso in casos:
        if id(caso) in usados:
            continue
        marcos = comum.marcos_do_caso(caso, hoje)
        pend = [mc for mc in marcos if not mc['feito_em']]
        motivos = [f"{'notificação' if mc['marco'] == 'notificacao' else 'inicial'} fora do prazo interno"
                   for mc in pend if mc['situacao'] == 'ESTOUROU']
        if caso.get('alerta_gestor_em'):
            motivos.append('régua de documentos esgotada')
        prox = pend[0] if pend else None
        if motivos or (prox and prox['dias_restantes'] <= 5):
            gravidade = 'ALTA'
        elif prox and prox['dias_restantes'] <= 15:
            gravidade = 'MEDIA'
        else:
            gravidade = 'BAIXA'
        acao = {'notificacao': 'Enviar a notificação extrajudicial ao banco',
                'inicial': 'Protocolar a petição inicial'}.get(prox['marco'], '') if prox else 'Acompanhar'
        resp = {'notificacao': 'Adv. Extrajudicial', 'inicial': 'Adv. Judicial'}.get(prox['marco'], '') if prox else ''
        bancos = ', '.join(sorted({nome_proprio(o.get('banco')) for o in (caso.get('triagem') or {}).get('operacoes') or []
                                   if o.get('banco')}))
        linhas.append([
            comum.nome_do_caso(caso), '(antes da ação)', bancos, comum.fase_do_caso(caso), gravidade,
            'SIM' if motivos else 'NÃO', '; '.join(motivos), acao, resp, comum.br(prox['limite']) if prox else '',
            '', f"contrato {caso.get('data_contrato_br') or comum.br(caso.get('data_contrato'))}", '', '',
            '; '.join(s['nome'] for s in comum.documentos_faltando(caso)), 'Pasta do cliente'])
    ordem = {'ALTA': 0, 'MEDIA': 1, 'BAIXA': 2}
    linhas.sort(key=lambda l_: (ordem[l_[4]], l_[5] != 'SIM', l_[9][6:] + l_[9][3:5] + l_[9][:2] if l_[9] else '9', l_[0]))
    return linhas


def gerar(exemplo=False):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    print('\n=== PLANILHA DE ATUALIZAÇÃO DOS CLIENTES ===')
    linhas = _linhas(exemplo)
    wb = Workbook()
    ws = wb.active
    ws.title = 'CLIENTES'
    cor = VISUAL_PLANILHA
    fino = Side(style='thin', color='D9D9D9')
    ws.append([c for c, _ in COLUNAS])
    for n, (_, largura) in enumerate(COLUNAS, 1):
        cel = ws.cell(row=1, column=n)
        cel.font = Font(bold=True, color='FFFFFF')
        cel.fill = PatternFill('solid', fgColor=cor['cabecalho'])
        cel.alignment = Alignment(wrap_text=True, vertical='center')
        ws.column_dimensions[get_column_letter(n)].width = largura
    for linha in linhas:
        ws.append(linha)
        r = ws.max_row
        for n in range(1, len(COLUNAS) + 1):
            c = ws.cell(row=r, column=n)
            c.alignment = Alignment(wrap_text=True, vertical='top')
            c.border = Border(bottom=fino)
        grav = ws.cell(row=r, column=5)
        grav.fill = PatternFill('solid', fgColor=cor.get(linha[4], 'FFFFFF'))
        grav.font = Font(bold=True)
        if linha[5] == 'SIM':
            ws.cell(row=r, column=6).font = Font(bold=True, color='C00000')
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(COLUNAS))}{max(1, ws.max_row)}'
    ws.row_dimensions[1].height = 30

    leg = wb.create_sheet('LEGENDA')
    for txt in [
        'COMO LER ESTA PLANILHA',
        'Gravidade ALTA: prazo em até 5 dias úteis, tarefa atrasada, publicação grave recente (liminar negada, '
        'execução/penhora, sentença desfavorável, custas) ou marco de 15/60 dias estourado.',
        'Gravidade MÉDIA: travado ou com algo vencendo em até 15 dias. BAIXA: o restante.',
        f'Travado: sem movimentação há {DIAS_PARADO}+ dias, tarefa de custas/juntada atrasada, tarefa atrasada há '
        'mais de 10 dias, régua de documentos esgotada ou marco estourado.',
        'Próxima ação: o que vence primeiro entre as tarefas abertas do ADVBOX e as publicações do DJEN com prazo.',
        'Prazo fatal: cálculo PRELIMINAR da Controladoria (conferir no processo).',
        'Fonte: ADVBOX (processos, tarefas, movimentações), varreduras do DJEN e caso.json das pastas.',
        f'Gerada em {comum.br(comum.hoje())}' + (' com DADOS FICTÍCIOS (--exemplo).' if exemplo else '.'),
    ]:
        leg.append([txt])
    leg.column_dimensions['A'].width = 130
    leg['A1'].font = Font(bold=True, color=cor['cabecalho'], size=13)

    pasta = comum.pasta_saida('controladoria', 'planilhas')
    nome = f"Atualizacao de Clientes - {comum.hoje():%Y-%m-%d}{'_EXEMPLO' if exemplo else ''}.xlsx"
    caminho = os.path.join(pasta, nome)
    wb.save(caminho)
    from collections import Counter
    c = Counter(l_[4] for l_ in linhas)
    print(f"   {len(linhas)} linha(s): ALTA {c['ALTA']} | MÉDIA {c['MEDIA']} | BAIXA {c['BAIXA']} | "
          f"travados {sum(1 for l_ in linhas if l_[5] == 'SIM')}")
    print(f'   Planilha: {caminho}')
    return caminho

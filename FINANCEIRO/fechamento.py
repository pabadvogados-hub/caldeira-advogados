"""
Fechamento mensal: recebidos no Asaas x lancamentos do ADVBOX.

  python FINANCEIRO/main.py fechamento 09/2026
  python FINANCEIRO/main.py fechamento              (sem mes = mes anterior; usado no agendamento)
  python FINANCEIRO/main.py fechamento 09/2026 --exemplo

Fonte da verdade: ADVBOX (receitas e despesas pelo VENCIMENTO no mes).
Asaas: cobrancas pela DATA DE PAGAMENTO no mes.
Saidas em SAIDA/FINANCEIRO/FECHAMENTO/AAAA-MM/: planilha (abas) + resumo .docx no timbrado.
So leitura: nada e lancado nem alterado no ADVBOX ou no Asaas.
Regras (comissoes, exclusoes, distribuicao de lucros): config/regras_financeiras.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402
import exemplo as ex  # noqa: E402
from config import regras_financeiras as regras  # noqa: E402


# ============================================================
# PERIODO
# ============================================================

def mes_anterior(hoje=None):
    h = (hoje or date.today()).replace(day=1) - timedelta(days=1)
    return f'{h.month:02d}/{h.year}'


def periodo(competencia):
    try:
        mes, ano = (int(x) for x in competencia.split('/'))
        inicio = date(ano, mes, 1)
    except (ValueError, AttributeError):
        raise SystemExit(f'ERRO: competencia invalida "{competencia}". Use MM/AAAA, ex.: 09/2026')
    fim = (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))
    return ano, mes, inicio, fim


# ============================================================
# DADOS
# ============================================================

def _recebido(p, clientes):
    cli = clientes.get(p.get('customer')) or {}
    bruto, liquido = c.num(p.get('value')), c.num(p.get('netValue') or p.get('value'))
    return {'id': p.get('id'), 'nome': cli.get('name') or '(sem nome no Asaas)', 'valor': bruto,
            'liquido': liquido, 'taxa': round(bruto - liquido, 2), 'vencimento': p.get('dueDate'),
            'pagamento': p.get('paymentDate') or p.get('clientPaymentDate') or p.get('confirmedDate'),
            'descricao': p.get('description') or '', 'status': p.get('status')}


def _lancamento(t):
    return {'id': t.get('id'), 'tipo': 'receita' if t.get('entry_type') == 'income' else 'despesa',
            'nome': t.get('name') or '', 'valor': c.num(t.get('amount')), 'vencimento': t.get('date_due'),
            'pagamento': t.get('date_payment'), 'categoria': t.get('category') or 'SEM CATEGORIA',
            'descricao': t.get('description') or ''}


def carregar(ano, mes, inicio, fim, exemplo):
    """Retorna dict com recebidos (Asaas), lancamentos (ADVBOX) e a pagar; None onde nao ha credencial."""
    hoje = date.today()
    if exemplo:
        clientes = c.ClientesAsaas(ex.CLIENTES)
        return {'recebidos': [_recebido(p, clientes) for p in ex.recebidos_do_mes(ano, mes)],
                'lancamentos': [_lancamento(t) for t in ex.transacoes_advbox(ano, mes)],
                'a_pagar': [_lancamento(t) for t in ex.a_pagar_14_dias(hoje)]}
    dados = {'recebidos': None, 'lancamentos': None, 'a_pagar': None}
    if c.asaas_configurado():
        print(f'Asaas: cobrancas pagas de {c.data_br(inicio)} a {c.data_br(fim)}...')
        clientes = c.ClientesAsaas()
        dados['recebidos'] = [_recebido(p, clientes) for p in c.cobrancas_recebidas(inicio.isoformat(), fim.isoformat())]
    else:
        print('Asaas: sem ASAAS_API_TOKEN, recebimentos nao consultados.')
    if c.advbox_configurado():
        from advbox_integration import listar_transacoes
        print(f'ADVBOX: lancamentos com vencimento de {c.data_br(inicio)} a {c.data_br(fim)}...')
        dados['lancamentos'] = [_lancamento(t) for t in listar_transacoes(
            {'date_due_start': inicio.isoformat(), 'date_due_end': fim.isoformat()})]
        dados['a_pagar'] = [_lancamento(t) for t in listar_transacoes(
            {'date_due_start': hoje.isoformat(), 'date_due_end': (hoje + timedelta(days=14)).isoformat()})]
    else:
        print('ADVBOX: sem ADVBOX_API_TOKEN, lancamentos nao consultados.')
    return dados


# ============================================================
# CONCILIACAO ASAAS x ADVBOX
# ============================================================

def _perto(datas_a, datas_b, tolerancia):
    da = [c.para_data(x) for x in datas_a if x]
    db = [c.para_data(x) for x in datas_b if x]
    da, db = [x for x in da if x], [x for x in db if x]
    if not da or not db:
        return True
    return any(abs((x - y).days) <= tolerancia or (x.year, x.month) == (y.year, y.month) for x in da for y in db)


def conciliar(recebidos, receitas):
    tol = regras.TOLERANCIA_DIAS_CONCILIACAO
    usados, linhas = set(), []
    pendentes = []
    for a in recebidos:
        par = next((b for b in receitas if b['id'] not in usados and abs(a['valor'] - b['valor']) <= 0.01
                    and c.nomes_parecidos(a['nome'], b['nome'])
                    and _perto((a['pagamento'], a['vencimento']), (b['vencimento'], b['pagamento']), tol)), None)
        if par:
            usados.add(par['id'])
            linhas.append(('CONCILIADO', a, par, 'OK'))
        else:
            pendentes.append(a)
    for a in pendentes:
        cand = [b for b in receitas if b['id'] not in usados and abs(a['valor'] - b['valor']) <= 0.01
                and _perto((a['pagamento'], a['vencimento']), (b['vencimento'], b['pagamento']), tol)]
        if len(cand) == 1:
            usados.add(cand[0]['id'])
            linhas.append(('CONFERIR', a, cand[0], 'Mesmo valor e data, nome diferente: confirmar se e o mesmo cliente'))
        else:
            linhas.append(('SO NO ASAAS', a, None,
                           'Recebido no Asaas sem receita no ADVBOX com vencimento no mes: lancar ou dar baixa no ADVBOX'))
    for b in receitas:
        if b['id'] in usados:
            continue
        if b['pagamento']:
            acao = 'Baixado no ADVBOX sem recebimento no Asaas: conferir no extrato do banco (PIX/deposito direto?)'
        else:
            acao = 'Receita em aberto no ADVBOX (sem pagamento): cobrar ou ajustar o lancamento'
        linhas.append(('SO NO ADVBOX', None, b, acao))
    return linhas


# ============================================================
# ANALISE
# ============================================================

def analisar(dados):
    recebidos = dados['recebidos'] or []
    lanc = dados['lancamentos']
    r = {'tem_advbox': lanc is not None, 'tem_asaas': dados['recebidos'] is not None,
         'asaas_bruto': sum(x['valor'] for x in recebidos), 'asaas_liquido': sum(x['liquido'] for x in recebidos),
         'asaas_taxas': sum(x['taxa'] for x in recebidos), 'asaas_qtd': len(recebidos), '_recebidos': recebidos}
    lanc = lanc or []
    receitas_todas = [x for x in lanc if x['tipo'] == 'receita']
    receitas = [x for x in receitas_todas if not regras.excluir_do_faturamento(x['nome'] + ' ' + x['descricao'])]
    despesas = [x for x in lanc if x['tipo'] == 'despesa']
    distrib = [x for x in despesas if regras.eh_distribuicao(x['categoria'])]
    operacionais = [x for x in despesas if not regras.eh_distribuicao(x['categoria'])]
    r.update({
        'receitas': receitas, 'receitas_excluidas': [x for x in receitas_todas if x not in receitas],
        'despesas': despesas, 'operacionais': operacionais, 'distribuicao_itens': distrib,
        'receita': sum(x['valor'] for x in receitas),
        'receita_recebida': sum(x['valor'] for x in receitas if x['pagamento']),
        'despesa_operacional': sum(x['valor'] for x in operacionais),
        'despesa_paga': sum(x['valor'] for x in operacionais if x['pagamento']),
        'distribuicao': sum(x['valor'] for x in distrib),
    })
    if not r['tem_advbox'] and r['tem_asaas']:
        r['receita'] = r['receita_recebida'] = r['asaas_bruto']   # sem ADVBOX: so o que entrou no Asaas
    r['receita_aberta'] = r['receita'] - r['receita_recebida']
    r['lucro'] = r['receita'] - r['despesa_operacional']
    r['pct_despesa'] = (r['despesa_operacional'] / r['receita'] * 100) if r['receita'] else 0.0
    r['margem'] = (r['lucro'] / r['receita'] * 100) if r['receita'] else 0.0
    r['apos_distribuicao'] = r['lucro'] - r['distribuicao']
    categorias = defaultdict(float)
    for x in operacionais:
        categorias[x['categoria']] += x['valor']
    r['categorias'] = sorted(categorias.items(), key=lambda kv: -kv[1])
    r['a_pagar'] = sorted([x for x in (dados['a_pagar'] or []) if x['tipo'] == 'despesa' and not x['pagamento']],
                          key=lambda x: x['vencimento'] or '')
    r['comissoes'] = []
    for a in recebidos:
        for chave in regras.comissao_da_cobranca(a['descricao'], a['nome']):
            regra = regras.COMISSOES[chave]
            r['comissoes'].append({'chave': chave, 'rotulo': regra.get('rotulo', chave), 'cliente': a['nome'],
                                   'base': a['valor'], 'percentual': regra.get('percentual', 0),
                                   'valor': round(a['valor'] * regra.get('percentual', 0), 2),
                                   'pagamento': a['pagamento']})
    return r


def indicadores(r):
    base = 'ADVBOX (por vencimento)' if r['tem_advbox'] else 'Asaas (sem ADVBOX) [CONFERIR]'
    return [
        (f'Receita do mês - {base}', r['receita']),
        ('   já recebida', r['receita_recebida']),
        ('   em aberto', r['receita_aberta']),
        ('Despesas operacionais', r['despesa_operacional']),
        ('   já pagas', r['despesa_paga']),
        ('Resultado operacional (receita - despesas operacionais)', r['lucro']),
        ('% despesa / receita', c.pct(r['pct_despesa'])),
        ('Margem', c.pct(r['margem'])),
        ('Distribuição de lucros (não é despesa operacional)', r['distribuicao']),
        ('Resultado após distribuição', r['apos_distribuicao']),
        ('Asaas - recebido bruto no mês', r['asaas_bruto']),
        ('Asaas - taxas', r['asaas_taxas']),
        ('Asaas - recebido líquido', r['asaas_liquido']),
    ]


# ============================================================
# SAIDAS
# ============================================================

def planilha(r, conc, nome_mes, ano, pasta):
    wb = c.planilha_nova()
    topo = f'FECHAMENTO {nome_mes}/{ano} - {c.NOME_ESCRITORIO}'
    c.aba(wb, 'RESUMO', ['Indicador', 'Valor'], [[k, v] for k, v in indicadores(r)], [58, 18],
          colunas_moeda=(1,), titulo_topo=topo)
    c.aba(wb, 'CONCILIACAO',
          ['Situacao', 'Cliente (Asaas)', 'Valor Asaas', 'Pago no Asaas', 'Cliente (ADVBOX)', 'Valor ADVBOX',
           'Venc. ADVBOX', 'Baixa ADVBOX', 'ID Asaas', 'ID ADVBOX', 'O que fazer'],
          [[s, a['nome'] if a else '', a['valor'] if a else None, c.data_br(a['pagamento']) if a else '',
            b['nome'] if b else '', b['valor'] if b else None, c.data_br(b['vencimento']) if b else '',
            c.data_br(b['pagamento']) if b and b['pagamento'] else '', a['id'] if a else '', b['id'] if b else '', o]
           for s, a, b, o in conc],
          [14, 32, 13, 12, 32, 13, 12, 12, 16, 10, 70], colunas_moeda=(2, 5))
    c.aba(wb, 'RECEBIDOS ASAAS', ['Pagamento', 'Vencimento', 'Cliente', 'Descricao', 'Bruto', 'Liquido', 'Taxa',
                                  'Status', 'ID'],
          [[c.data_br(a['pagamento']), c.data_br(a['vencimento']), a['nome'], a['descricao'], a['valor'],
            a['liquido'], a['taxa'], a['status'], a['id']] for a in r['_recebidos']],
          [12, 12, 32, 40, 13, 13, 10, 16, 18], colunas_moeda=(4, 5, 6))
    c.aba(wb, 'RECEITAS ADVBOX', ['Vencimento', 'Baixa', 'Cliente', 'Categoria', 'Descricao', 'Valor', 'Situacao'],
          [[c.data_br(x['vencimento']), c.data_br(x['pagamento']) if x['pagamento'] else '', x['nome'], x['categoria'],
            x['descricao'], x['valor'], 'RECEBIDA' if x['pagamento'] else 'EM ABERTO'] for x in r['receitas']] +
          [[c.data_br(x['vencimento']), '', x['nome'], x['categoria'], x['descricao'], x['valor'],
            'EXCLUIDA DO FATURAMENTO (regra)'] for x in r['receitas_excluidas']],
          [12, 12, 32, 24, 40, 13, 30], colunas_moeda=(5,))
    c.aba(wb, 'DESPESAS ADVBOX', ['Vencimento', 'Baixa', 'Favorecido', 'Categoria', 'Descricao', 'Valor', 'Tipo',
                                  'Situacao'],
          [[c.data_br(x['vencimento']), c.data_br(x['pagamento']) if x['pagamento'] else '', x['nome'], x['categoria'],
            x['descricao'], x['valor'], 'DISTRIBUICAO DE LUCROS' if regras.eh_distribuicao(x['categoria'])
            else 'OPERACIONAL', 'PAGA' if x['pagamento'] else 'EM ABERTO'] for x in r['despesas']],
          [12, 12, 28, 24, 40, 13, 24, 12], colunas_moeda=(5,))
    c.aba(wb, 'DESPESAS POR CATEGORIA', ['Categoria', 'Valor', '% da receita'],
          [[k, round(v, 2), c.pct((v / r['receita'] * 100) if r['receita'] else 0)] for k, v in r['categorias']],
          [36, 14, 14], colunas_moeda=(1,))
    if r['comissoes']:
        c.aba(wb, 'COMISSOES (CONFERIR)', ['Comissionado', 'Cliente', 'Pago em', 'Base', '%', 'Comissao'],
              [[x['rotulo'], x['cliente'], c.data_br(x['pagamento']), x['base'], c.pct(x['percentual'] * 100),
                x['valor']] for x in r['comissoes']], [26, 32, 12, 13, 8, 13], colunas_moeda=(3, 5))
    c.aba(wb, 'A PAGAR 14 DIAS', ['Vencimento', 'Favorecido', 'Categoria', 'Descricao', 'Valor'],
          [[c.data_br(x['vencimento']), x['nome'], x['categoria'], x['descricao'], x['valor']] for x in r['a_pagar']],
          [12, 30, 24, 40, 13], colunas_moeda=(4,))
    return c.salvar_planilha(wb, os.path.join(pasta, f'Fechamento {ano}-{nome_mes}.xlsx'))


def resumo_docx(r, conc, nome_mes, ano, pasta):
    from docx_caldeira import lista, novo_documento, paragrafo, secao, tabela, titulo
    doc = novo_documento()
    titulo(doc, f'Fechamento financeiro - {nome_mes}/{ano}')
    paragrafo(doc, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} para conferência do Financeiro. "
                   'Fonte da verdade: lançamentos do ADVBOX pelo vencimento; Asaas pela data de pagamento. '
                   'Nada foi lançado ou alterado nos sistemas.')
    if not r['tem_advbox']:
        paragrafo(doc, '[CONFERIR] ADVBOX não consultado (sem credencial): receita calculada só pelo Asaas '
                       'e despesas zeradas.')
    secao(doc, '1. Resultado do mês')
    tabela(doc, ['Indicador', 'Valor'],
           [[k, v if isinstance(v, str) else c.moeda(v)] for k, v in indicadores(r)], [11.5, 4.2])
    secao(doc, '2. Despesas operacionais por categoria')
    if r['categorias']:
        tabela(doc, ['Categoria', 'Valor', '% da receita'],
               [[k, c.moeda(v), c.pct((v / r['receita'] * 100) if r['receita'] else 0)] for k, v in r['categorias']],
               [9, 3.5, 3.2])
    else:
        paragrafo(doc, 'Nenhuma despesa lançada no período.')
    secao(doc, '3. Conciliação Asaas x ADVBOX')
    cont = defaultdict(int)
    for s, *_ in conc:
        cont[s] += 1
    paragrafo(doc, ' | '.join(f'{k}: {v}' for k, v in sorted(cont.items())) or 'Sem lançamentos para conciliar.')
    pend = [(s, a, b, o) for s, a, b, o in conc if s != 'CONCILIADO']
    if pend:
        tabela(doc, ['Situação', 'Cliente', 'Valor', 'O que fazer'],
               [[s, (a or b)['nome'], c.moeda((a or b)['valor']), o] for s, a, b, o in pend], [2.6, 4.2, 2.4, 6.5], tamanho=8)
    secao(doc, '4. Comissões')
    if r['comissoes']:
        tot = defaultdict(float)
        for x in r['comissoes']:
            tot[x['rotulo']] += x['valor']
        tabela(doc, ['Comissionado', 'Total do mês'], [[k, c.moeda(v)] for k, v in tot.items()], [10, 5.7])
        paragrafo(doc, 'Valores calculados só para conferência; o lançamento no ADVBOX continua manual.')
    else:
        paragrafo(doc, 'Nenhuma regra de comissão cadastrada (config/regras_financeiras.py).')
    secao(doc, '5. Contas a pagar nas próximas 2 semanas')
    if r['a_pagar']:
        tabela(doc, ['Vencimento', 'Favorecido', 'Categoria', 'Valor'],
               [[c.data_br(x['vencimento']), x['nome'], x['categoria'], c.moeda(x['valor'])] for x in r['a_pagar']],
               [2.6, 5.5, 4.4, 3.2])
    else:
        paragrafo(doc, 'Nenhuma despesa em aberto no período (ou ADVBOX não consultado).')
    secao(doc, 'Observações')
    lista(doc, ['Distribuição de lucros aparece separada e não entra no % de despesa nem no resultado operacional.',
                'Regras de comissão e de exclusão de faturamento: config/regras_financeiras.py '
                '(vazias até o escritório definir).',
                'Este resumo não substitui a contabilidade do escritório.'])
    arq = os.path.join(pasta, f'Fechamento {ano}-{nome_mes} - Resumo.docx')
    doc.save(arq)
    return arq


def executar(competencia=None, exemplo=False, saida=None):
    competencia = competencia or mes_anterior()
    ano, mes, inicio, fim = periodo(competencia)
    nome_mes = c.MESES[mes]
    c.cabecalho_execucao(f'FECHAMENTO MENSAL {nome_mes}/{ano}', exemplo)
    if not exemplo and not (c.asaas_configurado() or c.advbox_configurado()):
        print('Modo seguro: sem ASAAS_API_TOKEN e sem ADVBOX_API_TOKEN no config/.env. Nada consultado.')
        print(f'Para ver como funciona: python FINANCEIRO/main.py fechamento {competencia} --exemplo')
        return None
    dados = carregar(ano, mes, inicio, fim, exemplo)
    r = analisar(dados)
    conc =conciliar(dados['recebidos'] or [], r['receitas']) if dados['recebidos'] is not None \
        and dados['lancamentos'] is not None else []

    print('')
    for k, v in indicadores(r):
        print(f"  {k:58} {v if isinstance(v, str) else c.moeda(v):>16}")
    if conc:
        cont = defaultdict(int)
        for s, *_ in conc:
            cont[s] += 1
        print('\n  Conciliacao: ' + ' | '.join(f'{k} {v}' for k, v in sorted(cont.items())))
        for s, a, b, o in conc:
            if s != 'CONCILIADO':
                x = a or b
                print(f"    [{s}] {x['nome'][:34]:34} {c.moeda(x['valor']):>14}  {o}")
    else:
        print('\n  Conciliacao nao feita: precisa do Asaas E do ADVBOX.')
    if not regras.COMISSOES:
        print('  Comissoes: nenhuma regra cadastrada (config/regras_financeiras.py).')

    pasta = c.pasta_saida(saida, 'FECHAMENTO', f'{ano}-{mes:02d}')
    xlsx = planilha(r, conc, nome_mes, ano, pasta)
    docx = resumo_docx(r, conc, nome_mes, ano, pasta)
    print(f'\nPlanilha: {xlsx}\nResumo:   {docx}')
    return r

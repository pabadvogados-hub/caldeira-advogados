"""
Relatorio de inadimplencia: todas as cobrancas VENCIDAS do Asaas, por cliente.

  python FINANCEIRO/main.py inadimplencia            (so leitura; XLSX em SAIDA/FINANCEIRO/INADIMPLENCIA)
  python FINANCEIRO/main.py inadimplencia --exemplo

Mostra: cliente, valor em aberto, dias de atraso, se ainda esta na regua automatica,
se esta na lista de nao cobrar, e o total por faixa de atraso. Nada e enviado.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import date  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402
import exemplo as ex  # noqa: E402
from cobranca import toque_do_dia  # noqa: E402

FAIXAS = [(1, 15, '1 a 15 dias'), (16, 30, '16 a 30 dias'), (31, 60, '31 a 60 dias'),
          (61, 90, '61 a 90 dias'), (91, 10 ** 6, 'mais de 90 dias')]


def faixa(dias):
    for de, ate, rotulo in FAIXAS:
        if de <= dias <= ate:
            return rotulo
    return '-'


def montar(vencidas, clientes, nao_cobrar, hoje):
    por_cliente = defaultdict(list)
    for cob in vencidas:
        por_cliente[cob.get('customer')].append(cob)
    linhas = []
    for cid, cobs in por_cliente.items():
        cli = clientes.get(cid) or {}
        atrasos = [c.dias_do_vencimento(x.get('dueDate'), hoje) or 0 for x in cobs]
        linhas.append({
            'customer': cid, 'nome': cli.get('name') or '(sem nome no Asaas)', 'cpf': cli.get('cpfCnpj', ''),
            'telefone': c.ClientesAsaas.telefone(cli), 'qtd': len(cobs),
            'total': round(sum(c.num(x.get('value')) for x in cobs), 2),
            'maior_atraso': max(atrasos), 'mais_antigo': min(x.get('dueDate') or '' for x in cobs),
            'na_regua': any(toque_do_dia(a) for a in atrasos),
            'nao_cobrar': c.esta_na_lista(nao_cobrar, cid, cli.get('name'), cli.get('cpfCnpj')),
            'cobrancas': sorted(cobs, key=lambda x: x.get('dueDate') or ''),
        })
    linhas.sort(key=lambda x: (-x['total'], -x['maior_atraso']))
    return linhas


def planilha(linhas, hoje, saida=None):
    wb = c.planilha_nova()
    titulo = f"INADIMPLENCIA EM {hoje.strftime('%d/%m/%Y')} - {c.NOME_ESCRITORIO}"
    c.aba(wb, 'POR CLIENTE',
          ['Cliente', 'CPF/CNPJ', 'Telefone', 'Qtd vencidas', 'Total em aberto', 'Maior atraso (dias)',
           'Vencimento mais antigo', 'Faixa', 'Na regua automatica', 'Lista nao cobrar'],
          [[l['nome'], l['cpf'], l['telefone'], l['qtd'], l['total'], l['maior_atraso'], c.data_br(l['mais_antigo']),
            faixa(l['maior_atraso']), 'SIM' if l['na_regua'] else 'NAO - contato humano',
            'SIM' if l['nao_cobrar'] else ''] for l in linhas],
          [38, 16, 15, 12, 16, 14, 14, 16, 22, 12], colunas_moeda=(4,), titulo_topo=titulo)
    c.aba(wb, 'COBRANCAS',
          ['Cliente', 'ID Asaas', 'Descricao', 'Vencimento', 'Dias de atraso', 'Valor', 'Link da fatura'],
          [[l['nome'], x['id'], x.get('description') or '', c.data_br(x.get('dueDate')),
            c.dias_do_vencimento(x.get('dueDate'), hoje), c.num(x.get('value')), x.get('invoiceUrl') or '']
           for l in linhas for x in l['cobrancas']],
          [38, 18, 40, 12, 12, 14, 42], colunas_moeda=(5,))
    faixas = defaultdict(lambda: [0, 0.0])
    for l in linhas:
        for x in l['cobrancas']:
            f = faixas[faixa(c.dias_do_vencimento(x.get('dueDate'), hoje) or 0)]
            f[0] += 1
            f[1] += c.num(x.get('value'))
    c.aba(wb, 'FAIXAS DE ATRASO', ['Faixa', 'Cobrancas', 'Valor'],
          [[r, faixas[r][0], round(faixas[r][1], 2)] for _, _, r in FAIXAS] +
          [['TOTAL', sum(v[0] for v in faixas.values()), round(sum(v[1] for v in faixas.values()), 2)]],
          [18, 12, 16], colunas_moeda=(2,))
    arq = os.path.join(c.pasta_saida(saida, 'INADIMPLENCIA'), f"inadimplencia_{hoje.isoformat()}.xlsx")
    return c.salvar_planilha(wb, arq)


def executar(exemplo=False, saida=None, hoje=None):
    hoje = hoje or date.today()
    c.cabecalho_execucao('INADIMPLENCIA (cobrancas vencidas no Asaas)', exemplo)
    if exemplo:
        vencidas = [x for x in ex.cobrancas_abertas(hoje) if x['status'] == 'OVERDUE']
        clientes, nao_cobrar = c.ClientesAsaas(ex.CLIENTES), ex.NAO_COBRAR
    else:
        if not c.asaas_configurado():
            print('Modo seguro: sem ASAAS_API_TOKEN no config/.env. Nada consultado.')
            print('Para ver como funciona: python FINANCEIRO/main.py inadimplencia --exemplo')
            return []
        from asaas_integration import listar_cobrancas
        print('Buscando cobrancas vencidas (OVERDUE) no Asaas...')
        vencidas = [x for x in listar_cobrancas(status='OVERDUE') if not x.get('deleted')]
        clientes, nao_cobrar = c.ClientesAsaas(), c.carregar_nao_cobrar()

    linhas = montar(vencidas, clientes, nao_cobrar, hoje)
    total = sum(l['total'] for l in linhas)
    print(f"\n{'CLIENTE':38} {'QTD':>4} {'EM ABERTO':>14} {'ATRASO':>7}  OBS")
    for l in linhas:
        obs = []
        if not l['na_regua']:
            obs.append('fora da regua: contato humano')
        if l['nao_cobrar']:
            obs.append('lista nao cobrar')
        if not l['telefone']:
            obs.append('sem telefone')
        print(f"{l['nome'][:38]:38} {l['qtd']:>4} {c.moeda(l['total']):>14} {l['maior_atraso']:>6}d  {'; '.join(obs)}")
    print(f"\nTOTAL VENCIDO: {c.moeda(total)} em {sum(l['qtd'] for l in linhas)} cobranca(s) de {len(linhas)} cliente(s)")
    if linhas:
        print(f'Planilha: {planilha(linhas, hoje, saida)}')
    return linhas

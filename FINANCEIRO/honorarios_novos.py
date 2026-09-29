"""
Honorarios novos: todo caso da fase de contratacao tem cobranca criada no Asaas?

  python FINANCEIRO/main.py honorarios-novos
  python FINANCEIRO/main.py honorarios-novos --exemplo

Le os casos da CONTRATACAO (caso.json de cada pasta de cliente: chaves 'asaas' e 'cadastro')
e aponta ao Financeiro quem ainda esta sem cobranca. Com ASAAS_API_TOKEN, confere no Asaas se
as cobrancas existem e procura cobranca criada a mao pelo CPF. So leitura: nada e criado.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import date  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402
import exemplo as ex  # noqa: E402

OK = 'OK'


def valores_do_cadastro(cad):
    """Texto dos valores numericos do CADASTRO (os mesmos que a CONTRATACAO usa no Asaas) ou ''."""
    partes = []
    if cad.get('honorarios_entrada_valor') and cad.get('honorarios_entrada_vencimento'):
        partes.append(f"Entrada {c.moeda(c.num(cad['honorarios_entrada_valor']))} em {cad['honorarios_entrada_vencimento']}")
    if cad.get('honorarios_parcelas_qtd') and cad.get('honorarios_parcela_valor') \
            and cad.get('honorarios_parcelas_primeiro_vencimento'):
        partes.append(f"{cad['honorarios_parcelas_qtd']}x {c.moeda(c.num(cad['honorarios_parcela_valor']))} "
                      f"a partir de {cad['honorarios_parcelas_primeiro_vencimento']}")
    return '; '.join(partes)


def texto_combinado(cad):
    return ' | '.join(f'{k}: {cad[k]}' for k in ('honorarios_entrada', 'honorarios_pagamento', 'honorarios_exito')
                      if cad.get(k)) or '-'


def conferir_caso(base, caso, consultar_asaas):
    q = caso.get('qualificacao') or {}
    cad = caso.get('cadastro') or {}
    asaas = caso.get('asaas') or []
    valores = valores_do_cadastro(cad)
    linha = {'nome': q.get('nome') or os.path.basename(base), 'cpf': q.get('cpf') or '', 'pasta': base,
             'etapa': caso.get('etapa', ''), 'contrato': c.data_br(caso.get('data_contrato')),
             'valores': valores or '-', 'combinado': texto_combinado(cad),
             'links': ' '.join(l.get('link') or '' for l in asaas), 'no_asaas': ''}

    if asaas:
        linha['situacao'], linha['acao'] = OK, 'Cobrança criada pela automação.'
        if consultar_asaas:
            consultas = [c.obter_cobranca(l['id']) for l in asaas if l.get('id')]
            status = ['APAGADA' if p.get('deleted') else (p.get('status') or 'NAO ENCONTRADA') for p in consultas]
            linha['no_asaas'] = ', '.join(status)
            if status and all(s in ('APAGADA', 'NAO ENCONTRADA') for s in status):
                linha['situacao'] = 'CONFERIR'
                linha['acao'] = 'O caso diz que a cobrança foi criada, mas o Asaas não achou (apagada?). Recriar.'
        return linha

    if consultar_asaas and linha['cpf']:
        achadas = [p for p in c.cobrancas_do_cpf(linha['cpf'])
                   if (p.get('dateCreated') or p.get('dueDate') or '') >= (caso.get('data_contrato') or '')]
        if achadas:
            linha['no_asaas'] = f'{len(achadas)} cobranca(s) do CPF desde o contrato'
            linha['situacao'], linha['acao'] = OK, 'Cobrança criada direto no Asaas (fora da automação).'
            return linha

    if not caso.get('zapsign'):
        linha['situacao'] = 'AGUARDANDO ENVIO'
        linha['acao'] = ('A cobrança é criada junto com o envio para assinatura (CONTRATACAO enviar).'
                         + ('' if valores else ' ATENÇÃO: cadastro sem valores numéricos, o Asaas não será gerado.'))
    elif valores:
        linha['situacao'] = 'FALTA COBRANCA'
        linha['acao'] = ('Documentos já enviados e sem cobrança: criar no Asaas com os valores do cadastro '
                         '(ou rodar CONTRATACAO enviar com ASAAS_API_TOKEN configurado).')
    else:
        linha['situacao'] = 'FALTA COBRANCA'
        linha['acao'] = ('Cadastro sem valores numéricos: confirmar com o Closer (entrada, parcelas, vencimentos) '
                         'e criar a cobrança no Asaas.')
    return linha


def carregar_casos(exemplo):
    if exemplo:
        return ex.casos_contratacao()
    from CONTRATACAO import pasta_cliente
    return pasta_cliente.listar_casos()


def executar(exemplo=False, saida=None):
    c.cabecalho_execucao('HONORARIOS NOVOS (contratacao x Asaas)', exemplo)
    consultar = not exemplo and c.asaas_configurado()
    if not exemplo and not consultar:
        print('Sem ASAAS_API_TOKEN: confiro so o que esta gravado em cada caso (sem consultar o Asaas).')
    casos = [(b, cs) for b, cs in carregar_casos(exemplo) if cs.get('etapa') != 'ENCERRADO']
    if not casos:
        print('Nenhum caso na fase de contratacao (PASTA_CLIENTES_RAIZ/AGRONEGOCIO).')
        return []
    linhas = [conferir_caso(b, cs, consultar) for b, cs in casos]
    ordem = {'FALTA COBRANCA': 0, 'CONFERIR': 1, 'AGUARDANDO ENVIO': 2, OK: 3}
    linhas.sort(key=lambda l: (ordem.get(l['situacao'], 9), l['nome']))

    print(f"\n{'CLIENTE':34} {'CONTRATO':10} {'SITUACAO':17} O QUE FAZER")
    for l in linhas:
        print(f"{l['nome'][:34]:34} {l['contrato']:10} {l['situacao']:17} {l['acao']}")
    faltam = [l for l in linhas if l['situacao'] in ('FALTA COBRANCA', 'CONFERIR')]
    print(f'\n{len(faltam)} caso(s) precisam do Financeiro | {len(linhas)} caso(s) conferidos')

    wb = c.planilha_nova()
    c.aba(wb, 'HONORARIOS NOVOS',
          ['Cliente', 'CPF', 'Contrato', 'Etapa', 'Situacao', 'O que fazer', 'Valores (cadastro)',
           'Combinado (texto do contrato)', 'Status no Asaas', 'Links', 'Pasta'],
          [[l['nome'], l['cpf'], l['contrato'], l['etapa'], l['situacao'], l['acao'], l['valores'], l['combinado'],
            l['no_asaas'], l['links'], l['pasta']] for l in linhas],
          [32, 16, 11, 22, 17, 60, 40, 40, 20, 40, 50],
          titulo_topo=f"HONORARIOS NOVOS EM {date.today().strftime('%d/%m/%Y')} - {c.NOME_ESCRITORIO}")
    arq = c.salvar_planilha(wb, os.path.join(c.pasta_saida(saida, 'HONORARIOS_NOVOS'),
                                             f'honorarios_novos_{date.today().isoformat()}.xlsx'))
    print(f'Planilha: {arq}')
    return linhas

"""
Regras financeiras do Caldeira Advogados Associados.

Tudo que e politica do escritorio (regua de cobranca, comissoes, o que nao conta como
receita, o que e distribuicao de lucros) mora aqui. O codigo do FINANCEIRO/ le SO deste
arquivo: nada de regra escrita dentro do codigo.

>>> VAZIO DE PROPOSITO. Enquanto o escritorio nao definir as regras, nenhuma comissao e
>>> calculada, ninguem e excluido do faturamento e o fechamento roda de forma neutra.
>>> Quem preenche: Financeiro + titular, na reuniao de onboarding do financeiro.

Depois de alterar, conferir com:
    python FINANCEIRO/main.py fechamento 08/2026 --exemplo
"""

# ============================================================
# 1. REGUA DE COBRANCA DOS HONORARIOS (Asaas -> WhatsApp)
# ============================================================
# Dias em relacao ao vencimento: negativo = antes, 0 = no dia, positivo = atrasado.
# 'ate' e a janela de recuperacao: se a rotina nao rodou no dia exato (feriado, maquina
# desligada), o toque ainda sai ate esse dia. Cada toque sai UMA vez por cobranca, e o
# cliente recebe no maximo UMA mensagem por dia (os toques do dia sao juntados).
# Depois do ultimo toque a cobranca sai da regua automatica e vai para o relatorio de
# inadimplencia (contato humano do Financeiro).
REGUA_COBRANCA = [
    {'id': 'LEMBRETE_3D', 'dia': -3, 'ate': -1, 'tipo': 'lembrete'},
    {'id': 'VENCE_HOJE', 'dia': 0, 'ate': 0, 'tipo': 'lembrete'},
    {'id': 'VENCIDA_D1', 'dia': 1, 'ate': 4, 'tipo': 'vencida'},
    {'id': 'VENCIDA_D5', 'dia': 5, 'ate': 14, 'tipo': 'vencida'},
    {'id': 'VENCIDA_D15', 'dia': 15, 'ate': 29, 'tipo': 'vencida'},
]

# ============================================================
# 2. COMISSOES (VAZIO ate o escritorio definir)
# ============================================================
# Calculadas no fechamento APENAS para conferencia (planilha + resumo). Nada e lancado no
# ADVBOX automaticamente. Estrutura de cada comissionado:
#
#   'CHAVE_CURTA': {
#       'rotulo': 'Nome que aparece no relatorio',
#       'percentual': 0.10,          # fracao do valor RECEBIDO no Asaas (0.10 = 10%)
#       'marcadores': ['_XYZ'],      # texto na descricao da cobranca do Asaas que liga a cobranca a esta comissao
#       'clientes': [],              # OU: nomes de clientes (parte do nome, MAIUSCULO) que geram comissao
#       'exclusoes': [],             # clientes que NUNCA geram comissao para este comissionado
#   }
#
# Exemplo ILUSTRATIVO (nao ativo):
#   COMISSOES = {'PARCEIRO_1': {'rotulo': 'Parceiro de indicacao', 'percentual': 0.10,
#                               'marcadores': ['_P1'], 'clientes': [], 'exclusoes': []}}
COMISSOES = {}

# ============================================================
# 3. O QUE NAO E RECEITA DO ESCRITORIO (VAZIO)
# ============================================================
# Clientes/lancamentos que passam pelo caixa mas NAO sao receita do escritorio
# (ex.: valor de terceiro que so transita). Parte do nome, MAIUSCULO.
EXCLUIR_FATURAMENTO = []

# ============================================================
# 4. DISTRIBUICAO DE LUCROS (NAO e despesa operacional)
# ============================================================
# Palavras (MAIUSCULO) que identificam, pela CATEGORIA do ADVBOX, os lancamentos de
# distribuicao de lucros/pro-labore dos socios. Eles aparecem separados e NAO entram no
# calculo de % despesa/receita nem no lucro operacional.
# Ajustar ao plano de contas do ADVBOX do escritorio.
CATEGORIAS_DISTRIBUICAO = ['DISTRIBUI']

# Conciliacao Asaas x ADVBOX: diferenca maxima de dias entre o pagamento no Asaas e o
# vencimento/pagamento lancado no ADVBOX para considerar o mesmo lancamento.
TOLERANCIA_DIAS_CONCILIACAO = 5


# ============================================================
# FUNCOES (o codigo usa estas; nao precisa mexer)
# ============================================================

def _up(txt):
    return (txt or '').upper()


def excluir_do_faturamento(nome):
    n = _up(nome)
    return any(_up(x) in n for x in EXCLUIR_FATURAMENTO if x)


def eh_distribuicao(categoria):
    c = _up(categoria)
    return any(_up(p) in c for p in CATEGORIAS_DISTRIBUICAO if p)


def comissao_da_cobranca(descricao, nome_cliente):
    """Chaves de COMISSOES que valem para esta cobranca recebida (lista, pode ser vazia)."""
    desc, nome = _up(descricao), _up(nome_cliente)
    chaves = []
    for chave, r in COMISSOES.items():
        if any(_up(x) in nome for x in r.get('exclusoes', []) if x):
            continue
        por_marcador = any(_up(m) in desc for m in r.get('marcadores', []) if m)
        por_cliente = any(_up(c) in nome for c in r.get('clientes', []) if c)
        if por_marcador or por_cliente:
            chaves.append(chave)
    return chaves

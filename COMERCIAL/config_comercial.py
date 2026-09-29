"""
Regras do SETOR COMERCIAL (SDR -> Closer) e da captacao.

Tudo que o escritorio decide mora aqui: nota minima do lead, tabela de propostas
(valores ficam em branco ate o escritorio definir), limites dos alertas do Meta Ads
e da auditoria de atendimento, regioes prioritarias do radar.
"""

# ============================================================
# SDR - QUALIFICACAO DO LEAD
# ============================================================

# Nota minima (0 a 100) para o lead ser passado ao Closer como QUALIFICADO.
NOTA_MINIMA_QUALIFICADO = 60

# Pontos de cada criterio (divida rural com banco). A soma e 100.
PESOS_DIVIDA_RURAL = {
    'produtor_rural': 20,        # confirmou que e produtor rural (PF ou PJ do produtor)
    'credito_rural': 20,         # tem divida com banco/cooperativa ligada a atividade rural
    'banco': 10,                 # disse qual banco/cooperativa
    'valor': 10,                 # deu valor aproximado da divida
    'vencimento': 10,            # disse quando vence (ou que ja venceu)
    'perda': 15,                 # teve perda de safra / queda de receita e disse a causa
    'regiao': 5,                 # atua na regiao de atendimento
    'cobranca': 10,              # ha cobranca, execucao, negativacao ou vencimento proximo
}

# Pontos de cada criterio (previdenciario rural). A soma e 100.
PESOS_PREVIDENCIARIO = {
    'beneficio': 25,             # disse qual beneficio busca (salario-maternidade, BPC etc.)
    'trabalho_rural': 30,        # trabalha/trabalhou na roca (economia familiar)
    'situacao': 25,              # situacao informada (data do parto, idade, deficiencia, pedido negado no INSS)
    'documentos': 20,            # tem algum documento rural (bloco de notas, ITR, CAR, declaracao de sindicato)
}

# UFs de atuacao (pontua 'regiao' no SDR e define o radar padrao)
UFS_ATENDIMENTO = ['RO', 'MT']

# Tabela de propostas que o SDR sugere ao Closer. O ESCRITORIO define os valores:
# enquanto estiverem vazios, o resumo sai com [DEFINIR PELO ESCRITORIO].
PROPOSTAS = {
    'EXTRAJUDICIAL': {
        'servico': 'Notificação extrajudicial de pedido de prorrogação/alongamento aos bancos '
                   '(com levantamento das cédulas e laudos)',
        'entrada': '', 'parcelas': '', 'exito': '',
    },
    'EXTRAJUDICIAL_JUDICIAL': {
        'servico': 'Notificação extrajudicial + Ação Mandamental de Prorrogação Compulsória de Dívida Rural '
                   'com pedido de tutela de urgência, se o banco não atender',
        'entrada': '', 'parcelas': '', 'exito': '',
    },
    'EMBARGOS_EXECUCAO': {
        'servico': 'Defesa em execução já ajuizada (embargos à execução) + pedido de prorrogação',
        'entrada': '', 'parcelas': '', 'exito': '',
    },
    'PREVIDENCIARIO_RURAL': {
        'servico': 'Pedido/recurso de benefício previdenciário rural (salário-maternidade, BPC, aposentadoria rural)',
        'entrada': '', 'parcelas': '', 'exito': '',
    },
    'AVALIAR': {
        'servico': 'Caso fora do padrão: avaliar com o Gestor Jurídico antes de propor',
        'entrada': '', 'parcelas': '', 'exito': '',
    },
}

# ============================================================
# CALCULADORA DE JUROS (pagina de captacao)
# ============================================================

# Numero do WhatsApp do botao da calculadora (so digitos, com DDI 55).
# Vazio = usa a Central do escritorio (config/escritorio.py).
WHATSAPP_CALCULADORA = ''
MENSAGEM_WHATSAPP_CALCULADORA = ('Olá! Usei a calculadora de juros do crédito rural no site e '
                                 'gostaria de conversar com a equipe do escritório.')

# ============================================================
# META ADS - alertas do relatorio (nada e alterado na conta: so recomendacao)
# ============================================================
META = {
    'cpl_alvo': None,                  # custo por lead aceitavel (R$). None = usa a media da conta no periodo
    'alerta_cpl_subiu_pct': 30,        # alerta se o CPL subir mais que isso contra o periodo anterior
    'gasto_minimo_sem_lead': 50.0,     # anuncio que gastou isso (R$) sem nenhum lead entra no alerta
    'frequencia_alta': 3.0,            # frequencia acima disso = publico cansado do anuncio
    'ctr_baixo_pct': 0.8,              # CTR abaixo disso = criativo fraco
    'regioes_foco': ['Rondônia', 'Mato Grosso'],
}

# ============================================================
# AUDITORIA DE ATENDIMENTO (Atende Direito)
# ============================================================
ATENDIMENTO = {
    'sla_primeira_resposta_min': 15,   # acima disso o lead esfria (meta ideal: 5 min)
    'meta_ideal_min': 5,
    'horas_sem_resposta': 24,          # conversa sem nenhuma resposta ha mais que isso = perdida
    # palavras que indicam fechamento nas etiquetas/etapas do CRM do Atende Direito
    'palavras_fechou': ['fechou', 'fechado', 'contrato assinado', 'contratado', 'ganho', 'cliente'],
    'palavras_qualificado': ['qualificado', 'reuniao agendada', 'reunião agendada', 'agendado'],
}

# ============================================================
# RADAR DE CREDITO RURAL
# ============================================================
RADAR = {
    # pesos do indice de prioridade para trafego (somam 1)
    'peso_contratos': 0.40,            # quantidade de contratos = quantidade de produtores com credito
    'peso_valor': 0.35,                # volume financiado = tamanho das dividas (ticket)
    'peso_foco': 0.25,                 # volume em soja + bovinos (publico-alvo do escritorio)
    'produtos_foco': ['SOJA', 'BOVINOS'],
    'top_sugestao': 15,                # quantos municipios sugerir para o trafego
}

"""
Identidade e regras da FASE DE CONTRATACAO do Caldeira Advogados Associados.

Tudo que e do escritorio (nome, timbrado, prazos, checklist, pastas) mora aqui,
para que a equipe ajuste sem mexer no codigo.
"""

ESCRITORIO = {
    'nome': 'Caldeira Advogados Associados',
    'razao_social': 'CALDEIRA ADVOGADOS ASSOCIADOS',
    'cnpj': '51.038.631/0001-30',
    'endereco': 'Avenida São Paulo, 2384, Centro, Cacoal/RO, CEP 76963-782',
    'endereco_timbrado': 'Avenida São Paulo, 2384, Centro',
    'cidade': 'Cacoal',
    'uf': 'RO',
    'telefone': '(69) 99214-2954',
    'central': '(69) 99348-3443',
    'email': 'caldeiradvocacia@gmail.com',
    'site': 'caldeiraadvocacia.com.br',
    'instagram': '@caldeira.advogados',
}

# Advogado titular (assina o contrato pelo escritorio)
TITULAR = {
    'nome': 'Augusto Alves Caldeira',
    'oab': 'OAB/RO 11.101',
    'email': 'augustocaldeira.adv@gmail.com',
}

# Advogados que constam na procuracao (outorgados). Tirado das assinaturas das pecas
# enviadas em 28/09/2026; conferir com o escritorio se ha mais alguem.
OUTORGADOS = [
    {'nome': 'AUGUSTO ALVES CALDEIRA', 'oab': 'OAB/RO 11.101'},
    {'nome': 'LORENA GOIS FONTENELE', 'oab': 'OAB/RO 14.429'},
]

# Visual do timbrado (tirado das pecas do escritorio)
VISUAL = {
    'fonte': 'Times New Roman',
    'fonte_rodape': 'Calibri',
    'tamanho': 12,
    'cor_destaque': 'C45911',   # laranja dos titulos e nomes das partes
    'cor_texto': '20201F',
    'espacamento': 1.5,
    'recuo_primeira_linha_cm': 1.25,
}

# Prazos internos do fluxo (manual de funcoes). Na reuniao de 24/09/2026 foi proposto
# reduzir para 5 dias (notificacao) e 15 dias (inicial); o escritorio decide e altera aqui.
PRAZOS = {
    'onboarding_dias_apos_contrato': 2,     # Gestor Juridico marca a reuniao de onboarding
    'documentos_dias_apos_contrato': 1,     # Estagiario pede os documentos do checklist
    'notificacao_dias_apos_onboarding': 15, # Adv. Extrajudicial envia a notificacao ao banco
    'inicial_dias_apos_contrato': 60,       # protocolo da peticao inicial
}

# Checklist de documentos do fluxo do servico. 'pasta' e a subpasta onde o documento
# fica guardado; 'palavras' ajuda a reconhecer o arquivo pelo nome.
CHECKLIST_DOCUMENTOS = [
    {'id': 'pessoais', 'nome': 'CPF, RG e documentos pessoais', 'pasta': '01 DOCUMENTOS PESSOAIS',
     'palavras': ['cnh', 'rg', 'cpf', 'identidade', 'pessoal', 'certidao'], 'obrigatorio': True},
    {'id': 'endereco', 'nome': 'Comprovante de endereco', 'pasta': '02 COMPROVANTE DE ENDERECO',
     'palavras': ['endereco', 'residencia', 'conta de luz', 'energia', 'agua'], 'obrigatorio': True},
    {'id': 'contratos', 'nome': 'Copias de TODOS os contratos bancarios (cedulas, CPR, aditivos)',
     'pasta': '03 CEDULAS E CONTRATOS BANCARIOS',
     'palavras': ['cedula', 'ccr', 'cpr', 'contrato', 'aditivo', 'ccb', 'nota de credito', 'ncr'],
     'obrigatorio': True},
    {'id': 'extratos', 'nome': 'Extratos bancarios', 'pasta': '04 EXTRATOS BANCARIOS',
     'palavras': ['extrato'], 'obrigatorio': True},
    {'id': 'pagamentos', 'nome': 'Comprovantes de pagamento de parcelas', 'pasta': '05 COMPROVANTES DE PAGAMENTO',
     'palavras': ['comprovante', 'pagamento', 'recibo', 'boleto'], 'obrigatorio': True},
    {'id': 'frustracao', 'nome': 'Registro de frustracao de safra (se houver)', 'pasta': '06 FRUSTRACAO DE SAFRA',
     'palavras': ['frustracao', 'safra', 'laudo', 'emater', 'decreto', 'emergencia', 'proagro', 'sinistro'],
     'obrigatorio': False},
    {'id': 'matricula', 'nome': 'Matricula do imovel rural', 'pasta': '07 MATRICULA DO IMOVEL',
     'palavras': ['matricula', 'car', 'ccir', 'itr', 'imovel'], 'obrigatorio': True},
    {'id': 'fiscal', 'nome': 'Documentacao fiscal (notas fiscais)', 'pasta': '08 DOCUMENTACAO FISCAL',
     'palavras': ['nota fiscal', 'nf', 'nfe', 'fiscal', 'talao', 'produtor'], 'obrigatorio': True},
    {'id': 'procuracao', 'nome': 'Procuracao assinada', 'pasta': '00 CONTRATACAO',
     'palavras': ['procuracao'], 'obrigatorio': True},
    {'id': 'pecuaria', 'nome': 'GTA e extrato do IDARON (se for pecuarista)', 'pasta': '09 PECUARIA GTA IDARON',
     'palavras': ['gta', 'idaron', 'rebanho', 'vacinacao'], 'obrigatorio': False},
    {'id': 'ir', 'nome': 'Declaracao de Imposto de Renda (ultimos 3 anos)', 'pasta': '10 IMPOSTO DE RENDA',
     'palavras': ['imposto de renda', 'irpf', 'declaracao de ajuste', 'recibo de entrega'], 'obrigatorio': False},
    {'id': 'govbr', 'nome': 'Senha GOV.BR do cliente', 'pasta': None,
     'palavras': ['gov.br', 'govbr'], 'obrigatorio': True, 'sensivel': True},
]

# Estrutura da pasta do cliente. Ajustar para a nomenclatura padrao do escritorio.
PASTA_AREA = 'AGRONEGOCIO'
SUBPASTAS_CLIENTE = [
    '00 CONTRATACAO',
    'DOCUMENTOS DO CLIENTE',
    '10 EXTRAJUDICIAL',
    '20 JUDICIAL',
]

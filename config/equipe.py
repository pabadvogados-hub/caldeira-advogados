"""
Cargos do manual de funcoes do escritorio -> usuarios do ADVBOX.

Preencher com o nome e o ID de cada pessoa no ADVBOX (rodar
`python INTEGRACOES/advbox_integration.py` para listar os usuarios e IDs).
Enquanto um ID estiver vazio, a tarefa daquele cargo nao e criada.
"""

CARGOS = {
    'SDR': {'nome': '', 'advbox_id': ''},
    'CLOSER': {'nome': '', 'advbox_id': ''},
    'GESTOR_JURIDICO': {'nome': '', 'advbox_id': ''},
    'COORDENADOR_JURIDICO': {'nome': 'Dr. Willian', 'advbox_id': ''},
    'ADV_EXTRAJUDICIAL': {'nome': '', 'advbox_id': ''},
    'ADV_JUDICIAL': {'nome': '', 'advbox_id': ''},
    'ESTAGIARIO': {'nome': '', 'advbox_id': ''},
    'FINANCEIRO': {'nome': '', 'advbox_id': ''},
}

# Quem aparece como remetente das tarefas criadas pela automacao (campo "from" do ADVBOX)
REMETENTE_TAREFAS = 'GESTOR_JURIDICO'

# Tarefas que a fase de contratacao abre no ADVBOX (so com --criar-tarefas).
# 'tipo' e o nome (ou parte) do tipo de tarefa cadastrado no ADVBOX do escritorio.
TAREFAS_CONTRATACAO = [
    {'marco': 'documentos', 'cargo': 'ESTAGIARIO', 'tipo': 'SOLICITAR DOCUMENTOS',
     'texto': 'Solicitar ao cliente os documentos do checklist e organizar na pasta. Faltando: {faltando}. Pasta: {pasta}'},
    {'marco': 'onboarding', 'cargo': 'GESTOR_JURIDICO', 'tipo': 'REUNIAO',
     'texto': 'Reuniao de onboarding com o cliente. Relatorio de triagem na pasta: {pasta}'},
    {'marco': 'notificacao', 'cargo': 'ADV_EXTRAJUDICIAL', 'tipo': 'NOTIFICA',
     'texto': 'Enviar notificacao extrajudicial aos bancos ({bancos}). Prazo interno do escritorio.'},
    {'marco': 'inicial', 'cargo': 'COORDENADOR_JURIDICO', 'tipo': 'ACOMPANHAMENTO',
     'texto': 'Prazo maximo para protocolo da inicial (60 dias do contrato). Monitorar o caso.'},
]

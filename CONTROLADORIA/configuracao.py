"""
Regras da Controladoria (fases 5 e 6) do Caldeira Advogados Associados.

Tudo que o escritorio pode querer ajustar sem mexer no codigo mora aqui:
antecedencia do prazo interno, pasta de arquivo, periodicidade do relatorio ao
cliente e o que cada tipo de publicacao pede (prazo padrao do CPC, cargo
responsavel, providencia e peca sugerida).

Variaveis do config/.env que mudam o comportamento:
    OABS_MONITORADAS=11101/RO,14429/RO,182814/MG   OABs consultadas no DJEN (182814/MG = inscricao
                                          do titular usada no PJe do TJRO/TRF1)
    PRAZO_INTERNO_DIAS_ANTES=3            prazo interno = D-3 (dias uteis) do fatal
    PASTA_ARQUIVO_CLIENTES=               onde vao as pastas encerradas (fase 6)
    FERIADOS_EXTRAS=                      feriados locais DD/MM ou DD/MM/AAAA, separados por virgula
    RELATORIO_CLIENTE_DIAS=30             periodicidade do relatorio de andamento ao produtor
"""
import os

# Prazo interno: quantos DIAS UTEIS antes do prazo fatal a tarefa vence no ADVBOX.
DIAS_ANTES_FATAL = int(os.getenv('PRAZO_INTERNO_DIAS_ANTES', '3') or 3)

# Processo sem movimentacao ha mais que isso = "parado" (possivel falta de custas/juntada).
DIAS_PARADO = 30

# Relatorio periodico ao produtor (15 ou 30 dias).
RELATORIO_CLIENTE_DIAS = int(os.getenv('RELATORIO_CLIENTE_DIAS', '30') or 30)

# Fases do ADVBOX que contam como encerradas (nome ou parte do nome da fase).
FASES_ENCERRADAS = ('ARQUIV', 'ENCERR', 'RENUNCI', 'BAIXAD', 'FINALIZ', 'EXTINT')

# Classes processuais em que o produtor normalmente esta no POLO PASSIVO (o banco cobra).
# Usado so para dizer se "procedente" e bom ou ruim para o cliente (sempre "conferir").
CLASSES_POLO_PASSIVO = ('EXECUÇÃO', 'EXECUCAO', 'MONITÓRIA', 'MONITORIA', 'BUSCA E APREENSÃO',
                        'BUSCA E APREENSAO', 'COBRANÇA', 'COBRANCA', 'CUMPRIMENTO DE SENTENÇA',
                        'CUMPRIMENTO DE SENTENCA', 'REINTEGRAÇÃO', 'REINTEGRACAO')

# ------------------------------------------------------------------
# O QUE CADA TIPO DE PUBLICACAO PEDE
# ------------------------------------------------------------------
# prazo_dias: prazo padrao do CPC em dias uteis quando o texto nao traz "prazo de N dias"
#             (None = sem prazo fatal; so acompanhamento/ciencia).
# cargo:      chave de config/equipe.py (CARGOS) que recebe a tarefa.
# tipo_tarefa: nomes (ou parte) do tipo de tarefa no ADVBOX, em ordem de preferencia.
# peca / comando: sugestao para o advogado. A IA nao protocola.
#   ATENCAO: os comandos do modulo JUDICIAL precisam existir com esses nomes; ajustar aqui.
# aviso_cliente: gera mensagem ao produtor no comando avisos-cliente.
# gravidade: ALTA / MEDIA / BAIXA na planilha e no relatorio. Qualquer item vira ALTA quando o
#            prazo fatal esta a 5 dias uteis ou menos (audiencia: 10 dias corridos).
ACOES = {
    'LIMINAR_DEFERIDA': {
        'rotulo': 'Liminar / tutela deferida',
        'prazo_dias': None, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['ACOMPANHAMENTO', 'PRAZO'],
        'providencia': 'Avisar o cliente e acompanhar o cumprimento pelo banco (baixa de negativação, '
                       'suspensão de cobrança/débito automático). Se o banco descumprir: petição de '
                       'descumprimento com pedido de multa.',
        'peca': 'Petição de ciência / descumprimento (se houver)', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'MEDIA', 'acompanhar_dias': 10,
    },
    'LIMINAR_INDEFERIDA': {
        'rotulo': 'Liminar / tutela indeferida',
        'prazo_dias': 15, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['RECURSO', 'AGRAVO', 'PRAZO'],
        'providencia': 'Avaliar agravo de instrumento (art. 1.015, I, CPC) com o Coordenador Jurídico. '
                       'Conferir se cabe pedido de reconsideração com documento novo.',
        'peca': 'Agravo de Instrumento', 'comando': 'python JUDICIAL/main.py agravo "{pasta}"',
        'aviso_cliente': False, 'gravidade': 'ALTA',
    },
    'SENTENCA_FAVORAVEL': {
        'rotulo': 'Sentença favorável ao cliente',
        'prazo_dias': 5, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['PRAZO', 'ACOMPANHAMENTO'],
        'providencia': 'Avisar o cliente. Conferir se cabem embargos de declaração (5 dias úteis) e '
                       'aguardar recurso do banco (contrarrazões) ou cumprimento.',
        'peca': 'Embargos de Declaração (só se houver omissão/contradição)', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'MEDIA',
    },
    'SENTENCA_DESFAVORAVEL': {
        'rotulo': 'Sentença desfavorável ao cliente',
        'prazo_dias': 15, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['RECURSO', 'APELA', 'PRAZO'],
        'providencia': 'Avaliar apelação (15 dias úteis) ou acordo com o banco. Decisão do Coordenador '
                       'Jurídico com o cliente.',
        'peca': 'Apelação', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'ALTA',
    },
    'SENTENCA': {
        'rotulo': 'Sentença (resultado a conferir)',
        'prazo_dias': 5, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['PRAZO', 'RECURSO'],
        'providencia': 'Ler a sentença e confirmar se é favorável. Prazo de embargos de declaração (5) '
                       'e de apelação (15) correm juntos.',
        'peca': 'Embargos de Declaração ou Apelação (conforme resultado)', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'ALTA',
    },
    'REPLICA': {
        'rotulo': 'Intimação para réplica (contestação do banco)',
        'prazo_dias': 15, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['REPLICA', 'RÉPLICA', 'PRAZO'],
        'providencia': 'Elaborar réplica/impugnação à contestação (arts. 350 e 351 CPC).',
        'peca': 'Réplica / Impugnação à Contestação', 'comando': 'python JUDICIAL/main.py replica "{pasta}"',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
    'MANIFESTACAO': {
        'rotulo': 'Intimação para manifestação',
        'prazo_dias': 5, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['PRAZO', 'MANIFESTA'],
        'providencia': 'Manifestar-se no prazo (sem prazo no texto: 5 dias úteis, art. 218, §3º, CPC). '
                       'Conferir o que o juízo pediu.',
        'peca': 'Petição de manifestação', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
    'CUSTAS_EMENDA': {
        'rotulo': 'Custas / emenda / juntada de documento',
        'prazo_dias': 15, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['PRAZO', 'CUSTAS', 'JUNTADA'],
        'providencia': 'Recolher custas ou emendar/juntar o que o juízo pediu (emenda: 15 dias úteis, '
                       'art. 321 CPC). Processo trava sem isso: prioridade do Coordenador.',
        'peca': 'Petição de emenda / juntada / comprovante de custas', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'ALTA',
    },
    'AUDIENCIA': {
        'rotulo': 'Audiência designada',
        'prazo_dias': None, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['AUDIENCIA', 'AUDIÊNCIA', 'PRAZO'],
        'providencia': 'Avisar o cliente (dia, hora, local/link), preparar a audiência e pôr na agenda.',
        'peca': 'Preparação de audiência', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'MEDIA',
    },
    'PERICIA': {
        'rotulo': 'Perícia',
        'prazo_dias': 15, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['PERICIA', 'PERÍCIA', 'PRAZO'],
        'providencia': 'Avisar o cliente. Quesitos e assistente técnico em 15 dias úteis (art. 465, §1º, '
                       'CPC); conferir honorários periciais e data da vistoria.',
        'peca': 'Quesitos / indicação de assistente técnico', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'MEDIA',
    },
    'CONTESTACAO_JUNTADA': {
        'rotulo': 'Contestação juntada',
        'prazo_dias': 15, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['REPLICA', 'RÉPLICA', 'PRAZO'],
        'providencia': 'Preparar a réplica (o prazo corre da intimação; conferir se já houve).',
        'peca': 'Réplica / Impugnação à Contestação', 'comando': 'python JUDICIAL/main.py replica "{pasta}"',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
    'EXECUCAO_PENHORA': {
        'rotulo': 'Execução / penhora / bloqueio',
        'prazo_dias': 15, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['PRAZO', 'EMBARGOS'],
        'providencia': 'URGENTE: embargos à execução (15 dias úteis, art. 915 CPC) com pedido de efeito '
                       'suspensivo e prejudicialidade externa com a ação mandamental; conferir bloqueio '
                       'SISBAJUD/penhora de bens essenciais.',
        'peca': 'Embargos à Execução / impugnação à penhora', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'ALTA',
    },
    'RECURSO': {
        'rotulo': 'Recurso (do banco ou decisão em recurso)',
        'prazo_dias': 15, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['RECURSO', 'CONTRARRAZ', 'PRAZO'],
        'providencia': 'Se o banco recorreu: contrarrazões (15 dias úteis; embargos de declaração: 5). '
                       'Se é acórdão/decisão do tribunal: ler e avaliar recurso.',
        'peca': 'Contrarrazões', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
    'EMBARGOS_DECLARACAO': {
        'rotulo': 'Embargos de declaração julgados',
        'prazo_dias': 15, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['RECURSO', 'PRAZO'],
        'providencia': 'O prazo do recurso contra a decisão embargada volta a correr por inteiro '
                       '(art. 1.026 CPC). Decidir se recorre (agravo/apelação) ou se aguarda.',
        'peca': 'Recurso cabível contra a decisão embargada', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
    'TRANSITO_JULGADO': {
        'rotulo': 'Trânsito em julgado',
        'prazo_dias': None, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['ACOMPANHAMENTO', 'PRAZO'],
        'providencia': 'Conferir cumprimento da decisão pelo banco (novo cronograma, baixa de restrições). '
                       'Cumprido: fase 6 (python CONTROLADORIA/main.py finalizar "PASTA").',
        'peca': 'Cumprimento de sentença (se o banco não cumprir)', 'comando': '',
        'aviso_cliente': True, 'gravidade': 'MEDIA',
    },
    'DESPACHO': {
        'rotulo': 'Despacho de mero expediente',
        'prazo_dias': None, 'cargo': 'ADV_JUDICIAL', 'tipo_tarefa': ['ACOMPANHAMENTO'],
        'providencia': 'Ciência. Conferir se o despacho não pede providência do escritório.',
        'peca': '', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'BAIXA',
    },
    'REVISAO_MANUAL': {
        'rotulo': 'Não classificado (revisão manual)',
        'prazo_dias': None, 'cargo': 'COORDENADOR_JURIDICO', 'tipo_tarefa': ['ACOMPANHAMENTO', 'PRAZO'],
        'providencia': 'REVISÃO MANUAL: ler a publicação inteira e definir a providência e o prazo.',
        'peca': '', 'comando': '',
        'aviso_cliente': False, 'gravidade': 'MEDIA',
    },
}

# Marcadores que a automacao grava no texto da tarefa do ADVBOX (evita duplicar).
TAG_TAREFA = '[CONTROLADORIA]'

# Cores da planilha de clientes (cabecalho no laranja do timbrado).
try:
    from config.escritorio import VISUAL as _VISUAL
    _COR = _VISUAL.get('cor_destaque', 'C45911')
except Exception:
    _COR = 'C45911'
VISUAL_PLANILHA = {'cabecalho': _COR, 'ALTA': 'F8CBAD', 'MEDIA': 'FFE699', 'BAIXA': 'E2EFDA'}


def pasta_arquivo():
    """Pasta para onde vao as pastas de clientes encerradas (fase 6)."""
    destino = os.getenv('PASTA_ARQUIVO_CLIENTES')
    if destino:
        return destino
    from pasta_cliente import raiz_clientes  # CONTRATACAO (so leitura da configuracao)
    return os.path.join(raiz_clientes(), 'ARQUIVO')

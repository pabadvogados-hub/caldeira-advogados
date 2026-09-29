"""
Dados FICTICIOS para o modo --exemplo (Controladoria e Gestao).

Nenhum nome, numero de processo ou valor aqui e real. As datas sao relativas a hoje
para o exemplo parecer sempre atual. Os formatos imitam o que o ADVBOX e o DJEN
devolvem de verdade, para exercitar o mesmo codigo do modo real.
"""
from datetime import date, datetime, timedelta

HOJE = date.today()


def _d(dias):
    return (HOJE + timedelta(days=dias)).isoformat()


def _br(dias):
    return (HOJE + timedelta(days=dias)).strftime('%d/%m/%Y')


def _br_util(dias):
    """Como _br, mas empurra sabado/domingo para segunda (audiencia/pericia ficticia)."""
    from prazos import dia_util
    d = HOJE + timedelta(days=dias)
    while not dia_util(d, contar_recesso=True):
        d += timedelta(days=1)
    return d.strftime('%d/%m/%Y')


# ------------------------------------------------------------------
# EQUIPE (substitui config/equipe.py so no exemplo)
# ------------------------------------------------------------------
CARGOS_EXEMPLO = {
    'GESTOR_JURIDICO': {'nome': 'Gestora Exemplo', 'advbox_id': '9005'},
    'COORDENADOR_JURIDICO': {'nome': 'Coordenador Exemplo', 'advbox_id': '9001'},
    'ADV_JUDICIAL': {'nome': 'Advogada Judicial Exemplo', 'advbox_id': '9002'},
    'ADV_EXTRAJUDICIAL': {'nome': 'Advogado Extrajudicial Exemplo', 'advbox_id': '9003'},
    'ESTAGIARIO': {'nome': 'Estagiario Exemplo', 'advbox_id': '9004'},
}
USUARIOS = {k: (v['advbox_id'], v['nome']) for k, v in CARGOS_EXEMPLO.items()}

# ------------------------------------------------------------------
# PROCESSOS (formato /lawsuits)
# ------------------------------------------------------------------
_CLIENTES = [
    (501, '7999001-11.2026.8.22.0007', 'JOSÉ EXEMPLO DA SILVA', 'BANCO FICTÍCIO S.A.', 'INICIAL - AGUARDANDO LIMINAR', 'ADV_JUDICIAL'),
    (502, '7999002-22.2026.8.22.0007', 'MARIA TESTE OLIVEIRA', 'COOPERATIVA DE CRÉDITO EXEMPLO', 'CONTESTAÇÃO / RÉPLICA', 'ADV_JUDICIAL'),
    (503, '7999003-33.2026.8.22.0009', 'PEDRO MODELO SOUZA', 'BANCO FICTÍCIO S.A.', 'INSTRUÇÃO', 'ADV_JUDICIAL'),
    (504, '7999004-44.2025.8.22.0007', 'ANA FICTÍCIA LIMA', 'COOPERATIVA DE CRÉDITO EXEMPLO', 'SENTENÇA', 'COORDENADOR_JURIDICO'),
    (505, '7999005-55.2025.8.22.0007', 'CARLOS DEMONSTRAÇÃO ROCHA', 'BANCO FICTÍCIO S.A.', 'EXECUÇÃO (CLIENTE EXECUTADO)', 'COORDENADOR_JURIDICO'),
    (506, '7999006-66.2026.8.22.0005', 'JOÃO SIMULADO PEREIRA', 'BANCO FICTÍCIO S.A.', 'INICIAL - CUSTAS', 'ADV_JUDICIAL'),
    (507, '7999007-77.2025.8.22.0007', 'LUCIA AMOSTRA COSTA', 'COOPERATIVA DE CRÉDITO EXEMPLO', 'RECURSO', 'COORDENADOR_JURIDICO'),
    (508, '', 'ROBERTO PILOTO ALVES', 'BANCO FICTÍCIO S.A.', 'EXTRAJUDICIAL', 'ADV_EXTRAJUDICIAL'),
]


def processos():
    saida = []
    for i, (pid, numero, cliente, banco, fase, cargo) in enumerate(_CLIENTES):
        saida.append({
            'id': pid, 'process_number': numero, 'protocol_number': '',
            'stage': fase, 'type': 'AGRO - PRORROGAÇÃO DE DÍVIDA RURAL',
            'responsible': CARGOS_EXEMPLO[cargo]['nome'], 'responsible_id': CARGOS_EXEMPLO[cargo]['advbox_id'],
            'customers': [{'customer_id': 3000 + i, 'name': cliente, 'cellphone': f'(69) 90000-000{i}'}],
            'parte_contraria': banco,
            'created_at': _d(-200 + 20 * i) + ' 09:00:00',
            'folder': cliente[:30],
        })
    return saida


# ------------------------------------------------------------------
# MOVIMENTACOES (formato /last_movements)
# ------------------------------------------------------------------
def movimentacoes():
    return [
        {'lawsuit_id': 501, 'date': _d(-2), 'title': 'Decisão', 'description': 'Deferida a tutela de urgência'},
        {'lawsuit_id': 502, 'date': _d(-3), 'title': 'Juntada', 'description': 'Juntada de contestação'},
        {'lawsuit_id': 502, 'date': _d(-1), 'title': 'Intimação', 'description': 'Intimação para réplica'},
        {'lawsuit_id': 503, 'date': _d(-5), 'title': 'Despacho', 'description': 'Designada perícia agronômica'},
        {'lawsuit_id': 504, 'date': _d(-1), 'title': 'Sentença', 'description': 'Julgado procedente o pedido'},
        {'lawsuit_id': 505, 'date': _d(-4), 'title': 'Decisão', 'description': 'Deferido bloqueio via SISBAJUD'},
        {'lawsuit_id': 507, 'date': _d(-45), 'title': 'Remessa', 'description': 'Remetidos os autos ao Tribunal'},
        # 506 sem movimentacao ha mais de 60 dias (inicial parada por custas)
    ]


# ------------------------------------------------------------------
# TAREFAS (formato /posts)
# ------------------------------------------------------------------
# (id, tipo, cargo, criada(dias), prazo(dias), concluida(dias ou None), processo, urgente)
_TAREFAS = [
    (1, 'ELABORAR PEÇA', 'ADV_JUDICIAL', -60, -50, -52, 501, False),
    (2, 'PROTOCOLAR', 'ADV_JUDICIAL', -52, -49, -40, 501, False),
    (3, 'PRAZO', 'ADV_JUDICIAL', -20, -5, -6, 502, True),
    (4, 'ELABORAR PEÇA', 'ADV_JUDICIAL', -15, -2, None, 503, False),
    (5, 'PROTOCOLAR', 'ADV_JUDICIAL', -3, 2, None, 502, True),
    (6, 'AUDIÊNCIA', 'ADV_JUDICIAL', -10, 3, None, 503, False),
    (7, 'PRAZO', 'COORDENADOR_JURIDICO', -8, 1, None, 505, True),
    (8, 'ELABORAR PEÇA', 'COORDENADOR_JURIDICO', -40, -30, -18, 504, False),
    (9, 'PROTOCOLAR', 'COORDENADOR_JURIDICO', -18, -15, None, 504, False),
    (10, 'ACOMPANHAMENTO', 'COORDENADOR_JURIDICO', -70, -60, None, 507, False),
    (11, 'NOTIFICAÇÃO', 'ADV_EXTRAJUDICIAL', -25, -10, -12, 508, False),
    (12, 'NOTIFICAÇÃO', 'ADV_EXTRAJUDICIAL', -9, 4, None, 508, False),
    (13, 'ELABORAR PEÇA', 'ADV_EXTRAJUDICIAL', -30, -20, -8, 508, False),
    (14, 'SOLICITAR DOCUMENTOS', 'ESTAGIARIO', -12, -11, -11, 506, False),
    (15, 'SOLICITAR DOCUMENTOS', 'ESTAGIARIO', -6, -5, None, 508, False),
    (16, 'SOLICITAR DOCUMENTOS', 'ESTAGIARIO', -2, 1, -1, 502, False),
    (17, 'REUNIÃO', 'GESTOR_JURIDICO', -4, -2, -2, 501, False),
    (18, 'REUNIÃO', 'GESTOR_JURIDICO', -1, 2, None, 506, False),
    (19, 'PRAZO', 'ADV_JUDICIAL', -30, -12, -13, 507, False),
    (20, 'ACOMPANHAMENTO', 'ADV_JUDICIAL', -85, -75, None, 506, False),
    (21, 'ELABORAR PEÇA', 'ADV_JUDICIAL', -35, -25, -24, 506, False),
    (22, 'PRAZO', 'COORDENADOR_JURIDICO', -3, 3, -1, 507, True),
    (23, 'CUSTAS', 'ADV_JUDICIAL', -65, -55, None, 506, True),
    (24, 'PRAZO', 'ADV_JUDICIAL', -1, 4, None, 501, False),
]


def tarefas():
    procs = {p['id']: p for p in processos()}
    saida = []
    for tid, tipo, cargo, criada, prazo, concluida, proc, urgente in _TAREFAS:
        uid, nome = USUARIOS[cargo]
        p = procs[proc]
        saida.append({
            'id': 70000 + tid, 'task': tipo, 'created_at': _d(criada) + ' 08:30:00',
            'date': _d(criada), 'date_deadline': _d(prazo), 'lawsuits_id': proc,
            'comments': f'Tarefa fictícia {tid} ({tipo.lower()})',
            'lawsuit': {'id': proc, 'process_number': p['process_number'], 'customers': p['customers']},
            'users': [{'id': int(uid), 'name': nome, 'urgent': urgente,
                       'completed': (_d(concluida) + ' 17:00:00') if concluida is not None else None}],
        })
    return saida


# ------------------------------------------------------------------
# CASOS DA PASTA DO CLIENTE (caso.json)
# ------------------------------------------------------------------
def _prazos(contrato_dias):
    inicio = HOJE + timedelta(days=contrato_dias)
    onb = inicio + timedelta(days=2)
    f = lambda d: d.strftime('%d/%m/%Y')  # noqa: E731
    return [
        {'marco': 'Pedir documentos do checklist ao cliente', 'id': 'documentos',
         'data': f(inicio + timedelta(days=1)), 'responsavel': 'Estagiário'},
        {'marco': 'Reunião de onboarding com o cliente', 'id': 'onboarding', 'data': f(onb),
         'responsavel': 'Gestor Jurídico'},
        {'marco': 'Notificação extrajudicial enviada aos bancos', 'id': 'notificacao',
         'data': f(onb + timedelta(days=15)), 'responsavel': 'Adv. Extrajudicial'},
        {'marco': 'Protocolo da petição inicial (prazo máximo)', 'id': 'inicial',
         'data': f(inicio + timedelta(days=60)), 'responsavel': 'Adv. Judicial'},
    ]


def _docs(faltando):
    nomes = {'pessoais': 'CPF, RG e documentos pessoais', 'contratos': 'Copias de TODOS os contratos bancarios',
             'extratos': 'Extratos bancarios', 'matricula': 'Matricula do imovel rural',
             'fiscal': 'Documentacao fiscal (notas fiscais)'}
    return [{'id': k, 'nome': v, 'obrigatorio': True,
             'situacao': 'NAO TEM' if k in faltando else 'NA PASTA'} for k, v in nomes.items()]


def casos():
    def caso(nome, contrato, etapa, faltando=(), notif=None, peca_inicial=None, pid=None, regua=False, tel='(69) 90000-0000'):
        c = {
            'id': f'{nome}-EXEMPLO', 'etapa': etapa,
            'data_contrato': (HOJE + timedelta(days=contrato)).isoformat(),
            'data_contrato_br': _br(contrato),
            'qualificacao': {'nome': nome, 'telefone': tel},
            'triagem': {'operacoes': [{'banco': 'BANCO FICTÍCIO S.A.'}]},
            'prazos': _prazos(contrato),
            'documentos_status': _docs(faltando),
        }
        if regua:
            c['alerta_gestor_em'] = _d(-1)
        if notif is not None:
            c['extrajudicial'] = {'notificacoes': [{'banco': 'BANCO FICTÍCIO S.A.', 'tipo': 'alongamento',
                                                    'enviada_em': _d(notif), 'resposta': None}]}
        if peca_inicial is not None:
            c['judicial'] = [{'tipo': 'inicial', 'banco': 'BANCO FICTÍCIO S.A.',
                              'gerada_em': _d(peca_inicial - 2) + 'T10:00:00',
                              'protocolada_em': _d(peca_inicial)}]
        if pid:
            c['advbox'] = {'cliente_id': 3000, 'processo_id': pid}
        return (f'EXEMPLO/AGRONEGOCIO/{nome}', c)

    return [
        caso('ROBERTO PILOTO ALVES', -20, 'EXTRAJUDICIAL - NOTIFICAÇÃO', notif=None, pid=508),
        caso('FERNANDA ENSAIO MOURA', -5, 'COBRANCA DE DOCUMENTOS', faltando=('contratos', 'matricula', 'fiscal'), regua=True),
        caso('PAULO PROTÓTIPO NUNES', -52, 'EXTRAJUDICIAL - AGUARDANDO RESPOSTA', notif=-30),
        caso('JOSÉ EXEMPLO DA SILVA', -75, 'JUDICIAL - INICIAL PROTOCOLADA', notif=-60, peca_inicial=-30, pid=501),
        caso('JOÃO SIMULADO PEREIRA', -66, 'JUDICIAL - PRONTO PARA A INICIAL', faltando=('extratos',), notif=-40, pid=506),
    ]


# ------------------------------------------------------------------
# DJEN (formato do item bruto da API Comunica)
# ------------------------------------------------------------------
_ADV = 'Advogados do(a) {papel}: AUGUSTO ALVES CALDEIRA - MG182814, LORENA GOIS FONTENELE - RO14429'


def _djen(i, dias, numero, classe, tipo_doc, papel, corpo, orgao='Cacoal - 3ª Vara Cível'):
    return {
        'id': 900000 + i, 'data_disponibilizacao': _d(dias), 'siglaTribunal': 'TJRO',
        'tipoComunicacao': 'Intimação', 'tipoDocumento': tipo_doc, 'nomeClasse': classe,
        'nomeOrgao': orgao, 'numeroprocessocommascara': numero,
        'numero_processo': ''.join(c for c in numero if c.isdigit()),
        'link': f'https://exemplo.invalido/djen/{900000 + i}',
        'destinatarios': [{'nome': 'PARTE FICTÍCIA', 'polo': 'A'}],
        'destinatarioadvogados': [{'advogado': {'nome': 'AUGUSTO ALVES CALDEIRA', 'numero_oab': '182814', 'uf_oab': 'MG'}}],
        'texto': f'TRIBUNAL DE JUSTIÇA DO ESTADO DE RONDÔNIA {orgao} Processo: {numero} Classe: {classe} '
                 + _ADV.format(papel=papel) + ' ' + corpo,
    }


def djen():
    pc = 'PROCEDIMENTO COMUM CÍVEL'
    return [
        _djen(1, -1, '7999001-11.2026.8.22.0007', pc, 'Decisão', 'AUTOR',
              'DECISÃO Presentes a probabilidade do direito e o perigo de dano. Diante do exposto, DEFIRO a tutela '
              'provisória de urgência para suspender a exigibilidade das cédulas rurais e determinar que o réu se '
              'abstenha de negativar o autor e seus avalistas, sob pena de multa diária de R$ 1.000,00. Cite-se.'),
        _djen(2, -1, '7999002-22.2026.8.22.0007', pc, 'Intimação', 'AUTOR',
              'INTIMAÇÃO AUTOR - RÉPLICA Fica a parte AUTORA intimada, na pessoa do seu advogado, para apresentar '
              'réplica no prazo de 15 (quinze) dias.'),
        _djen(3, -2, '7999003-33.2026.8.22.0009', pc, 'Decisão', 'AUTOR',
              'DECISÃO Defiro a produção de prova pericial agronômica. Nomeio perito o engenheiro agrônomo indicado '
              'pela CPE. A perícia será realizada no dia ' + _br_util(20) + ', às 8h00, na propriedade rural. Fica a parte '
              'AUTORA intimada para, no prazo de 15 (quinze) dias, apresentar quesitos e indicar assistente técnico.',
              orgao='Pimenta Bueno - 2ª Vara Cível'),
        _djen(4, 0, '7999004-44.2025.8.22.0007', pc, 'Sentença', 'AUTOR',
              'SENTENÇA Ante o exposto, JULGO PROCEDENTES os pedidos para reconhecer o direito do autor ao alongamento '
              'da dívida rural, com carência de 3 (três) anos e pagamento em 10 (dez) parcelas anuais, mantidos os '
              'encargos pactuados. Condeno o réu nas custas e honorários de 10%. Intimem-se.'),
        _djen(5, -3, '7999005-55.2025.8.22.0007', 'EXECUÇÃO DE TÍTULO EXTRAJUDICIAL', 'Decisão', 'EXECUTADO',
              'DECISÃO Defiro o pedido do exequente e determino o bloqueio de valores via SISBAJUD em nome do executado, '
              'até o limite do débito. Efetivado o bloqueio, intime-se o executado.'),
        _djen(6, -1, '7999006-66.2026.8.22.0005', pc, 'Decisão', 'AUTOR',
              'DECISÃO Indefiro o pedido de gratuidade. Intime-se a parte autora para, no prazo de 15 (quinze) dias, '
              'comprovar o recolhimento das custas iniciais, sob pena de cancelamento da distribuição.',
              orgao='Ji-Paraná - 4ª Vara Cível'),
        _djen(7, -2, '7999007-77.2025.8.22.0007', pc, 'Decisão', 'AUTOR',
              'DECISÃO Designo audiência de conciliação para o dia ' + _br_util(12) + ', às 9h30, por videoconferência. '
              'Intimem-se as partes.'),
        _djen(8, -1, '7999008-88.2026.8.22.0007', pc, 'Decisão', 'AUTOR',
              'DECISÃO Não estão presentes os requisitos. Assim, indefiro a tutela de urgência requerida. Cite-se.'),
        _djen(9, 0, '7999009-99.2026.8.22.0007', pc, 'Despacho', 'AUTOR',
              'DESPACHO Aguarde-se o decurso do prazo. Após, conclusos.'),
        _djen(10, 0, '7999010-00.2026.8.22.0007', pc, 'Certidão', 'AUTOR',
              'CERTIDÃO Certifico que os autos foram redistribuídos por prevenção ao juízo da 1ª Vara Cível.'),
    ]


def agora():
    return datetime.now()

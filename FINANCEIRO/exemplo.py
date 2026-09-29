"""
Dados FICTICIOS para o modo --exemplo (nenhuma API e consultada, nada e enviado).
Todas as datas sao calculadas a partir de hoje, para a regua sempre ter o que mostrar.
Nomes, CPFs, telefones e links sao inventados e marcados como EXEMPLO.
"""
from datetime import date, timedelta

CLIENTES = {
    'cus_ex01': {'id': 'cus_ex01', 'name': 'ANTONIO EXEMPLO PEREIRA', 'cpfCnpj': '00000000001', 'mobilePhone': '69900000001'},
    'cus_ex02': {'id': 'cus_ex02', 'name': 'BENEDITA FICTICIA LIMA', 'cpfCnpj': '00000000002', 'mobilePhone': '69900000002'},
    'cus_ex03': {'id': 'cus_ex03', 'name': 'CARLOS MODELO SANTOS', 'cpfCnpj': '00000000003', 'mobilePhone': '69900000003'},
    'cus_ex04': {'id': 'cus_ex04', 'name': 'DIRCE TESTE OLIVEIRA', 'cpfCnpj': '00000000004', 'mobilePhone': '69900000004'},
    'cus_ex05': {'id': 'cus_ex05', 'name': 'EDSON DEMONSTRACAO ROCHA', 'cpfCnpj': '00000000005', 'mobilePhone': ''},
    'cus_ex06': {'id': 'cus_ex06', 'name': 'FATIMA AMOSTRA COSTA', 'cpfCnpj': '00000000006', 'mobilePhone': '69900000006'},
    'cus_ex07': {'id': 'cus_ex07', 'name': 'GERALDO SIMULADO ALVES', 'cpfCnpj': '00000000007', 'mobilePhone': '69900000007'},
}

# no exemplo, este cliente faz o papel de quem esta em clientes_nao_cobrar.txt
NAO_COBRAR = {'ids': set(), 'cpfs': set(), 'nomes': ['FATIMA AMOSTRA']}


def _cob(n, cliente, valor, venc, status, desc='Honorarios advocaticios - parcela', pago=None):
    return {'id': f'pay_ex{n:03d}', 'customer': cliente, 'value': valor, 'netValue': round(valor * 0.985, 2),
            'dueDate': venc.isoformat(), 'status': status, 'description': desc,
            'paymentDate': pago.isoformat() if pago else None,
            'invoiceUrl': f'https://www.asaas.com/i/EXEMPLO{n:03d}', 'billingType': 'UNDEFINED'}


def cobrancas_abertas(hoje=None):
    """Cobrancas PENDING/OVERDUE espalhadas pela regua."""
    h = hoje or date.today()
    d = lambda n: h + timedelta(days=n)  # noqa: E731
    return [
        _cob(1, 'cus_ex01', 2500.00, d(3), 'PENDING'),                        # lembrete 3 dias antes
        _cob(2, 'cus_ex02', 1800.00, d(0), 'PENDING', 'Honorarios advocaticios - entrada'),  # vence hoje
        _cob(3, 'cus_ex03', 2500.00, d(-1), 'OVERDUE'),                       # D+1
        _cob(4, 'cus_ex03', 2500.00, d(-5), 'OVERDUE'),                       # D+5 do mesmo cliente: 1 mensagem so
        _cob(5, 'cus_ex04', 3200.00, d(-15), 'OVERDUE'),                      # D+15
        _cob(6, 'cus_ex04', 3200.00, d(-47), 'OVERDUE'),                      # fora da regua: so inadimplencia
        _cob(7, 'cus_ex05', 1500.00, d(-5), 'OVERDUE'),                       # sem telefone no Asaas
        _cob(8, 'cus_ex06', 4000.00, d(-1), 'OVERDUE'),                       # na lista de nao cobrar
        _cob(9, 'cus_ex07', 2000.00, d(10), 'PENDING'),                       # a vencer, fora da regua hoje
        _cob(10, 'cus_ex07', 2000.00, d(-2), 'OVERDUE'),                      # D+2: janela do D+1 (rotina nao rodou ontem)
    ]


def recebidos_do_mes(ano, mes):
    """Cobrancas pagas no mes (Asaas)."""
    dia = lambda n: date(ano, mes, n)  # noqa: E731
    return [
        _cob(21, 'cus_ex01', 2500.00, dia(5), 'RECEIVED', pago=dia(5)),
        _cob(22, 'cus_ex02', 1800.00, dia(8), 'RECEIVED', 'Honorarios advocaticios - entrada', pago=dia(9)),
        _cob(23, 'cus_ex03', 2500.00, dia(10), 'CONFIRMED', pago=dia(10)),
        _cob(24, 'cus_ex07', 2000.00, dia(15), 'RECEIVED', 'Honorarios advocaticios - parcela _P1', pago=dia(16)),
        _cob(25, 'cus_ex04', 3200.00, dia(20), 'RECEIVED_IN_CASH', pago=dia(22)),   # nao lancado no ADVBOX
    ]


def transacoes_advbox(ano, mes):
    """Lancamentos do ADVBOX com vencimento no mes (receitas e despesas)."""
    dia = lambda n: f'{ano}-{mes:02d}-{n:02d}'  # noqa: E731
    t = lambda i, tipo, nome, valor, venc, cat, desc, pago=True: {  # noqa: E731
        'id': 9000 + i, 'entry_type': tipo, 'name': nome, 'amount': valor, 'date_due': venc,
        'date_payment': venc if pago else None, 'category': cat, 'description': desc}
    return [
        t(1, 'income', 'ANTONIO EXEMPLO PEREIRA', 2500.00, dia(5), 'HONORARIOS INICIAIS', 'Parcela 2/6'),
        t(2, 'income', 'BENEDITA FICTICIA LIMA', 1800.00, dia(8), 'HONORARIOS INICIAIS', 'Entrada'),
        t(3, 'income', 'CARLOS MODELO SANTOS', 2500.00, dia(10), 'HONORARIOS INICIAIS', 'Parcela 3/6'),
        t(4, 'income', 'GERALDO SIMULADO ALVES', 2000.00, dia(15), 'HONORARIOS INICIAIS', 'Parcela 1/4'),
        t(5, 'income', 'HELENA PIX DIRETO', 6000.00, dia(18), 'HONORARIOS DE EXITO', 'Exito - PIX na conta'),
        t(6, 'income', 'IVO PENDENTE MOURA', 1200.00, dia(25), 'HONORARIOS INICIAIS', 'Parcela 4/6', pago=False),
        t(7, 'expense', 'IMOBILIARIA EXEMPLO', 3500.00, dia(5), 'ALUGUEL', 'Aluguel do escritorio'),
        t(8, 'expense', 'EQUIPE', 6800.00, dia(5), 'SALARIOS', 'Folha do mes'),
        t(9, 'expense', 'SISTEMAS', 890.00, dia(10), 'SOFTWARE', 'ADVBOX + Atende Direito + ZapSign'),
        t(10, 'expense', 'CONTABILIDADE', 650.00, dia(12), 'CONTABILIDADE', 'Honorarios contabeis'),
        t(11, 'expense', 'RECEITA FEDERAL', 1340.00, dia(20), 'IMPOSTOS', 'DAS Simples Nacional'),
        t(12, 'expense', 'SOCIOS', 5000.00, dia(28), 'DISTRIBUICAO DE LUCROS', 'Distribuicao aos socios'),
        t(13, 'expense', 'ENERGIA', 420.00, dia(27), 'CONSUMO', 'Conta de energia', pago=False),
    ]


def a_pagar_14_dias(hoje=None):
    h = hoje or date.today()
    return [
        {'id': 9901, 'entry_type': 'expense', 'name': 'IMOBILIARIA EXEMPLO', 'amount': 3500.00,
         'date_due': (h + timedelta(days=6)).isoformat(), 'date_payment': None, 'category': 'ALUGUEL',
         'description': 'Aluguel do escritorio'},
        {'id': 9902, 'entry_type': 'expense', 'name': 'SISTEMAS', 'amount': 890.00,
         'date_due': (h + timedelta(days=11)).isoformat(), 'date_payment': None, 'category': 'SOFTWARE',
         'description': 'Assinaturas de sistemas'},
    ]


def casos_contratacao(hoje=None):
    """Casos ficticios no formato do caso.json da CONTRATACAO: (pasta, caso)."""
    h = hoje or date.today()
    iso = lambda n: (h - timedelta(days=n)).isoformat()  # noqa: E731
    base = 'CLIENTES/AGRONEGOCIO/'
    cad_ok = {'honorarios_entrada_valor': '3.000,00', 'honorarios_entrada_vencimento': '10/10/2026',
              'honorarios_parcelas_qtd': '6', 'honorarios_parcela_valor': '2.500,00',
              'honorarios_parcelas_primeiro_vencimento': '10/11/2026',
              'honorarios_entrada': 'R$ 3.000,00 na assinatura', 'honorarios_exito': '10% do proveito'}
    return [
        (base + 'ANTONIO EXEMPLO PEREIRA', {
            'etapa': 'COBRANCA DE DOCUMENTOS', 'data_contrato': iso(12), 'enviado_em': iso(11),
            'qualificacao': {'nome': 'ANTONIO EXEMPLO PEREIRA', 'cpf': '000.000.000-01'},
            'cadastro': cad_ok, 'zapsign': [{'documento': 'Contrato'}],
            'asaas': [{'descricao': 'Entrada', 'link': 'https://www.asaas.com/i/EXEMPLO101', 'id': 'pay_ex101'},
                      {'descricao': '6 parcelas', 'link': 'https://www.asaas.com/i/EXEMPLO102', 'id': 'pay_ex102'}]}),
        (base + 'BENEDITA FICTICIA LIMA', {
            'etapa': 'AGUARDANDO ASSINATURA', 'data_contrato': iso(4), 'enviado_em': iso(3),
            'qualificacao': {'nome': 'BENEDITA FICTICIA LIMA', 'cpf': '000.000.000-02'},
            'cadastro': cad_ok, 'zapsign': [{'documento': 'Contrato'}], 'asaas': []}),
        (base + 'CARLOS MODELO SANTOS', {
            'etapa': 'DOCUMENTOS GERADOS', 'data_contrato': iso(1),
            'qualificacao': {'nome': 'CARLOS MODELO SANTOS', 'cpf': '000.000.000-03'},
            'cadastro': cad_ok}),
        (base + 'DIRCE TESTE OLIVEIRA', {
            'etapa': 'AGUARDANDO ASSINATURA', 'data_contrato': iso(6), 'enviado_em': iso(5),
            'qualificacao': {'nome': 'DIRCE TESTE OLIVEIRA', 'cpf': '000.000.000-04'},
            'cadastro': {'honorarios_entrada': 'entrada a combinar', 'honorarios_pagamento': 'parcelado na safra'},
            'zapsign': [{'documento': 'Contrato'}]}),
    ]

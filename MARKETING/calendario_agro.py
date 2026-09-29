"""
Calendario do produtor de Rondonia e do norte de Mato Grosso, mes a mes - da o GANCHO SAZONAL dos posts.

Dados no codigo (sem internet): lavoura (soja, milho safrinha, cafe da regiao), pecuaria, clima,
credito rural (vencimentos tipicos, Plano Safra, juros semestrais), datas e sugestoes de pauta por pilar.

IMPORTANTE: e um calendario GERAL. Datas mudam por ano, municipio, cultivar e cedula. Tudo que tem
[CONFERIR] precisa ser checado no ano (portaria, decreto, calendario oficial) antes de virar post.
O verificador de conformidade bloqueia qualquer post que ainda tenha [CONFERIR].

Uso direto:
    python MARKETING/calendario_agro.py            (ano inteiro)
    python MARKETING/calendario_agro.py --mes 7
"""
import argparse
import calendar
import datetime
import sys

FONTE = ('Calendário agrícola geral de Rondônia e do norte de Mato Grosso, montado a partir de referências públicas '
         '(calendários de plantio e colheita da CONAB, IDARON/RO, INDEA/MT, MAPA/Plano Safra, INMET) e da experiência '
         'do escritório. Datas variam por ano, município e cultivar: itens com [CONFERIR] precisam ser checados no ano.')

# Pilares editoriais (mesmos ids usados no conteudo.py)
PILARES = {
    'direitos_divida': 'Direitos do produtor na dívida rural (prorrogação e alongamento)',
    'frustracao_safra': 'Frustração de safra (estiagem, excesso de chuva, praga, queda de preço)',
    'negativacao_avalista': 'Negativação, execução, busca e apreensão e direitos do avalista',
    'documentos': 'Documentos que o produtor deve guardar',
    'bastidores': 'Bastidores e autoridade do escritório (como trabalhamos, sem resultado de cliente)',
    'previdenciario': 'Previdenciário rural (salário-maternidade rural, BPC, aposentadoria rural)',
}

MESES = {
    1: {
        'nome': 'Janeiro',
        'lavoura': ['Soja: início da colheita no norte de MT e enchimento de grãos em RO.',
                    'Risco de veranico (dias seguidos sem chuva) no enchimento de grãos [CONFERIR previsão do ano].',
                    'Milho safrinha: começa o plantio logo atrás da colheita da soja no norte de MT.'],
        'pecuaria': ['Período das águas: pasto bom, engorda a pasto.', 'Estação de monta em andamento em muitas fazendas.'],
        'clima': ['Estação chuvosa em RO e MT.'],
        'credito': ['Juros das cédulas rurais costumam ser exigidos em 30/06 e 31/12 (DL 167/67, art. 5º) '
                    '- conferir na cédula de cada produtor.',
                    'Começa a preparação para os vencimentos de custeio que caem após a colheita.'],
        'datas': [(4, 'Instalação do Estado de Rondônia (1982) [CONFERIR data comemorativa oficial]')],
        'ganchos': [('frustracao_safra', 'Veranico no enchimento de grãos: como registrar a perda desde o primeiro dia'),
                    ('documentos', 'Antes de colher: monte o "diário da safra" com fotos, datas e anotações'),
                    ('direitos_divida', 'Vai vencer depois da colheita? Por que o pedido de prorrogação é feito por escrito')],
    },
    2: {
        'nome': 'Fevereiro',
        'lavoura': ['Soja: pico da colheita no norte de MT e começo da colheita em RO.',
                    'Milho safrinha: plantio em ritmo forte (janela depende da colheita da soja).'],
        'pecuaria': ['Águas: boa oferta de pasto.'],
        'clima': ['Chuva intensa pode atrapalhar a colheita (grão ardido, perda de qualidade).',
                  'Cheias de rios e estradas vicinais ruins podem afetar o escoamento [CONFERIR situação do ano].'],
        'credito': ['Preço da soja tende a ficar pressionado no pico da colheita (maior oferta) [CONFERIR cotação do ano].'],
        'datas': [],
        'ganchos': [('frustracao_safra', 'Chuva demais na colheita também é fator adverso: o que o MCR 2.6.4 prevê'),
                    ('frustracao_safra', 'Preço baixo na colheita e a "dificuldade de comercialização"'),
                    ('documentos', 'Nota fiscal de venda e romaneio: provas da safra que você colheu')],
    },
    3: {
        'nome': 'Março',
        'lavoura': ['Soja: colheita avançando em RO (Cone Sul e região de Cacoal).',
                    'Milho safrinha: fim da janela de plantio [CONFERIR zoneamento agrícola do ano].'],
        'pecuaria': ['Fim das águas se aproximando; começa a desmama em parte das fazendas.'],
        'clima': ['Ainda chuvoso; enchentes podem afetar logística [CONFERIR].'],
        'credito': ['Começa o prazo de entrega da declaração de Imposto de Renda (atividade rural / livro caixa) '
                    '[CONFERIR prazo da Receita no ano].'],
        'datas': [(8, 'Dia Internacional da Mulher')],
        'ganchos': [('documentos', 'Imposto de Renda do produtor: o livro caixa também é prova da perda'),
                    ('previdenciario', 'Mulher do campo: salário-maternidade da trabalhadora rural, quem pode pedir'),
                    ('frustracao_safra', 'Produção esperada x produção colhida: a conta que o produtor precisa ter anotada')],
    },
    4: {
        'nome': 'Abril',
        'lavoura': ['Soja: fim da colheita em RO.', 'Café da região (robusta/conilon): início da colheita [CONFERIR].'],
        'pecuaria': ['Desmama e venda de bezerros em muitas fazendas.', 'Oferta de boi gordo das águas pode pressionar a arroba.'],
        'clima': ['Transição para a seca no fim do mês.'],
        'credito': ['Vencimentos de custeio da soja costumam cair após a colheita (abril a junho) [CONFERIR na cédula].',
                    'Declaração de Imposto de Renda em andamento.'],
        'datas': [],
        'ganchos': [('direitos_divida', 'Parcela do custeio vencendo e a safra não pagou: o que a norma prevê'),
                    ('direitos_divida', 'Prorrogação x renegociação oferecida pelo banco: entenda a diferença antes de assinar'),
                    ('negativacao_avalista', 'Por que o nome limpo pesa tanto para quem produz')],
    },
    5: {
        'nome': 'Maio',
        'lavoura': ['Milho safrinha: enchimento de grãos; falta de chuva no fim do ciclo é risco.',
                    'Café da região: colheita [CONFERIR].'],
        'pecuaria': ['Começo da seca: pasto perde qualidade; suplementação encarece a produção.',
                     'Etapa de atualização cadastral/declaração de rebanho no IDARON [CONFERIR calendário oficial].'],
        'clima': ['Início da estação seca em RO.'],
        'credito': ['Fim do prazo do Imposto de Renda [CONFERIR data].', 'Vencimentos de custeio da soja [CONFERIR na cédula].'],
        'datas': [('2dom', 'Dia das Mães (2º domingo de maio)'),
                  (None, 'Rondônia Rural Show (Ji-Paraná) costuma ocorrer no fim de maio [CONFERIR data do ano]')],
        'ganchos': [('previdenciario', 'Salário-maternidade rural: documentos que mostram o trabalho no campo'),
                    ('documentos', 'Extrato do IDARON e GTAs: por que guardar'),
                    ('bastidores', 'O que a equipe do escritório analisa numa cédula de crédito rural')],
    },
    6: {
        'nome': 'Junho',
        'lavoura': ['Milho safrinha: começo da colheita.',
                    'Vazio sanitário da soja em vigor em RO e MT [CONFERIR datas da portaria do ano].'],
        'pecuaria': ['Seca: entressafra do boi, pasto seco, custo de suplementação maior.'],
        'clima': ['Seca; friagens podem ocorrer no sul de RO [CONFERIR].'],
        'credito': ['30 de junho: data em que os juros das cédulas rurais costumam ser exigidos (DL 167/67, art. 5º) '
                    '- conferir na cédula.',
                    'Fim do ano-safra (30/06) e anúncio do Plano Safra do próximo ciclo (fim de junho/início de julho) '
                    '[CONFERIR data do anúncio].'],
        'datas': [(5, 'Dia Mundial do Meio Ambiente')],
        'ganchos': [('direitos_divida', '30 de junho: o que são os juros semestrais da cédula rural'),
                    ('frustracao_safra', 'Seca no fim do ciclo do milho safrinha: como documentar a quebra'),
                    ('negativacao_avalista', 'Penhor de safra e de rebanho: o que é ser fiel depositário')],
    },
    7: {
        'nome': 'Julho',
        'lavoura': ['Milho safrinha: colheita.', 'Planejamento e contratação do custeio da próxima soja.'],
        'pecuaria': ['Seca forte; risco de perda de peso do rebanho e mortalidade em pasto ruim.'],
        'clima': ['Seca; começam os focos de queimada.',
                  'Decretos de emergência por estiagem costumam sair na seca (julho a outubro) [CONFERIR se houve no ano].'],
        'credito': ['Começa o novo ano-safra (1º de julho) com as regras do Plano Safra [CONFERIR normas do ano].',
                    'Contratação do custeio da soja: hora de ler a cédula antes de assinar.'],
        'datas': [(25, 'Dia do Trabalhador Rural [CONFERIR]'), (28, 'Dia do Agricultor')],
        'ganchos': [('direitos_divida', 'Novo ano-safra: o que conferir na cédula antes de assinar'),
                    ('frustracao_safra', 'Decreto de emergência por estiagem: o que ele significa e o que não significa para a sua dívida'),
                    ('bastidores', 'Dia do Agricultor: por que o escritório escolheu atuar ao lado de quem produz')],
    },
    8: {
        'nome': 'Agosto',
        'lavoura': ['Fim da colheita do milho safrinha.', 'Preparo de área e compra de insumos para a soja.'],
        'pecuaria': ['Pico da seca; nascimentos de bezerros em muitas fazendas.'],
        'clima': ['Pico de queimadas em RO e norte de MT.'],
        'credito': ['Declaração do ITR costuma ser entregue entre agosto e setembro [CONFERIR prazo da Receita].',
                    'Vencimentos de custeio do milho safrinha [CONFERIR na cédula].'],
        'datas': [(11, 'Dia do Advogado'), ('2dom', 'Dia dos Pais (2º domingo de agosto)')],
        'ganchos': [('frustracao_safra', 'Queimada atingiu a pastagem: o que registrar e guardar'),
                    ('documentos', 'ITR, CAR e CCIR em dia: documentos do imóvel que também servem de prova'),
                    ('negativacao_avalista', 'Pai, filho e esposa como avalistas: o que cada um assina')],
    },
    9: {
        'nome': 'Setembro',
        'lavoura': ['Fim do vazio sanitário e começo do plantio da soja no norte de MT [CONFERIR datas].',
                    'Café da região: florada com a volta das chuvas [CONFERIR].'],
        'pecuaria': ['Fim da seca; pastagens castigadas.'],
        'clima': ['Queimadas ainda altas; chuvas voltam no fim do mês [CONFERIR previsão].'],
        'credito': ['Prazo final do ITR [CONFERIR data].', 'Liberação do custeio da soja.'],
        'datas': [],
        'ganchos': [('frustracao_safra', 'Pastagem castigada pela seca: praga e queimada contam como ocorrência prejudicial?'),
                    ('negativacao_avalista', 'Recebeu citação em execução? Os prazos de defesa são curtos'),
                    ('documentos', 'Pedido ao banco por e-mail: como guardar a prova do envio')],
    },
    10: {
        'nome': 'Outubro',
        'lavoura': ['Soja: pico do plantio em RO (depende da regularidade das chuvas).'],
        'pecuaria': ['Volta das águas; começa a estação de monta.'],
        'clima': ['Chuvas irregulares no começo podem atrasar ou obrigar replantio.'],
        'credito': ['Custeio liberado e insumos comprados: notas de compra são prova do investimento na lavoura.'],
        'datas': [(16, 'Dia Mundial da Alimentação')],
        'ganchos': [('frustracao_safra', 'Replantio por falta de chuva: anote datas, áreas e custos'),
                    ('documentos', 'Notas fiscais de insumos: por que guardar desde o plantio'),
                    ('direitos_divida', 'CCB, CPR, cheque especial: dívida com cara de comercial pode ser crédito rural?')],
    },
    11: {
        'nome': 'Novembro',
        'lavoura': ['Soja: fim do plantio em RO; lavouras em desenvolvimento.'],
        'pecuaria': ['Águas; estação de monta.',
                     'Etapa de atualização cadastral/declaração de rebanho no IDARON [CONFERIR calendário oficial].'],
        'clima': ['Estação chuvosa.'],
        'credito': ['Mês de promoções no comércio: o escritório NÃO faz "Black Friday" nem promoção (Provimento 205/2021).'],
        'datas': [(26, 'Aniversário de Cacoal [CONFERIR data]')],
        'ganchos': [('negativacao_avalista', 'Busca e apreensão de máquina financiada: entenda o básico'),
                    ('bastidores', 'Como é a primeira conversa com o escritório e o que perguntamos'),
                    ('previdenciario', 'BPC: o que é e quem pode ter direito')],
    },
    12: {
        'nome': 'Dezembro',
        'lavoura': ['Soja em desenvolvimento; veranico nesta fase é risco [CONFERIR previsão].'],
        'pecuaria': ['Águas; engorda a pasto.'],
        'clima': ['Chuvas intensas; decretos de emergência podem sair também no fim do ano [CONFERIR se houve].'],
        'credito': ['31 de dezembro: data em que os juros das cédulas rurais costumam ser exigidos (DL 167/67, art. 5º) '
                    '- conferir na cédula.', 'Fechamento do ano: balanço da safra e da dívida.'],
        'datas': [(22, 'Criação do Estado de Rondônia (1981) [CONFERIR data comemorativa oficial]')],
        'ganchos': [('documentos', 'Fechamento do ano: a pasta de documentos que todo produtor deveria ter'),
                    ('frustracao_safra', 'Balanço da safra: produção esperada x colhida'),
                    ('direitos_divida', 'Já prorroguei uma vez. Posso pedir de novo?')],
    },
}


def mes(m):
    return MESES[int(m)]


def _segundo_domingo(ano, m):
    dias = [d for d in range(1, 15) if datetime.date(ano, m, d).weekday() == 6]
    return dias[1]


def datas_do_mes(m, ano):
    """Lista de (datetime.date | None, texto) das datas do mes (None = data variavel sem dia fixo)."""
    saida = []
    for dia, texto in mes(m)['datas']:
        if dia == '2dom':
            saida.append((datetime.date(ano, m, _segundo_domingo(ano, m)), texto))
        elif isinstance(dia, int) and dia <= calendar.monthrange(ano, m)[1]:
            saida.append((datetime.date(ano, m, dia), texto))
        else:
            saida.append((None, texto))
    return saida


def ganchos_do_mes(m, pilar=None):
    return [t for p, t in mes(m)['ganchos'] if pilar is None or p == pilar]


def contexto_curto(m):
    """Uma frase de contexto sazonal (primeiro item de lavoura + pecuaria + clima)."""
    d = mes(m)
    partes = [d['lavoura'][0], d['pecuaria'][0], d['clima'][0]]
    return ' '.join(partes)


def resumo_mes(m, ano=None):
    """Texto do mes (para o prompt da IA e para o DOCX)."""
    d = mes(m)
    ano = ano or datetime.date.today().year
    linhas = [f'{d["nome"].upper()} no campo (RO e norte de MT):']
    for chave, rotulo in (('lavoura', 'Lavoura'), ('pecuaria', 'Pecuária'), ('clima', 'Clima'), ('credito', 'Crédito rural')):
        for item in d[chave]:
            linhas.append(f'- {rotulo}: {item}')
    for data, texto in datas_do_mes(m, ano):
        linhas.append(f'- Data: {data.strftime("%d/%m") + " - " if data else ""}{texto}')
    linhas.append('Sugestões de pauta do mês:')
    for p, t in d['ganchos']:
        linhas.append(f'- [{p}] {t}')
    return '\n'.join(linhas)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Calendário do produtor (RO / norte de MT)')
    ap.add_argument('--mes', type=int, help='1 a 12 (padrão: ano inteiro)')
    ap.add_argument('--ano', type=int, default=datetime.date.today().year)
    args = ap.parse_args(argv)
    meses = [args.mes] if args.mes else range(1, 13)
    for m in meses:
        print(resumo_mes(m, args.ano))
        print()
    print('Fonte:', FONTE)
    return 0


if __name__ == '__main__':
    sys.exit(main())

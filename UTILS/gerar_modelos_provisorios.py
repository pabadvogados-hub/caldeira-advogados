"""
Gera os modelos PROVISORIOS de contrato, procuracao e declaracao em DOCS_MODELOS/.

Eles existem so para a fase de contratacao rodar de ponta a ponta enquanto o escritorio
nao entrega os modelos oficiais (.docx). Cada um comeca com a marca
[CONFERIR: MODELO PROVISORIO ...], que TRAVA o envio para assinatura.

Para usar o modelo oficial: salve o .docx do escritorio em DOCS_MODELOS/ com o mesmo nome,
troque os dados do cliente pelos {{CAMPOS}} listados em docs/CAMPOS_DOS_MODELOS.md e
apague a linha da marca.

    python UTILS/gerar_modelos_provisorios.py            (nao sobrescreve modelo existente)
    python UTILS/gerar_modelos_provisorios.py --forcar
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'CONTRATACAO'))
sys.path.insert(0, RAIZ)
from docx_caldeira import novo_documento, paragrafo, secao, titulo  # noqa: E402

DOCS = os.path.join(RAIZ, 'DOCS_MODELOS')
MARCA = '[CONFERIR: MODELO PROVISÓRIO gerado pela automação. Substituir pelo modelo oficial do escritório antes de enviar para assinatura]'

QUALIFICACAO = ('{{NOME}}, {{NACIONALIDADE}}, {{ESTADO_CIVIL}}, {{PROFISSAO}}, portador(a) da cédula de identidade '
                'RG nº {{RG}} {{ORGAO_EMISSOR}}, inscrito(a) no CPF sob o nº {{CPF}}, residente e domiciliado(a) em '
                '{{ENDERECO_COMPLETO}}, telefone {{TELEFONE}}, e-mail {{EMAIL}}')

ESCRITORIO_TXT = ('CALDEIRA ADVOGADOS ASSOCIADOS, sociedade de advogados inscrita no CNPJ sob o nº {{ESCRITORIO_CNPJ}}, '
                  'com endereço profissional na {{ESCRITORIO_ENDERECO}}, e-mail {{ESCRITORIO_EMAIL}}')


def _assinatura(doc, nome, detalhe=''):
    paragrafo(doc, ' ')
    p = paragrafo(doc, '_______________________________________')
    p.alignment = 1
    p = paragrafo(doc, nome, negrito=True)
    p.alignment = 1
    if detalhe:
        p = paragrafo(doc, detalhe)
        p.alignment = 1


def procuracao():
    doc = novo_documento()
    paragrafo(doc, MARCA)
    titulo(doc, 'Procuração')
    paragrafo(doc, QUALIFICACAO + '.', rotulo='OUTORGANTE')
    paragrafo(doc, '{{OUTORGADOS}}, integrantes de ' + ESCRITORIO_TXT + '.', rotulo='OUTORGADOS')
    paragrafo(doc, 'Os da cláusula ad judicia et extra, para o foro em geral, em qualquer juízo, instância ou '
                   'tribunal, inclusive na Justiça Federal, podendo propor contra quem de direito as ações '
                   'competentes e defender o(a) Outorgante nas contrárias, seguindo umas e outras até decisão final, '
                   'usando os recursos legais e acompanhando-os, com poderes especiais para confessar, reconhecer a '
                   'procedência do pedido, transigir, desistir, renunciar ao direito sobre o qual se funda a ação, '
                   'receber, dar quitação, firmar compromisso, requerer a gratuidade da justiça e firmar declaração de '
                   'hipossuficiência econômica, e substabelecer com ou sem reserva de poderes.', rotulo='PODERES')
    paragrafo(doc, 'Representar o(a) Outorgante perante bancos, cooperativas de crédito, o Banco Central do Brasil, '
                   'órgãos de proteção ao crédito e cartórios, para requerer cópias de contratos, cédulas, aditivos, '
                   'extratos e demonstrativos de débito; notificar extrajudicialmente; requerer a prorrogação, o '
                   'alongamento, a renegociação ou a repactuação de operações de crédito rural; e registrar reclamações '
                   'em plataformas públicas, como o consumidor.gov.br.', rotulo='PODERES EXTRAJUDICIAIS')
    paragrafo(doc, '{{OBJETO}}', rotulo='FINALIDADE')
    paragrafo(doc, '{{CIDADE_UF}}, {{DATA_EXTENSO}}.')
    _assinatura(doc, '{{NOME}}', 'CPF {{CPF}}')
    doc.save(os.path.join(DOCS, 'PROCURACAO_MODELO.docx'))


def declaracao():
    doc = novo_documento()
    paragrafo(doc, MARCA)
    titulo(doc, 'Declaração de Hipossuficiência')
    paragrafo(doc, QUALIFICACAO + ', DECLARA, para os fins do artigo 99, § 3º, do Código de Processo Civil, que '
                   'não possui condições de arcar com as custas e despesas processuais sem prejuízo do próprio sustento '
                   'e do de sua família, razão pela qual requer os benefícios da gratuidade da justiça.', recuo=True)
    paragrafo(doc, 'Declara, ainda, estar ciente de que a falsidade desta declaração sujeita o(a) declarante às '
                   'sanções civis, administrativas e penais previstas em lei.', recuo=True)
    paragrafo(doc, '{{CIDADE_UF}}, {{DATA_EXTENSO}}.')
    _assinatura(doc, '{{NOME}}', 'CPF {{CPF}}')
    doc.save(os.path.join(DOCS, 'DECLARACAO_HIPOSSUFICIENCIA_MODELO.docx'))


def contrato():
    doc = novo_documento()
    paragrafo(doc, MARCA)
    titulo(doc, 'Contrato de Prestação de Serviços Advocatícios')
    paragrafo(doc, 'Contrato nº {{NUMERO_CONTRATO}}', negrito=True).alignment = 1
    paragrafo(doc, QUALIFICACAO + ', doravante CONTRATANTE.', rotulo='CONTRATANTE')
    paragrafo(doc, ESCRITORIO_TXT + ', neste ato representada por {{TITULAR_NOME}}, {{TITULAR_OAB}}, doravante '
                   'CONTRATADA.', rotulo='CONTRATADA')
    paragrafo(doc, 'As partes acima qualificadas celebram o presente contrato, que se regerá pelas cláusulas a seguir.',
              recuo=True)

    clausulas = [
        ('Cláusula 1ª. Do objeto',
         'A CONTRATADA prestará serviços advocatícios ao CONTRATANTE na defesa de seus interesses relativos às '
         'operações de crédito rural mantidas com as seguintes instituições credoras: {{BANCOS}}, compreendendo a análise da documentação, a '
         'notificação extrajudicial das instituições credoras, a negociação e, se necessário, o ajuizamento e o '
         'acompanhamento da ação judicial cabível, com pedido de tutela de urgência.'),
        ('Cláusula 2ª. Dos honorários',
         'Pelos serviços, o CONTRATANTE pagará à CONTRATADA: (a) {{HONORARIOS_ENTRADA}}; (b) forma de pagamento: '
         '{{HONORARIOS_PAGAMENTO}}; e (c) honorários de êxito de {{HONORARIOS_EXITO}}. Os honorários de '
         'sucumbência pertencem exclusivamente à CONTRATADA.'),
        ('Cláusula 3ª. Das despesas',
         'Custas, emolumentos, laudos técnicos (agronômico e financeiro), perícias e demais despesas do caso correm por '
         'conta do CONTRATANTE, salvo concessão da gratuidade da justiça, e não se confundem com os honorários.'),
        ('Cláusula 4ª. Das obrigações do CONTRATANTE',
         'O CONTRATANTE se obriga a fornecer, em até 5 (cinco) dias, cópias de TODOS os contratos e cédulas de TODOS os '
         'bancos, extratos, comprovantes de pagamento, matrícula do imóvel rural, documentação fiscal e demais '
         'documentos solicitados; a informar imediatamente qualquer vencimento, cobrança, notificação ou citação que '
         'receber; e a não firmar acordo ou renegociação com os credores sem ciência da CONTRATADA.'),
        ('Cláusula 5ª. Das obrigações da CONTRATADA',
         'A CONTRATADA se obriga a atuar com zelo e diligência, a manter o CONTRATANTE informado sobre o andamento do '
         'caso e a guardar sigilo profissional. A obrigação é de meio, não de resultado.'),
        ('Cláusula 6ª. Da proteção de dados',
         'Os dados pessoais do CONTRATANTE serão tratados exclusivamente para a execução deste contrato e o exercício '
         'regular de direitos, nos termos da Lei nº 13.709/2018.'),
        ('Cláusula 7ª. Da rescisão',
         'A revogação do mandato ou a rescisão deste contrato por iniciativa do CONTRATANTE não o desobriga do pagamento '
         'dos honorários proporcionais aos serviços já prestados e dos honorários de êxito sobre o proveito obtido até '
         'então.'),
        ('Cláusula 8ª. Do título executivo',
         'Este contrato constitui título executivo extrajudicial, nos termos do artigo 24 da Lei nº 8.906/1994.'),
        ('Cláusula 9ª. Do foro',
         'Fica eleito o foro da comarca de {{CIDADE_UF}} para dirimir as questões oriundas deste contrato.'),
    ]
    for nome, texto in clausulas:
        secao(doc, nome)
        paragrafo(doc, texto, recuo=True)

    paragrafo(doc, 'E, por estarem justas e contratadas, as partes assinam o presente instrumento por meio eletrônico, '
                   'que reconhecem como válido.', recuo=True)
    paragrafo(doc, '{{CIDADE_UF}}, {{DATA_EXTENSO}}.')
    _assinatura(doc, '{{NOME}}', 'CONTRATANTE')
    _assinatura(doc, 'CALDEIRA ADVOGADOS ASSOCIADOS', '{{TITULAR_NOME}} · {{TITULAR_OAB}}')
    doc.save(os.path.join(DOCS, 'CONTRATO_HONORARIOS_MODELO.docx'))


if __name__ == '__main__':
    os.makedirs(DOCS, exist_ok=True)
    forcar = '--forcar' in sys.argv
    for nome, fn in (('PROCURACAO_MODELO.docx', procuracao), ('DECLARACAO_HIPOSSUFICIENCIA_MODELO.docx', declaracao),
                     ('CONTRATO_HONORARIOS_MODELO.docx', contrato)):
        caminho = os.path.join(DOCS, nome)
        if os.path.exists(caminho) and not forcar:
            print(f'mantido (ja existe): {nome}')
            continue
        fn()
        print(f'gerado: {nome}')

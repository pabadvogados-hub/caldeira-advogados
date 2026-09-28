"""
Textos que vao para o produtor pelo WhatsApp (Atende Direito).
Linguagem simples, direta, sem juridiques. Nada de senha por mensagem.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from config.escritorio import ESCRITORIO  # noqa: E402

ASSINATURA = ESCRITORIO['nome']

COMO_MANDAR = {
    'pessoais': 'foto da CNH ou do RG (frente e verso)',
    'endereco': 'uma conta de luz, água ou telefone recente no seu nome',
    'contratos': 'cópia de TODOS os contratos e cédulas de TODOS os bancos, com os aditivos',
    'extratos': 'extratos das contas nos bancos onde tem financiamento',
    'pagamentos': 'comprovantes das parcelas que já pagou',
    'frustracao': 'o que tiver sobre a perda da safra (laudo, fotos, decreto de emergência, Proagro)',
    'matricula': 'matrícula do imóvel rural (pode ser do cartório ou o CAR/CCIR)',
    'fiscal': 'notas fiscais de venda da produção',
    'procuracao': 'a procuração assinada (pelo link que mandamos)',
}


def primeiro_nome(nome):
    return (nome or '').split(' ')[0].title() or 'tudo bem'


def lista_faltando(faltando):
    linhas = []
    for i, item in enumerate(faltando, 1):
        if item.get('sensivel'):
            linhas.append(f'{i}. Senha do GOV.BR: não mande por mensagem, a gente pega com você por ligação')
        else:
            linhas.append(f"{i}. {COMO_MANDAR.get(item['id'], item['nome'])}")
    return '\n'.join(linhas)


def assinatura_e_documentos(nome, links, faltando):
    txt = f'Olá, {primeiro_nome(nome)}! Aqui é do {ASSINATURA}.\n\n'
    txt += 'Seus documentos já estão prontos para assinar pelo celular:\n'
    for l in links:
        txt += f"\n{l['documento']}: {l['link']}"
    if faltando:
        txt += ('\n\nPara a gente já notificar os bancos, precisamos destes documentos '
                '(pode mandar foto por aqui mesmo):\n\n' + lista_faltando(faltando))
    txt += '\n\nQualquer dúvida, é só responder esta mensagem.'
    return txt


def cobranca_documentos(nome, faltando, toque):
    nome = primeiro_nome(nome)
    if toque == 1:
        abertura = f'Olá, {nome}! Aqui é do {ASSINATURA}. Para darmos andamento no seu caso, ainda faltam:'
    elif toque == 2:
        abertura = (f'{nome}, tudo bem? Seu caso está parado esperando só estes documentos. '
                    'Assim que chegarem, notificamos os bancos:')
    else:
        abertura = (f'{nome}, sem estes documentos não conseguimos proteger você contra a cobrança dos bancos '
                    'dentro do prazo. Se tiver dificuldade para conseguir algum, responda aqui que a gente ajuda:')
    return f'{abertura}\n\n{lista_faltando(faltando)}\n\nPode mandar foto por aqui mesmo.'


def documentos_completos(nome):
    return (f'{primeiro_nome(nome)}, recebemos todos os documentos. Obrigado! Agora o seu caso segue para a '
            f'equipe jurídica e em breve você recebe as novidades por aqui.\n\n{ASSINATURA}')

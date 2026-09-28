"""
Analise da reuniao de fechamento pela IA (Claude).

1. triagem(): le a transcricao da reuniao do Closer com o produtor e monta o
   RELATORIO DE TRIAGEM que vai para o Gestor Juridico (gatilhos, gaps, operacoes
   bancarias, pontos de atencao do fluxo, estrategia candidata).
2. qualificacao(): extrai os dados pessoais do cliente, com a regra de origem:
   documento oficial (CNH/RG) > cadastro do Closer > transcricao.

A resposta vem em JSON garantido por schema (structured outputs).
A IA nao decide estrategia nem protocola: tudo sai para revisao do Gestor Juridico.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

import ia  # noqa: E402  (NUCLEO)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from config.escritorio import CHECKLIST_DOCUMENTOS, ESCRITORIO  # noqa: E402

MODELO_TRIAGEM = os.getenv('MODELO_TRIAGEM', 'claude-opus-5')
MODELO_EXTRACAO = os.getenv('MODELO_EXTRACAO', 'claude-sonnet-5')
DNA = os.path.join(RAIZ, 'BASE_CONHECIMENTO', 'DNA_PECAS.md')

PONTOS_ATENCAO = [
    'Datas de vencimento das parcelas (vencidas ou nao?)',
    'Ha execucao judicial ja em andamento?',
    'O produtor enviou TODAS as cedulas de TODOS os bancos?',
    'Todos os bancos credores estao contemplados?',
    'Prazo maximo de 60 dias: contrato ate o protocolo',
    'Tutela de urgencia: suspensao de exigibilidade + proibicao de negativacao',
    'Laudos: frustracao de safra + financeiro',
    'Ha avalistas ou garantias (alienacao fiduciaria, hipoteca, penhor) em risco?',
    'Houve pedido administrativo de prorrogacao a cada banco, por operacao (data, canal, resposta)?',
    'Ha laudo agronomico com ART e vistoria no local? (os bancos atacam laudo sem isso)',
]


def _s(desc=''):
    return {'type': 'string', 'description': desc} if desc else {'type': 'string'}


def _obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def _lista(item):
    return {'type': 'array', 'items': item}


SCHEMA_TRIAGEM = _obj({
    'data_reuniao': _s('DD/MM/AAAA, ou vazio'),
    'closer': _s('quem conduziu a reuniao pelo escritorio, ou vazio'),
    'resumo_caso': _s('3 a 6 paragrafos em linguagem juridica formal, terceira pessoa'),
    'atividade_rural': _obj({
        'tipo': _s('agricultura, pecuaria, mista ou outra'),
        'culturas_rebanho': _s(),
        'area_propriedade': _s(),
        'municipio_propriedade': _s(),
        'safra_afetada': _s('ex.: soja 2025/2026'),
        'causa_da_perda': _s('estiagem, excesso de chuva, praga, queda de preco, custo de producao etc.'),
        'prejuizo_relatado': _s(),
    }),
    'operacoes': _lista(_obj({
        'banco': _s(),
        'instrumento': _s('CCR, CPR, CCB rural, NCR, cedula rural pignoraticia/hipotecaria, contrato etc.'),
        'finalidade': _s('custeio, investimento, comercializacao, maquinario etc.'),
        'valor': _s(),
        'vencimentos': _s(),
        'situacao': _s('em dia, vencida, a vencer, renegociada, em execucao'),
        'garantias_avalistas': _s(),
        'observacao': _s(),
    })),
    'linha_do_tempo': _lista(_obj({
        'data': _s('DD/MM/AAAA, MM/AAAA ou safra; como foi dito'),
        'evento': _s('contratacao, vencimento, parcela paga, renegociacao, perda de safra, cobranca, execucao etc.'),
    })),
    'gatilhos': _lista(_obj({
        'gatilho': _s('fato que exige acao rapida'),
        'detalhe': _s(),
        'gravidade': {'type': 'string', 'enum': ['ALTA', 'MEDIA', 'BAIXA']},
    })),
    'gaps': _lista(_s('informacao ou documento que falta para seguir')),
    'pontos_atencao': _lista(_obj({
        'ponto': _s(),
        'resposta': {'type': 'string', 'enum': ['SIM', 'NAO', 'NAO INFORMADO']},
        'evidencia': _s('trecho curto da reuniao ou justificativa'),
    })),
    'estrategia_candidata': _obj({
        'extrajudicial': _s('o que a notificacao aos bancos deve pedir'),
        'judicial': _s('acao candidata, se a via extrajudicial falhar'),
        'foro': _s('justica estadual ou federal e por que'),
        'tutela_urgencia': _s(),
        'laudos': _s('laudo de frustracao de safra (agronomo) e laudo financeiro: o que cada um precisa provar'),
        'observacao': _s(),
    }),
    'riscos': _lista(_s()),
    'pontos_fortes': _lista(_s()),
    'perguntas_onboarding': _lista(_s('pergunta para a reuniao de onboarding com o Gestor Juridico')),
    'documentos': _lista(_obj({
        'id': {'type': 'string', 'enum': [d['id'] for d in CHECKLIST_DOCUMENTOS]},
        'status': {'type': 'string', 'enum': ['JA ENTREGOU', 'VAI ENVIAR', 'NAO TEM', 'NAO FALADO']},
        'observacao': _s(),
    })),
    'honorarios': _obj({
        'entrada': _s('valor combinado de entrada/pro labore, ou vazio'),
        'parcelas': _s('forma de pagamento combinada, ou vazio'),
        'exito': _s('percentual ou regra de exito combinada, ou vazio'),
        'observacao': _s(),
    }),
    'trechos': _lista(_obj({'tema': _s(), 'trecho': _s('citacao literal curta da transcricao')})),
})

SCHEMA_QUALIFICACAO = _obj({k: _s() for k in (
    'nome', 'cpf', 'rg', 'orgao_emissor', 'data_nascimento', 'nacionalidade', 'estado_civil',
    'profissao', 'telefone', 'email', 'logradouro', 'numero', 'bairro', 'cidade', 'uf', 'cep',
    'conjuge_nome', 'conjuge_cpf', 'origem', 'indicante',
)} | {'observacoes': _s('divergencias entre as fontes, se houver')})


def _dna():
    if os.path.exists(DNA):
        with open(DNA, encoding='utf-8') as f:
            return f.read()
    return ''


def _chamar(modelo, sistema, conteudo, schema, max_tokens):
    return ia.json_por_schema(modelo, sistema, conteudo, schema, max_tokens)


def triagem(transcricao, texto_documentos='', cadastro=None):
    e = ESCRITORIO
    checklist = '\n'.join(f"- {d['id']}: {d['nome']}" for d in CHECKLIST_DOCUMENTOS)
    pontos = '\n'.join(f'- {p}' for p in PONTOS_ATENCAO)
    dna = _dna()
    sistema = f"""Voce e a analista juridica de triagem do {e['nome']} ({e['cidade']}/{e['uf']}), escritorio que defende o produtor rural contra bancos e cooperativas de credito: notificacao extrajudicial, prorrogacao e alongamento de divida rural, tutela de urgencia com suspensao de exigibilidade e proibicao de negativacao do produtor e dos avalistas, laudo de frustracao de safra e laudo financeiro.

Seu trabalho substitui o preenchimento manual do RELATORIO DE TRIAGEM que o Closer entrega ao Gestor Juridico logo apos fechar o contrato. O Gestor usa esse relatorio para conduzir a reuniao de onboarding e delegar o caso ao Advogado Extrajudicial. Prazos internos do escritorio: notificacao aos bancos em ate 15 dias do onboarding e protocolo da inicial em ate 60 dias da assinatura do contrato.

Regras:
- Use somente o que esta na transcricao, nos documentos e no cadastro. Nunca invente banco, valor, data, cedula, area ou nome. Sem dado, deixe o campo vazio e registre a lacuna em "gaps".
- Valores e datas como foram ditos; se foram aproximados na fala, diga que sao aproximados.
- "gatilhos" sao fatos que pedem acao rapida: parcela vencida ou vencendo nos proximos 30 dias, execucao ou busca e apreensao em andamento, negativacao, leilao ou consolidacao de propriedade, avalista sendo cobrado, prazo de prorrogacao administrativa correndo.
- Responda cada ponto de atencao do fluxo do escritorio, nesta ordem:
{pontos}
- Em "documentos", classifique cada item do checklist do escritorio pelo que foi dito na reuniao:
{checklist}
- A estrategia e CANDIDATA: a decisao e do Gestor Juridico. Aponte a tese que os fatos sustentam e o que ainda falta provar. Nao cite jurisprudencia que nao esteja no material de referencia abaixo.
- "trechos": ate 12 citacoes literais curtas da transcricao que sustentam os pontos principais.
- Escreva em portugues, linguagem formal, terceira pessoa, referindo-se ao cliente como "o Produtor" ou "o Cliente".
"""
    if dna:
        sistema += f'\n<referencia_do_escritorio>\nPadrao de pecas e teses do escritorio (extraido das pecas reais):\n{dna}\n</referencia_do_escritorio>\n'

    conteudo = f'<transcricao_reuniao>\n{transcricao}\n</transcricao_reuniao>'
    if texto_documentos:
        conteudo += f'\n\n<documentos_do_cliente>\n{texto_documentos}\n</documentos_do_cliente>'
    if cadastro:
        conteudo += f'\n\n<cadastro_do_closer>\n{json.dumps(cadastro, ensure_ascii=False, indent=1)}\n</cadastro_do_closer>'
    conteudo += '\n\nMonte o Relatorio de Triagem deste caso.'
    return _chamar(MODELO_TRIAGEM, sistema, conteudo, SCHEMA_TRIAGEM, 32000)


def qualificacao(transcricao, texto_documentos='', cadastro=None):
    sistema = """Voce extrai a qualificacao completa de um cliente para contrato, procuracao e declaracao.
Fontes e prioridade:
1. Documento oficial (CNH, RG, certidao): nome completo, CPF, RG e orgao emissor, data de nascimento, nacionalidade.
2. Cadastro do Closer: telefone, e-mail, endereco, estado civil, profissao, origem e indicante.
3. Transcricao da reuniao: so para o que nao estiver nas fontes acima.
Nunca invente. Campo sem fonte fica vazio. Nome sempre completo, como no documento. CPF no formato 000.000.000-00, data DD/MM/AAAA, CEP 00000-000, UF com 2 letras.
Se as fontes divergirem (ex.: nome diferente no cadastro e na CNH), use o documento oficial e explique em "observacoes"."""
    conteudo = f'<transcricao_reuniao>\n{transcricao[:60000]}\n</transcricao_reuniao>'
    if texto_documentos:
        conteudo += f'\n\n<documentos_do_cliente>\n{texto_documentos}\n</documentos_do_cliente>'
    if cadastro:
        conteudo += f'\n\n<cadastro_do_closer>\n{json.dumps(cadastro, ensure_ascii=False, indent=1)}\n</cadastro_do_closer>'
    dados = _chamar(MODELO_EXTRACAO, sistema, conteudo, SCHEMA_QUALIFICACAO, 4000)

    # o cadastro do Closer manda nos dados de contato (o modelo pode ter lido errado)
    for campo in ('telefone', 'email', 'estado_civil', 'profissao', 'origem', 'indicante'):
        if cadastro and cadastro.get(campo):
            dados[campo] = cadastro[campo]
    return validar(dados)


# ============================================================
# VALIDACOES
# ============================================================

def cpf_valido(cpf):
    n = re.sub(r'\D', '', cpf or '')
    if len(n) != 11 or n == n[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(n[j]) * ((i + 1) - j) for j in range(i))
        dig = (soma * 10) % 11 % 10
        if dig != int(n[i]):
            return False
    return True


def validar(dados):
    avisos = []
    cpf = dados.get('cpf', '')
    if cpf:
        n = re.sub(r'\D', '', cpf)
        if cpf_valido(cpf):
            dados['cpf'] = f'{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}'
        else:
            avisos.append(f'CPF {cpf} nao confere (digito verificador)')
            dados['cpf'] = f'{cpf} [CONFERIR]'
    cep = re.sub(r'\D', '', dados.get('cep', ''))
    if cep:
        dados['cep'] = f'{cep[:5]}-{cep[5:]}' if len(cep) == 8 else f"{dados['cep']} [CONFERIR]"
    for campo in ('nome', 'cpf', 'rg', 'estado_civil', 'profissao', 'logradouro', 'cidade', 'uf', 'cep'):
        if not dados.get(campo):
            avisos.append(f'sem {campo}')
    if dados.get('nome') and len(dados['nome'].split()) < 2:
        avisos.append('nome parece incompleto')
        dados['nome'] = f"{dados['nome']} [CONFERIR]"
    dados['_avisos'] = avisos
    return dados

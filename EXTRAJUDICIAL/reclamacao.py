"""
Texto pronto da reclamacao no consumidor.gov.br (fluxo: banco nao respondeu ou nao houve acordo ->
reclamacao + nova notificacao -> judicial). Montado so com dados do caso.json, sem IA, em primeira
pessoa (a reclamacao e do cliente, protocolada com a conta GOV.BR dele).
Sai em .txt (para copiar e colar no formulario) e .docx (para a pasta), em 10 EXTRAJUDICIAL.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bancos as base_bancos  # noqa: E402
import registro as reg  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from notificacao import DATA, EMAIL_RESPOSTAS, _moeda, _valor  # noqa: E402
from config.escritorio import ESCRITORIO  # noqa: E402

INSTRUCOES = [
    'Protocolar em www.consumidor.gov.br com a conta GOV.BR do CLIENTE. A senha do GOV.BR é pedida por ligação, '
    'nunca por mensagem escrita.',
    'Conferir se a instituição está cadastrada no consumidor.gov.br (cooperativas nem sempre estão). Se não estiver, '
    'levar ao Gestor Jurídico a alternativa (ex.: reclamação no Banco Central).',
    'Anexar: a notificação enviada (PDF), o comprovante do envio (e-mail enviado) e a procuração.',
    'Conferir o limite de caracteres do campo de relato no formulário antes de colar.',
    'Depois de protocolar, registrar o número: python EXTRAJUDICIAL/main.py consumidor-gov "PASTA" --banco X --protocolo NUMERO',
]


def _limpo(txt):
    """Tira as notas internas da triagem, ex.: '(conforme relato)', '(aproximado, ...)'."""
    txt = re.sub(r'\s*\([^)]*(?:relato|aproximad|conforme|n[aã]o confirmad)[^)]*\)', '', txt or '', flags=re.I)
    return re.sub(r'\s+', ' ', txt).strip(' .;,')


def _operacoes_texto(ops):
    partes = []
    for o in ops:
        desc = _limpo(o.get('finalidade')) or 'operação de crédito rural'
        v = _valor(o.get('valor'))
        if v is not None:
            aprox = 'aproximadamente ' if 'aproximad' in (o.get('valor') or '').lower() else ''
            desc += f', de {aprox}{_moeda(v)}'
        datas = DATA.findall(o.get('vencimentos') or '')
        if datas:
            desc += f", com vencimento em {', '.join(datas)}"
        if desc[:1].isupper() and desc[1:2].islower():
            desc = desc[0].lower() + desc[1:]
        partes.append(desc)
    return '; '.join(partes)


def montar_textos(caso, banco, notifs):
    t = caso.get('triagem') or {}
    ar = t.get('atividade_rural') or {}
    q = caso.get('qualificacao') or {}
    ops = reg.operacoes_do_banco(caso, banco)
    enviadas = [n for n in notifs if n.get('enviada_em')]
    primeira = enviadas[0] if enviadas else None
    ultima = notifs[-1]
    municipio = ar.get('municipio_propriedade') or '/'.join(x for x in (q.get('cidade'), q.get('uf')) if x) \
        or '[PREENCHER município]'

    relato = [f"Sou produtor rural em {municipio} e mantenho operações de crédito rural com {banco}"
              + (f": {_operacoes_texto(ops)}." if ops else '.')]
    causa = _limpo(ar.get('causa_da_perda'))
    if causa:
        safra = _limpo(ar.get('safra_afetada'))
        safra = f" na {safra[0].lower() + safra[1:]}" if safra.lower().startswith('safra') else \
            (f' na safra {safra}' if safra else '')
        relato.append(f'Em razão de {causa[0].lower() + causa[1:]}{safra}, tive dificuldade temporária para pagar '
                      'as parcelas nas datas originais.')
    pedido_txt = ('a prorrogação (alongamento) da dívida rural, nos termos do Manual de Crédito Rural (MCR 2.6.4) e '
                  'da Súmula 298 do STJ, e a cópia integral dos meus contratos'
                  if any(n['tipo'] == 'alongamento' for n in notifs) else 'a cópia integral dos meus contratos rurais')
    data_envio = reg.br(primeira['enviada_em']) if primeira else '[PREENCHER data do envio da notificação]'
    relato.append(f'Em {data_envio}, por meio dos meus advogados, enviei notificação ao banco pedindo {pedido_txt}.')
    if len(enviadas) > 1:
        relato.append(f"Reiterei o pedido em {reg.br(enviadas[-1]['enviada_em'])}.")
    r = ultima.get('resposta') or {}
    if r.get('tipo') == 'recebida':
        relato.append(f"O banco respondeu em {reg.br(r.get('data'))}, sem atender ao pedido de prorrogação.")
    elif primeira:
        dias = (reg.hoje() - reg.de_iso(primeira['enviada_em'])).days
        relato.append(f'Até hoje, passados {dias} dias, não recebi resposta fundamentada.')

    pedidos = ['Que a instituição analise formalmente o meu pedido de prorrogação e responda por escrito, com '
               'fundamento, como prevê o Manual de Crédito Rural.' if 'prorroga' in pedido_txt else
               'Que a instituição envie a cópia integral dos meus contratos rurais.',
               'Que envie cópia integral das cédulas, aditivos e renegociações e o extrato de evolução do saldo devedor.',
               'Que suspenda o débito automático das parcelas e não inclua o meu nome nem o dos meus avalistas em '
               'cadastros de inadimplentes enquanto o pedido estiver em análise.',
               f"Que trate do assunto com os meus advogados, pelo e-mail {EMAIL_RESPOSTAS} ou pelo telefone "
               f"{ESCRITORIO['telefone']}."]
    return ' '.join(relato), pedidos


def gerar(base, caso, banco):
    notifs = reg.notificacoes_do_banco(caso, banco)
    if not notifs:
        raise SystemExit(f'ERRO: não há notificação ao {banco} neste caso. Gere e envie a notificação primeiro.')
    if not any(n.get('enviada_em') for n in notifs):
        print(f'   AVISO: nenhuma notificação ao {banco} foi registrada como enviada; a data fica [PREENCHER].')
    relato, pedidos = montar_textos(caso, banco, notifs)
    entrada = base_bancos.achar(banco, (caso.get('qualificacao') or {}).get('cidade', '')) or {}
    empresa = entrada.get('razao_social') or banco
    assunto = 'Crédito rural - pedido de prorrogação da dívida sem resposta'
    nome = reg.nome_cliente(caso)
    raiz = os.path.join(reg.pasta_extra(base), f"{reg.nome_arquivo_cliente(caso)} - Reclamacao consumidor.gov - "
                                               f"{reg.arquivo_seguro(banco).upper()} - {reg.hoje().strftime('%d-%m-%Y')}")
    linhas = ['RECLAMAÇÃO NO CONSUMIDOR.GOV.BR - TEXTO PRONTO', '', 'INSTRUÇÕES (não copiar):']
    linhas += [f'- {i}' for i in INSTRUCOES]
    linhas += ['', f'CONSUMIDOR: {nome} (conta GOV.BR do cliente)', f'EMPRESA: {empresa}', f'ASSUNTO: {assunto}', '',
               'RELATO (copiar):', relato, '', 'PEDIDO (copiar):']
    linhas += [f'{i}) {p}' for i, p in enumerate(pedidos, 1)]
    linhas += ['', f'Tamanho do relato: {len(relato)} caracteres; do pedido: {len(" ".join(pedidos))} caracteres.']
    with open(raiz + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')

    doc = novo_documento()
    titulo(doc, 'Reclamação - consumidor.gov.br')
    paragrafo(doc, 'Texto pronto para o Adv. Extrajudicial protocolar com a conta GOV.BR do cliente.', tamanho=10).alignment = 1
    paragrafo(doc, nome, rotulo='Consumidor')
    paragrafo(doc, empresa if entrada.get('razao_social') else f'{banco} [CONFERIR razão social]', rotulo='Empresa')
    paragrafo(doc, assunto, rotulo='Assunto')
    secao(doc, 'Relato (copiar)')
    paragrafo(doc, relato, recuo=True)
    secao(doc, 'Pedido (copiar)')
    lista(doc, [f'{i}) {p}' for i, p in enumerate(pedidos, 1)])
    secao(doc, 'Instruções')
    lista(doc, INSTRUCOES, tamanho=10)
    doc.save(raiz + '.docx')

    n = notifs[-1]
    n['consumidor_gov'] = {'arquivo': raiz + '.txt', 'docx': raiz + '.docx', 'gerado_em': reg.iso(reg.hoje()),
                           'protocolo': None}
    reg.evento(n, 'Texto da reclamação no consumidor.gov.br gerado')
    return raiz + '.txt', relato, pedidos


def registrar_protocolo(caso, banco, protocolo):
    notifs = reg.notificacoes_do_banco(caso, banco)
    alvo = next((n for n in reversed(notifs) if n.get('consumidor_gov')), None)
    if not alvo:
        raise SystemExit(f'ERRO: gere primeiro o texto da reclamação ao {banco} (consumidor-gov sem --protocolo).')
    alvo['consumidor_gov'].update({'protocolo': protocolo, 'protocolado_em': reg.iso(reg.hoje())})
    reg.evento(alvo, f'Reclamação no consumidor.gov.br protocolada: {protocolo}')
    return alvo

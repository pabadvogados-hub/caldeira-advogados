"""
Regua de cobranca dos honorarios: Asaas -> WhatsApp (Atende Direito).

  python FINANCEIRO/main.py cobranca            relatorio do que SERIA enviado hoje (nada sai)
  python FINANCEIRO/main.py cobranca --enviar   envia (precisa ASAAS_API_TOKEN + ATENDE_DIREITO_TOKEN)
  python FINANCEIRO/main.py cobranca --exemplo  demonstracao com dados ficticios (nunca envia)

Regua (config/regras_financeiras.py): lembrete 3 dias antes e no dia do vencimento;
vencidas em D+1, D+5 e D+15. Regras:
- so cobranca A VENCER dentro da regua ou VENCIDA; cada toque sai 1 vez por cobranca
- no maximo 1 mensagem por dia por cliente (toques do mesmo dia vao juntos)
- clientes de FINANCEIRO/clientes_nao_cobrar.txt nunca recebem
- historico do que ja saiu: SAIDA/FINANCEIRO/historico_cobranca.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402
import exemplo as ex  # noqa: E402
from config.regras_financeiras import REGUA_COBRANCA  # noqa: E402

FRASE = {
    'LEMBRETE_3D': 'Passando para lembrar que está chegando o vencimento dos seus honorários:',
    'VENCE_HOJE': 'Hoje é o dia do vencimento dos seus honorários:',
    'VENCIDA_D1': 'Ainda não identificamos o pagamento dos honorários abaixo:',
    'VENCIDA_D5': 'Os honorários abaixo continuam em aberto:',
    'VENCIDA_D15': 'Os honorários abaixo seguem em aberto há 15 dias ou mais:',
}
FECHO = {
    'LEMBRETE_3D': 'Se já pagou, pode desconsiderar esta mensagem. Qualquer dúvida, é só responder aqui.',
    'VENCE_HOJE': 'Se já pagou, pode desconsiderar esta mensagem. Qualquer dúvida, é só responder aqui.',
    'VENCIDA_D1': ('Se já pagou, por favor desconsidere: a compensação do boleto pode levar alguns dias úteis. '
                   'Se tiver qualquer dificuldade, responda esta mensagem.'),
    'VENCIDA_D5': 'Se estiver com alguma dificuldade, responda aqui que a gente conversa sobre a melhor forma de regularizar.',
    'VENCIDA_D15': ('Pedimos, por gentileza, que regularize ou fale com o nosso financeiro respondendo esta '
                    'mensagem, para combinarmos a melhor solução.'),
}


def _arq_historico():
    return os.path.join(ambiente.pasta_saida('FINANCEIRO'), 'historico_cobranca.json')


def ler_historico():
    try:
        with open(_arq_historico(), encoding='utf-8') as f:
            h = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        h = {}
    h.setdefault('cobrancas', {})
    h.setdefault('clientes', {})
    return h


def salvar_historico(h):
    with open(_arq_historico(), 'w', encoding='utf-8') as f:
        json.dump(h, f, ensure_ascii=False, indent=1)


def toque_do_dia(dias):
    """Passo da regua que vale para uma cobranca com 'dias' em relacao ao vencimento (ou None)."""
    if dias is None:
        return None
    for passo in REGUA_COBRANCA:
        if passo['dia'] <= dias <= passo['ate']:
            return passo
    return None


def _peso(passo):
    return passo['dia']


def montar_mensagem(nome, itens):
    """itens: lista de (cobranca, passo). A mensagem segue o toque mais serio do dia."""
    grave = max((p for _, p in itens), key=_peso)
    linhas = [f'Olá, {c.primeiro_nome(nome)}! Aqui é do financeiro do {c.NOME_ESCRITORIO}.', '',
              FRASE.get(grave['id'], FRASE['VENCIDA_D1']), '']
    for cob, passo in sorted(itens, key=lambda x: x[0].get('dueDate') or ''):
        quando = ('venceu em' if passo['tipo'] == 'vencida' else 'com vencimento em')
        linhas.append(f"- {c.moeda(cob.get('value'))} {quando} {c.data_br(cob.get('dueDate'))}")
        linhas.append(f"  Para pagar (boleto ou Pix): {cob.get('invoiceUrl')}")
    linhas += ['', FECHO.get(grave['id'], FECHO['VENCIDA_D1'])]
    return '\n'.join(linhas)


def buscar_cobrancas(hoje):
    """PENDING e OVERDUE que podem cair na regua hoje."""
    antes = -min(p['dia'] for p in REGUA_COBRANCA)          # ex.: 3 dias antes
    depois = max(p['ate'] for p in REGUA_COBRANCA)          # ex.: ate 29 dias de atraso
    de, ate = (hoje - timedelta(days=depois)).isoformat(), (hoje + timedelta(days=max(antes, 0))).isoformat()
    print(f'Buscando no Asaas cobrancas em aberto com vencimento de {c.data_br(de)} a {c.data_br(ate)}...')
    vistas = {}
    for status in ('PENDING', 'OVERDUE'):
        for p in c.cobrancas_abertas(status, de, ate):
            vistas[p['id']] = p
    return list(vistas.values())


def planejar(cobrancas, clientes, nao_cobrar, historico, hoje):
    """Decide, por cliente, o que sai hoje. Retorna lista de dicts (um por cliente)."""
    por_cliente = defaultdict(list)
    for cob in cobrancas:
        passo = toque_do_dia(c.dias_do_vencimento(cob.get('dueDate'), hoje))
        if not passo:
            continue
        if passo['id'] in historico['cobrancas'].get(cob['id'], {}):
            continue  # este toque ja saiu antes
        por_cliente[cob.get('customer')].append((cob, passo))

    plano = []
    for cid, itens in por_cliente.items():
        cli = clientes.get(cid) or {}
        nome = cli.get('name') or '(sem nome no Asaas)'
        tel = c.ClientesAsaas.telefone(cli)
        item = {'customer': cid, 'nome': nome, 'cpf': cli.get('cpfCnpj', ''), 'telefone': tel, 'itens': itens,
                'total': sum(c.num(cob.get('value')) for cob, _ in itens),
                'toques': ', '.join(sorted({p['id'] for _, p in itens})),
                'mensagem': montar_mensagem(nome, itens)}
        if c.esta_na_lista(nao_cobrar, cid, nome, cli.get('cpfCnpj')):
            item['situacao'] = 'NAO COBRAR (lista de excecoes)'
        elif not tel:
            item['situacao'] = 'SEM TELEFONE NO ASAAS'
        elif any(not cob.get('invoiceUrl') for cob, _ in itens):
            item['situacao'] = 'SEM LINK DA FATURA'
        elif historico['clientes'].get(cid) == hoje.isoformat():
            item['situacao'] = 'JA RECEBEU MENSAGEM HOJE'
        else:
            item['situacao'] = 'A ENVIAR'
        plano.append(item)
    plano.sort(key=lambda x: (x['situacao'] != 'A ENVIAR', -x['total']))
    return plano


def enviar_plano(plano, historico, hoje):
    from atendedireito_integration import enviar_texto_por_telefone
    for item in plano:
        if item['situacao'] != 'A ENVIAR':
            continue
        ok, contato = enviar_texto_por_telefone(item['telefone'], item['mensagem'])
        if ok:
            item['situacao'] = 'ENVIADA'
            historico['clientes'][item['customer']] = hoje.isoformat()
            for cob, passo in item['itens']:
                historico['cobrancas'].setdefault(cob['id'], {})[passo['id']] = hoje.isoformat()
            salvar_historico(historico)   # grava a cada envio: se cair no meio, nao repete
        else:
            item['situacao'] = 'NAO ENVIADA (contato nao achado no Atende Direito)' if not contato \
                else 'NAO ENVIADA (erro no Atende Direito)'
        print(f"   {item['nome'][:40]:40} {item['situacao']}")
        time.sleep(2)


def relatorio(plano, hoje, modo, saida=None):
    linhas = [f'REGUA DE COBRANCA - {c.NOME_ESCRITORIO}', f"Data: {hoje.strftime('%d/%m/%Y')}   Modo: {modo}", '']
    grupos = defaultdict(list)
    for item in plano:
        grupos[item['situacao']].append(item)
    for sit, itens in grupos.items():
        linhas.append(f'### {sit}: {len(itens)} cliente(s) - {c.moeda(sum(i["total"] for i in itens))}')
    linhas.append('')
    for item in plano:
        linhas += ['-' * 72, f"{item['nome']}  |  {item['telefone'] or 'sem telefone'}  |  {item['situacao']}",
                   f"Toque(s): {item['toques']}  |  Total: {c.moeda(item['total'])}"]
        for cob, passo in item['itens']:
            linhas.append(f"   {cob['id']}  venc {c.data_br(cob.get('dueDate'))}  {c.moeda(cob.get('value'))}  "
                          f"[{passo['id']}]  {cob.get('description') or ''}")
        linhas += ['', 'Mensagem:', *['   | ' + l for l in item['mensagem'].split('\n')], '']
    if not plano:
        linhas.append('Nenhuma cobranca cai na regua hoje.')
    pasta = c.pasta_saida(saida, 'COBRANCA')
    arq = os.path.join(pasta, f"cobranca_{datetime.now().strftime('%Y-%m-%d_%H%M')}.txt")
    with open(arq, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    return arq


def executar(enviar=False, exemplo=False, saida=None, hoje=None):
    hoje = hoje or date.today()
    c.cabecalho_execucao('COBRANCA DE HONORARIOS (regua)', exemplo)
    if exemplo:
        cobrancas, clientes, nao_cobrar = ex.cobrancas_abertas(hoje), c.ClientesAsaas(ex.CLIENTES), ex.NAO_COBRAR
        historico = {'cobrancas': {}, 'clientes': {}}
    else:
        if not c.asaas_configurado():
            print('Modo seguro: sem ASAAS_API_TOKEN no config/.env. Nada consultado, nada enviado.')
            print('Para ver como funciona: python FINANCEIRO/main.py cobranca --exemplo')
            return []
        cobrancas, clientes, nao_cobrar = buscar_cobrancas(hoje), c.ClientesAsaas(), c.carregar_nao_cobrar()
        historico = ler_historico()

    plano = planejar(cobrancas, clientes, nao_cobrar, historico, hoje)
    pode_enviar = enviar and not exemplo and ambiente.tem_credencial('ATENDE_DIREITO_TOKEN')
    if enviar and exemplo:
        print('AVISO: --exemplo nunca envia nada (dados ficticios).')
    elif enviar and not pode_enviar:
        print('AVISO: sem ATENDE_DIREITO_TOKEN no config/.env: nada enviado (so relatorio).')
    modo = 'ENVIO' if pode_enviar else ('EXEMPLO' if exemplo else 'SIMULACAO (use --enviar para mandar)')

    print(f'\n{len(plano)} cliente(s) com toque da regua hoje:')
    print(f"{'CLIENTE':40} {'TOTAL':>14}  {'TOQUE(S)':24} SITUACAO")
    for item in plano:
        print(f"{item['nome'][:40]:40} {c.moeda(item['total']):>14}  {item['toques'][:24]:24} {item['situacao']}")
    if pode_enviar:
        print('\nEnviando pelo WhatsApp (Atende Direito)...')
        enviar_plano(plano, historico, hoje)
    arq = relatorio(plano, hoje, modo, saida)
    print(f'\nRelatorio com as mensagens: {arq}')
    return plano

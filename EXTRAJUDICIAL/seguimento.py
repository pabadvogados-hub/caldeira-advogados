"""
Acompanhamento da fase extrajudicial em todos os casos.

acompanhar(): prazo de resposta de cada banco, notificacao atrasada (limite = caso['prazos'] 'notificacao'),
inicial perto do limite (caso['prazos'] 'inicial'), minuta/rascunho parado, proxima acao do fluxo.
Com --enviar: SO avisa o cliente pelo WhatsApp que o banco foi notificado (1 vez por notificacao, depois
que o advogado registrou o envio). Nada vai para banco.

painel(): todos os casos na fase extrajudicial.
Agendar `python EXTRAJUDICIAL/main.py acompanhar --enviar` 1x ao dia (junto do acompanhamento da contratacao).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro as reg  # noqa: E402
from CONTRATACAO.pasta_cliente import listar_casos  # noqa: E402
from config.escritorio import ESCRITORIO  # noqa: E402

ENCERRADAS = ('ENCERRADO',)


def mensagem_cliente(caso, n):
    nome = reg.nome_cliente(caso).split(' ')[0].title()
    pedido = ('pedindo a prorrogação da sua dívida rural' if n['tipo'] == 'alongamento'
              else 'pedindo a cópia dos seus contratos')
    return (f"Olá, {nome}! Aqui é do {ESCRITORIO['nome']}. Notificamos o {n['banco']} em "
            f"{reg.br(n['enviada_em'])}, {pedido}. Assim que o banco responder, avisamos você por aqui.")


def _avisar_cliente(caso, n, enviar):
    if not n.get('enviada_em') or n.get('whatsapp_cliente_em'):
        return
    txt = mensagem_cliente(caso, n)
    if not enviar:
        print(f"     [simulado] WhatsApp ao cliente: {txt}")
        return
    if not ambiente.tem_credencial('ATENDE_DIREITO_TOKEN'):
        print('     WhatsApp: sem ATENDE_DIREITO_TOKEN no .env, nada enviado.')
        return
    telefone = (caso.get('qualificacao') or {}).get('telefone')
    if not telefone:
        print('     WhatsApp: cliente sem telefone no caso.json, nada enviado.')
        return
    from atendedireito_integration import enviar_texto_por_telefone
    ok, _ = enviar_texto_por_telefone(telefone, txt)
    if ok:
        n['whatsapp_cliente_em'] = reg.iso(reg.hoje())
        reg.evento(n, 'Cliente avisado pelo WhatsApp que o banco foi notificado')
        print('     WhatsApp: cliente avisado.')
    else:
        print('     WhatsApp: NAO enviado (contato nao achado no Atende Direito?).')


def _dica_gmail(n):
    """Se o rascunho sumiu do Gmail e o envio nao foi registrado, provavelmente foi enviado."""
    if not n.get('rascunho_id') or n.get('enviada_em'):
        return
    try:
        import gmail_integration
        existe = gmail_integration.rascunho_existe(n['rascunho_id'])
    except Exception:
        existe = None
    if existe is False:
        print(f"     {n['banco']}: o rascunho saiu do Gmail (enviado?). Confirme com registrar-envio.")


def casos_ativos():
    return [(b, c) for b, c in listar_casos()
            if c.get('etapa') not in ENCERRADAS and (c.get('triagem') or {}).get('operacoes')]


def acompanhar(enviar=False):
    casos = casos_ativos()
    if not casos:
        print('Nenhum caso com operações bancárias.')
        return
    print(f"\n=== ACOMPANHAMENTO EXTRAJUDICIAL ({reg.br(reg.hoje())}){'' if enviar else ' [simulado]'} ===")
    for base, caso in casos:
        print(f"\n{reg.nome_cliente(caso)}")
        for a in reg.alertas_caso(caso):
            print(f'   ALERTA  {a}')
        for b in reg.bancos_do_caso(caso):
            if b not in reg.bancos_ativos(caso):
                print(f'   {b[:30]:30} {"FORA DA FASE":22} -> credor não bancário: notificar só se o Gestor decidir (--banco).')
                continue
            n = reg.ultima(caso, b)
            st = reg.situacao(n) if n else 'A NOTIFICAR'
            acao = reg.proxima_acao_banco(caso, b)
            print(f'   {b[:30]:30} {st:22} -> {acao}')
            if n:
                n['proxima_acao'] = acao
                _dica_gmail(n)
        for n in reg.extrajudicial(caso)['notificacoes']:
            _avisar_cliente(caso, n, enviar)
        reg.extrajudicial(caso)['ultimo_acompanhamento'] = reg.iso(reg.hoje())
        reg.salvar(base, caso)


def painel():
    casos = casos_ativos()
    if not casos:
        print('Nenhum caso com operações bancárias.')
        return
    h = reg.hoje()
    print(f"\n{'CLIENTE':28} {'BANCOS':>6} {'ENVIADAS':>8} {'AGUARD.':>7} {'S/RESP':>6} {'PROPOST':>7} "
          f"{'NOTIFICACAO':>11} {'INICIAL':>10} {'DIAS':>4}  ALERTA")
    for base, caso in casos:
        bancos = reg.bancos_ativos(caso)
        ultimas =[reg.ultima(caso, b) for b in bancos]
        st = [reg.situacao(n) if n else 'A NOTIFICAR' for n in ultimas]
        enviadas = sum(1 for b in bancos if any(x.get('enviada_em') for x in reg.notificacoes_do_banco(caso, b)))
        prazos = reg.prazos_caso(caso)
        ini = prazos.get('inicial')
        alertas = reg.alertas_caso(caso)
        print(f"{reg.nome_cliente(caso)[:28]:28} {len(bancos):>6} {enviadas:>8} "
              f"{sum(s in ('AGUARDANDO RESPOSTA', 'PRAZO VENCIDO') for s in st):>7} "
              f"{sum(s in ('SEM RESPOSTA', 'SEM ACORDO') for s in st):>6} "
              f"{sum(s == 'PROPOSTA EM ANALISE' for s in st):>7} "
              f"{reg.br(prazos.get('notificacao')):>11} {reg.br(ini):>10} "
              f"{(ini - h).days if ini else '-':>4}  {'; '.join(alertas)[:90]}")
        for b, n, s in zip(bancos, ultimas, st):
            print(f"{'':30}{b[:28]:28} {s:22} {reg.proxima_acao_banco(caso, b)[:110]}")

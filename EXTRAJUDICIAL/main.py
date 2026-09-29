"""
FASE 3 - EXTRAJUDICIAL - Caldeira Advogados Associados

  Notificacao aos bancos (uma por banco/credor; DOCX + PDF em 10 EXTRAJUDICIAL):
    python EXTRAJUDICIAL/main.py notificar "PASTA DO CLIENTE" [--tipo alongamento|contratos] [--banco NOME]
        [--carencia 3 --parcelas 15] [--sem-ia] [--rascunho-gmail]
        --rascunho-gmail cria o RASCUNHO no Gmail (nunca envia) se nao houver [CONFERIR]/[PREENCHER]
    python EXTRAJUDICIAL/main.py rascunho "PASTA" --banco NOME       (depois de revisar o .docx)

  Base de e-mails dos bancos (config/bancos_emails.json):
    python EXTRAJUDICIAL/main.py bancos

  Registro do que o advogado fez / recebeu:
    python EXTRAJUDICIAL/main.py registrar-envio "PASTA" --banco NOME [--data DD/MM/AAAA]
    python EXTRAJUDICIAL/main.py registrar-resposta "PASTA" --banco NOME --arquivo resposta.pdf | --sem-resposta
    python EXTRAJUDICIAL/main.py proposta "PASTA" --banco NOME --arquivo proposta.pdf   (parecer ao Gestor)
    python EXTRAJUDICIAL/main.py decisao "PASTA" --banco NOME --resultado acordo|sem-acordo|judicial
    python EXTRAJUDICIAL/main.py consumidor-gov "PASTA" --banco NOME [--protocolo NUMERO]

  Acompanhamento e relatorios:
    python EXTRAJUDICIAL/main.py acompanhar [--enviar]      (agendar 1x ao dia; --enviar so avisa o cliente)
    python EXTRAJUDICIAL/main.py relatorio-gestor "PASTA"
    python EXTRAJUDICIAL/main.py painel

A IA nao envia nada ao banco: o advogado revisa o rascunho no Gmail e clica em Enviar.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bancos as base_bancos  # noqa: E402
import notificacao as nt  # noqa: E402
import proposta as prop  # noqa: E402
import reclamacao  # noqa: E402
import registro as reg  # noqa: E402
import relatorio_gestor  # noqa: E402
import seguimento  # noqa: E402
from CONTRATACAO.extrator import ler_arquivo  # noqa: E402


def _data(txt):
    if not txt:
        return reg.hoje()
    d = reg.de_br(txt)
    if not d:
        raise SystemExit(f'ERRO: data invalida "{txt}" (use DD/MM/AAAA).')
    if d > reg.hoje():
        raise SystemExit(f'ERRO: a data {txt} esta no futuro.')
    return d


def _proxima(caso, banco):
    print(f'   Próxima ação: {reg.proxima_acao_banco(caso, banco)}')


def notificar(pasta, tipo, banco, rascunho_gmail, usar_ia, carencia, parcelas):
    base, caso = reg.abrir_caso(pasta)
    print(f'\n=== NOTIFICAÇÃO EXTRAJUDICIAL: {reg.nome_cliente(caso)} ===')
    if not caso.get('assinado_em'):
        print('   AVISO: contrato/procuração ainda não constam como assinados; a notificação cita a procuração em anexo.')
    if banco:
        alvos = [reg.resolver_banco(caso, banco)]
    else:
        alvos = []
        for b in reg.bancos_do_caso(caso):
            if nt.credor_nao_bancario(caso, b):
                print(f'   {b}: credor não bancário, pulado (só com --banco, se o Gestor decidir notificar).')
            else:
                alvos.append(b)
    if not alvos:
        raise SystemExit('ERRO: nenhum banco para notificar neste caso (triagem sem operações).')
    for b in alvos:
        n = nt.gerar(base, caso, b, tipo, usar_ia, carencia, parcelas)
        reg.salvar(base, caso)
        print(f"   OK  {os.path.basename(n['arquivo'])}{'  (+ PDF)' if n.get('pdf') else '  (PDF NÃO gerado)'}")
        print(f"       e-mail do banco: {n.get('email_destino') or 'SEM e-mail em config/bancos_emails.json'}")
        if n['pendencias']:
            print(f"       {len(n['pendencias'])} marca(s) a resolver: {', '.join(n['pendencias'][:6])}"
                  + (' ...' if len(n['pendencias']) > 6 else ''))
        for a in (n.get('avisos_ia') or [])[:10]:
            print(f'       revisar: {a}')
        if rascunho_gmail:
            nt.criar_rascunho(base, caso, n)
        n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
        reg.salvar(base, caso)
        _proxima(caso, b)
    if not rascunho_gmail:
        print('\nNada saiu do escritório. Revise os .docx em 10 EXTRAJUDICIAL e depois:')
        print(f'   python EXTRAJUDICIAL/main.py rascunho "{base}" --banco NOME')


def rascunho(pasta, banco):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    n = reg.ultima(caso, b)
    if not n:
        raise SystemExit(f'ERRO: não há notificação ao {b}. Rode "notificar" primeiro.')
    nt.criar_rascunho(base, caso, n)
    n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
    reg.salvar(base, caso)
    _proxima(caso, b)


def registrar_envio(pasta, banco, data_txt):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    n = next((x for x in reversed(reg.notificacoes_do_banco(caso, b)) if not x.get('enviada_em')), None)
    if not n:
        ultima = reg.ultima(caso, b)
        if ultima:
            raise SystemExit(f"ERRO: a última notificação ao {b} já consta enviada em {reg.br(ultima['enviada_em'])}.")
        raise SystemExit(f'ERRO: não há notificação ao {b}. Rode "notificar" primeiro.')
    pend = reg.pendencias_docx(n['arquivo'])
    if pend:
        print(f'   ATENÇÃO: o .docx ainda tem {len(pend)} marca(s) ({", ".join(pend[:4])}). '
              'Confirme que a versão enviada ao banco foi a corrigida.')
    reg.registrar_envio(n, _data(data_txt))
    n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
    reg.salvar(base, caso)
    print(f"   {b}: envio registrado em {reg.br(n.get('enviada_em'))}; prazo de resposta até {reg.br(n.get('prazo_resposta'))} "
          f'({reg.PRAZO_RESPOSTA_BANCO_DIAS} dias corridos).')
    print('   O aviso ao cliente sai no próximo "acompanhar --enviar" (1 vez por notificação).')
    _proxima(caso, b)


def registrar_resposta(pasta, banco, arquivo, sem_resposta, data_txt):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    n = next((x for x in reversed(reg.notificacoes_do_banco(caso, b)) if x.get('enviada_em')), None)
    if not n:
        raise SystemExit(f'ERRO: nenhuma notificação ao {b} consta como enviada. Rode registrar-envio antes.')
    d = _data(data_txt)
    if sem_resposta:
        prazo = reg.de_iso(n.get('prazo_resposta'))
        if prazo and d <= prazo:
            print(f'   AVISO: o prazo de resposta vai até {reg.br(prazo)}; registrando a ausência mesmo assim.')
        n['resposta'] = {'tipo': 'sem_resposta', 'data': reg.iso(d), 'arquivo': None, 'trecho': '',
                         'registrada_em': reg.iso(reg.hoje())}
        reg.evento(n, f'Sem resposta do banco até {reg.br(d)}')
    else:
        if not os.path.exists(arquivo):
            raise SystemExit(f'ERRO: arquivo não encontrado: {arquivo}')
        destino = os.path.join(reg.pasta_extra(base), f"{reg.nome_arquivo_cliente(caso)} - Resposta "
                                                      f"{reg.arquivo_seguro(b).upper()} - {d.strftime('%d-%m-%Y')}"
                                                      f"{os.path.splitext(arquivo)[1].lower()}")
        if os.path.abspath(arquivo) != os.path.abspath(destino):
            shutil.copy2(arquivo, destino)
        texto = ler_arquivo(destino)
        n['resposta'] = {'tipo': 'recebida', 'data': reg.iso(d), 'arquivo': destino, 'trecho': texto[:400],
                         'registrada_em': reg.iso(reg.hoje())}
        reg.evento(n, f'Resposta do banco recebida em {reg.br(d)}')
        print(f'   Resposta guardada: {os.path.basename(destino)}')
    n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
    reg.salvar(base, caso)
    print(f'   {b}: {reg.situacao(n)}')
    _proxima(caso, b)


def proposta(pasta, banco, arquivo, usar_ia):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    parecer, a = prop.analisar(base, caso, b, arquivo, usar_ia)
    n = reg.ultima(caso, b)
    n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
    reg.salvar(base, caso)
    print(f'   OK  {os.path.basename(parecer)}')
    print(f"   Resumo: {(a.get('resumo_da_proposta') or '')[:400]}")
    print('   A decisão é do Gestor Jurídico. Nada foi respondido ao banco.')
    _proxima(caso, b)


def decisao(pasta, banco, resultado, obs):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    n = reg.ultima(caso, b)
    if not n:
        raise SystemExit(f'ERRO: não há notificação ao {b}.')
    n['decisao'] = {'resultado': resultado, 'data': reg.iso(reg.hoje()), 'observacao': obs or ''}
    reg.evento(n, f'Decisão do Gestor registrada: {resultado}{" - " + obs if obs else ""}')
    n['proxima_acao'] = reg.proxima_acao_banco(caso, b)
    reg.salvar(base, caso)
    print(f'   {b}: {reg.situacao(n)}')
    _proxima(caso, b)


def consumidor_gov(pasta, banco, protocolo):
    base, caso = reg.abrir_caso(pasta)
    b = reg.resolver_banco(caso, banco)
    if protocolo:
        reclamacao.registrar_protocolo(caso, b, protocolo)
        reg.salvar(base, caso)
        print(f'   {b}: protocolo {protocolo} registrado.')
    else:
        arq, relato, pedidos = reclamacao.gerar(base, caso, b)
        reg.salvar(base, caso)
        print(f'   OK  {os.path.basename(arq)} (+ .docx)')
        print(f'\nRELATO:\n{relato}\n\nPEDIDO:')
        for i, p in enumerate(pedidos, 1):
            print(f'{i}) {p}')
    _proxima(caso, b)


def relatorio(pasta):
    base, caso = reg.abrir_caso(pasta)
    caminho, alertas = relatorio_gestor.gerar(base, caso)
    reg.salvar(base, caso)
    print(f'   OK  {os.path.basename(caminho)}')
    for a in alertas:
        print(f'   ALERTA  {a}')


def main():
    ap = argparse.ArgumentParser(description='Fase extrajudicial - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('notificar')
    p.add_argument('pasta')
    p.add_argument('--tipo', choices=['alongamento', 'contratos'], default='alongamento')
    p.add_argument('--banco')
    p.add_argument('--rascunho-gmail', action='store_true')
    p.add_argument('--sem-ia', action='store_true')
    p.add_argument('--carencia', type=int, help='anos de carencia pedidos (senao: laudo ou 3 com [CONFERIR])')
    p.add_argument('--parcelas', type=int, help='parcelas anuais pedidas (senao: laudo ou 15 com [CONFERIR])')
    r = sub.add_parser('rascunho')
    r.add_argument('pasta')
    r.add_argument('--banco', required=True)
    sub.add_parser('bancos')
    e = sub.add_parser('registrar-envio')
    e.add_argument('pasta')
    e.add_argument('--banco', required=True)
    e.add_argument('--data')
    rr = sub.add_parser('registrar-resposta')
    rr.add_argument('pasta')
    rr.add_argument('--banco', required=True)
    g = rr.add_mutually_exclusive_group(required=True)
    g.add_argument('--arquivo')
    g.add_argument('--sem-resposta', action='store_true')
    rr.add_argument('--data')
    a = sub.add_parser('acompanhar')
    a.add_argument('--enviar', action='store_true')
    c = sub.add_parser('consumidor-gov')
    c.add_argument('pasta')
    c.add_argument('--banco', required=True)
    c.add_argument('--protocolo')
    pr = sub.add_parser('proposta')
    pr.add_argument('pasta')
    pr.add_argument('--banco', required=True)
    pr.add_argument('--arquivo', required=True)
    pr.add_argument('--sem-ia', action='store_true')
    d = sub.add_parser('decisao')
    d.add_argument('pasta')
    d.add_argument('--banco', required=True)
    d.add_argument('--resultado', required=True, choices=['acordo', 'sem-acordo', 'judicial'])
    d.add_argument('--obs')
    rg = sub.add_parser('relatorio-gestor')
    rg.add_argument('pasta')
    sub.add_parser('painel')
    args = ap.parse_args()

    if args.cmd == 'notificar':
        notificar(args.pasta, args.tipo, args.banco, args.rascunho_gmail, not args.sem_ia, args.carencia, args.parcelas)
    elif args.cmd == 'rascunho':
        rascunho(args.pasta, args.banco)
    elif args.cmd == 'bancos':
        base_bancos.listar()
    elif args.cmd == 'registrar-envio':
        registrar_envio(args.pasta, args.banco, args.data)
    elif args.cmd == 'registrar-resposta':
        registrar_resposta(args.pasta, args.banco, args.arquivo, args.sem_resposta, args.data)
    elif args.cmd == 'acompanhar':
        seguimento.acompanhar(args.enviar)
    elif args.cmd == 'consumidor-gov':
        consumidor_gov(args.pasta, args.banco, args.protocolo)
    elif args.cmd == 'proposta':
        proposta(args.pasta, args.banco, args.arquivo, not args.sem_ia)
    elif args.cmd == 'decisao':
        decisao(args.pasta, args.banco, args.resultado, args.obs)
    elif args.cmd == 'relatorio-gestor':
        relatorio(args.pasta)
    elif args.cmd == 'painel':
        seguimento.painel()


if __name__ == '__main__':
    main()

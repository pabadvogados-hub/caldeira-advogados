"""
COMERCIAL (fluxo inicial SDR -> Closer) + CAPTACAO - Caldeira Advogados Associados

  SDR de IA: qualifica o lead a partir da conversa exportada do WhatsApp/Atende Direito
    python COMERCIAL/main.py sdr "conversa.txt"
    python COMERCIAL/main.py sdr --exemplo              (conversa ficticia)
    ... --sem-ia                                        (pre-analise por palavras-chave, sem chamar a IA)

  Radar de credito rural por municipio (dados publicos do Banco Central):
    python COMERCIAL/main.py radar                      (RO e MT, ano anterior)
    python COMERCIAL/main.py radar --uf RO --ano 2025

  Calculadora de juros (pagina de captacao):
    python COMERCIAL/main.py calculadora [--whatsapp 5569999999999]

  Relatorio do Meta Ads (so leitura; nunca altera campanha):
    python COMERCIAL/main.py meta-ads --dias 1|7|30
    python COMERCIAL/main.py meta-ads --exemplo

  Auditoria do atendimento (Atende Direito):
    python COMERCIAL/main.py auditoria-atendimento --dias 7
    python COMERCIAL/main.py auditoria-atendimento --csv EXPORT.csv
    python COMERCIAL/main.py auditoria-atendimento --exemplo

POP: docs/POP_COMERCIAL.md | Roteiro da reuniao de fechamento: docs/ROTEIRO_CLOSER.md
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
EXEMPLOS = os.path.join(AQUI, 'exemplos')


def main():
    ap = argparse.ArgumentParser(description='Comercial e captacao - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('sdr', help='qualifica o lead a partir da conversa')
    s.add_argument('conversa', nargs='?')
    s.add_argument('--exemplo', action='store_true')
    s.add_argument('--sem-ia', action='store_true', help='nao chama a IA (pre-analise por palavras-chave)')
    s.add_argument('--saida')

    r = sub.add_parser('radar', help='radar de credito rural por municipio')
    r.add_argument('--uf', default='', help='ex.: RO,MT (padrao: UFs de atendimento)')
    r.add_argument('--ano', type=int)
    r.add_argument('--mt-todo', action='store_true', help='sugerir MT inteiro, nao so o Norte Mato-grossense')
    r.add_argument('--saida')

    c = sub.add_parser('calculadora', help='gera COMERCIAL/calculadora/index.html')
    c.add_argument('--whatsapp', help='numero do botao, so digitos com DDI (ex.: 5569999999999)')

    m = sub.add_parser('meta-ads', help='relatorio das campanhas do Meta (so leitura)')
    m.add_argument('--dias', type=int, default=7, choices=[1, 7, 30])
    m.add_argument('--exemplo', action='store_true')
    m.add_argument('--saida')

    a = sub.add_parser('auditoria-atendimento', help='auditoria do atendimento no Atende Direito')
    a.add_argument('--dias', type=int, help='API: padrao 7. CSV/exemplo: so filtra se informado')
    a.add_argument('--csv', help='export de conversas em CSV (quando a API nao traz o historico)')
    a.add_argument('--exemplo', action='store_true')
    a.add_argument('--saida')

    args = ap.parse_args()

    if args.cmd == 'sdr':
        import sdr
        if args.exemplo:
            caminho = os.path.join(EXEMPLOS, 'CONVERSA_LEAD_EXEMPLO.txt')
        elif args.conversa:
            caminho = args.conversa
        else:
            raise SystemExit('Informe o arquivo da conversa ou use --exemplo.')
        sdr.qualificar_arquivo(caminho, sem_ia=args.sem_ia, saida=args.saida)
    elif args.cmd == 'radar':
        import radar
        ufs = [u for u in args.uf.replace(' ', ',').split(',') if u] or None
        radar.gerar(ufs, args.ano, args.saida, args.mt_todo)
    elif args.cmd == 'calculadora':
        import calculadora
        calculadora.gerar(args.whatsapp)
    elif args.cmd == 'meta-ads':
        import meta_ads
        meta_ads.relatorio(args.dias, args.exemplo, args.saida)
    elif args.cmd == 'auditoria-atendimento':
        import auditoria
        auditoria.relatorio(args.dias, args.csv, args.exemplo, args.saida)


if __name__ == '__main__':
    main()

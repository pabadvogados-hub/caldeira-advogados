"""
FINANCEIRO - Caldeira Advogados Associados

  Regua de cobranca dos honorarios (Asaas -> WhatsApp):
    python FINANCEIRO/main.py cobranca                 relatorio do que sairia hoje (nada e enviado)
    python FINANCEIRO/main.py cobranca --enviar        envia (agendado de segunda a sexta, 10h)

  Inadimplencia (vencidas por cliente, XLSX):
    python FINANCEIRO/main.py inadimplencia

  Fechamento mensal (Asaas x ADVBOX, conciliacao, analise, XLSX + resumo DOCX):
    python FINANCEIRO/main.py fechamento 09/2026
    python FINANCEIRO/main.py fechamento               (mes anterior; agendado no dia 5)

  Contratos novos sem cobranca no Asaas:
    python FINANCEIRO/main.py honorarios-novos

  Em todos: --exemplo usa dados ficticios (nada e consultado nem enviado);
            --saida PASTA grava os relatorios em outra pasta (padrao: SAIDA/FINANCEIRO/).

Regras do escritorio (regua, comissoes, exclusoes): config/regras_financeiras.py
Quem nao recebe cobranca automatica: FINANCEIRO/clientes_nao_cobrar.txt
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # acentos no terminal do Windows e nos logs do agendador
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass


def main():
    ap = argparse.ArgumentParser(description='Financeiro - Caldeira Advogados Associados')
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument('--exemplo', action='store_true', help='dados ficticios, nada e consultado nem enviado')
    comum.add_argument('--saida', help='pasta dos relatorios (padrao: SAIDA/FINANCEIRO)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    cb = sub.add_parser('cobranca', parents=[comum], help='regua de cobranca dos honorarios')
    cb.add_argument('--enviar', action='store_true', help='envia pelo WhatsApp (Atende Direito)')
    sub.add_parser('inadimplencia', parents=[comum], help='vencidas por cliente (XLSX)')
    fe = sub.add_parser('fechamento', parents=[comum], help='fechamento mensal')
    fe.add_argument('competencia', nargs='?', help='MM/AAAA (padrao: mes anterior)')
    sub.add_parser('honorarios-novos', parents=[comum], help='contratos sem cobranca no Asaas')
    args = ap.parse_args()

    if args.cmd == 'cobranca':
        import cobranca
        cobranca.executar(enviar=args.enviar, exemplo=args.exemplo, saida=args.saida)
    elif args.cmd == 'inadimplencia':
        import inadimplencia
        inadimplencia.executar(exemplo=args.exemplo, saida=args.saida)
    elif args.cmd == 'fechamento':
        import fechamento
        fechamento.executar(args.competencia, exemplo=args.exemplo, saida=args.saida)
    elif args.cmd == 'honorarios-novos':
        import honorarios_novos
        honorarios_novos.executar(exemplo=args.exemplo, saida=args.saida)


if __name__ == '__main__':
    main()

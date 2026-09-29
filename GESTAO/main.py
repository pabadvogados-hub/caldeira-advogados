"""
GESTAO - controle de pauta do escritorio (Caldeira Advogados Associados)

  Segunda (reuniao de pauta: o que cada um faz na semana):
    python GESTAO/main.py pauta [--exemplo]

  Sexta (auditoria: fez? protocolou? prazos cumpridos? indicadores):
    python GESTAO/main.py auditoria [--exemplo]

  Varredura historica do ADVBOX (onde a equipe trava):
    python GESTAO/main.py gargalos --dias 90 [--exemplo]

Tudo so leitura (ADVBOX, pastas dos clientes, varreduras do DJEN). Sai DOCX no timbrado
+ texto curto para o WhatsApp da equipe em SAIDA/gestao/. Nada e enviado.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coleta  # noqa: E402  (carrega ambiente e o caminho da CONTROLADORIA)


def main():
    coleta.comum.console_utf8()
    ap = argparse.ArgumentParser(description='Gestão: pauta, auditoria e gargalos - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pauta', help='pauta de segunda')
    p.add_argument('--exemplo', action='store_true')
    a = sub.add_parser('auditoria', help='auditoria de sexta')
    a.add_argument('--exemplo', action='store_true')
    g = sub.add_parser('gargalos', help='varredura historica de tarefas do ADVBOX')
    g.add_argument('--dias', type=int, default=90)
    g.add_argument('--exemplo', action='store_true')
    args = ap.parse_args()

    if args.cmd == 'pauta':
        import pauta
        pauta.gerar(args.exemplo)
    elif args.cmd == 'auditoria':
        import auditoria
        auditoria.gerar(args.exemplo)
    elif args.cmd == 'gargalos':
        import gargalos
        gargalos.gerar(args.dias, args.exemplo)


if __name__ == '__main__':
    main()

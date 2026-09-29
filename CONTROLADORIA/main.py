"""
CONTROLADORIA - fases 5 (Acompanhamento processual) e 6 (Finalizacao)
Caldeira Advogados Associados

  Varredura diaria das publicacoes (DJEN por OAB -> ADVBOX -> classificacao -> prazos):
    python CONTROLADORIA/main.py varredura --dias 7                  (so relatorio, nada sai)
    python CONTROLADORIA/main.py varredura --dias 7 --criar-tarefas  (tarefa no ADVBOX, confirmando item a item)
    python CONTROLADORIA/main.py varredura --ia                      (IA sugere o que ficou em revisao manual)
    python CONTROLADORIA/main.py varredura --exemplo                 (dados ficticios)

  Avisos ao produtor sobre decisoes relevantes (liminar, audiencia, pericia, sentenca):
    python CONTROLADORIA/main.py avisos-cliente [--exemplo]          (gera mensagens + CSV de revisao)
    python CONTROLADORIA/main.py avisos-cliente --enviar             (envia so o que foi revisado)

  Relatorio periodico de andamento a cada cliente (15 ou 30 dias):
    python CONTROLADORIA/main.py relatorio-clientes --dias 30 [--exemplo]
    python CONTROLADORIA/main.py relatorio-clientes --enviar

  Planilha de atualizacao individual dos clientes (reuniao operacional):
    python CONTROLADORIA/main.py planilha [--exemplo]

  Processos parados (possivel falta de custas/juntada) para o Coordenador destravar:
    python CONTROLADORIA/main.py parados --dias 30 [--exemplo]

  Fase 6 - encerramento do caso:
    python CONTROLADORIA/main.py finalizar "PASTA DO CLIENTE" [--motivo "..."] [--atualizar-advbox]

Nada sai do escritorio sem flag explicita (--enviar, --criar-tarefas, --atualizar-advbox) E credencial.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum  # noqa: E402
from configuracao import DIAS_PARADO, RELATORIO_CLIENTE_DIAS  # noqa: E402


def main():
    comum.console_utf8()
    ap = argparse.ArgumentParser(description='Controladoria (fases 5 e 6) - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)

    v = sub.add_parser('varredura', help='DJEN -> ADVBOX -> classificacao -> prazos -> relatorio')
    v.add_argument('--dias', type=int, default=7)
    v.add_argument('--criar-tarefas', action='store_true', help='cria tarefas no ADVBOX (confirma item a item)')
    v.add_argument('--ia', action='store_true', help='IA sugere classificacao para o que ficou em revisao manual')
    v.add_argument('--ia-max', type=int, default=3, help='maximo de chamadas de IA (padrao 3)')
    v.add_argument('--exemplo', action='store_true')

    a = sub.add_parser('avisos-cliente', help='mensagens ao produtor sobre decisoes relevantes')
    a.add_argument('--enviar', action='store_true')
    a.add_argument('--so', help='com --enviar: so este cliente')
    a.add_argument('--exemplo', action='store_true')

    r = sub.add_parser('relatorio-clientes', help='relatorio periodico de andamento a cada cliente')
    r.add_argument('--dias', type=int, default=RELATORIO_CLIENTE_DIAS, choices=(15, 30))
    r.add_argument('--enviar', action='store_true')
    r.add_argument('--so', help='com --enviar: so este cliente')
    r.add_argument('--exemplo', action='store_true')

    p = sub.add_parser('planilha', help='planilha .xlsx de atualizacao individual de clientes')
    p.add_argument('--exemplo', action='store_true')

    pa = sub.add_parser('parados', help='processos sem movimentacao ha N dias')
    pa.add_argument('--dias', type=int, default=DIAS_PARADO)
    pa.add_argument('--exemplo', action='store_true')

    f = sub.add_parser('finalizar', help='fase 6: checklist de encerramento e arquivamento da pasta')
    f.add_argument('pasta')
    f.add_argument('--motivo', default='')
    f.add_argument('--atualizar-advbox', action='store_true', help='grava a data de encerramento no ADVBOX')
    f.add_argument('--sim', action='store_true', help='confirma sem perguntar (uso consciente)')

    args = ap.parse_args()
    if args.cmd == 'varredura':
        import varredura
        varredura.executar(args.dias, args.criar_tarefas, args.exemplo, args.ia, args.ia_max)
    elif args.cmd == 'avisos-cliente':
        import avisos
        avisos.enviar(args.so) if args.enviar else avisos.gerar(args.exemplo)
    elif args.cmd == 'relatorio-clientes':
        import relatorio_clientes
        relatorio_clientes.enviar(args.so) if args.enviar else relatorio_clientes.gerar(args.dias, args.exemplo)
    elif args.cmd == 'planilha':
        import planilha
        planilha.gerar(args.exemplo)
    elif args.cmd == 'parados':
        import parados
        parados.gerar(args.dias, args.exemplo)
    elif args.cmd == 'finalizar':
        import finalizar
        finalizar.executar(args.pasta, args.motivo, args.atualizar_advbox, args.sim)


if __name__ == '__main__':
    main()

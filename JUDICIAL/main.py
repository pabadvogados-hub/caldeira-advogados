"""
FASE 4 - JUDICIAL (PECAS) - Caldeira Advogados Associados

  Checklist pre-protocolo (sem IA): BLOQUEIA / ATENCAO / OK + pedido pronto ao Estagiario
    python JUDICIAL/main.py checklist "PASTA DO CLIENTE" [--banco NOME]

  Minuta da Acao Mandamental de Prorrogacao Compulsoria (uma por banco), no timbrado:
    python JUDICIAL/main.py inicial "PASTA DO CLIENTE" [--banco NOME] [--revisional] [--federal]

  Demais pecas (motor generico, cada uma com seu esqueleto em BASE_CONHECIMENTO/ESQUELETOS):
    python JUDICIAL/main.py agravo        "PASTA" --decisao DECISAO.pdf        (liminar negada -> TJRO/TRF1)
    python JUDICIAL/main.py replica       "PASTA" --contestacao CONTESTACAO.pdf
    python JUDICIAL/main.py embargos      "PASTA" --execucao EXECUCAO.pdf
    python JUDICIAL/main.py contrarrazoes "PASTA" --recurso APELACAO.pdf
    python JUDICIAL/main.py manifestacao  "PASTA" --instrucao "o que a peticao deve dizer" [--documento X.pdf]
    (todas aceitam --banco NOME e --instrucao "orientacao extra do advogado")

  Refazer o .docx/.pdf a partir do texto salvo (sem nova chamada de IA; ex.: depois de corrigir o texto):
    python JUDICIAL/main.py docx "20 JUDICIAL/_texto_ia/ARQUIVO.md"

  Pecas geradas no caso:
    python JUDICIAL/main.py pecas "PASTA DO CLIENTE"

  --simular (inicial e demais): monta o prompt e salva em 20 JUDICIAL/_texto_ia, sem chamar a IA.
  --resposta "..._texto_ia/... - resposta bruta da IA.txt": refaz limpeza, conferencia com o DNA, cabecalho e fecho
    a partir da resposta ja salva, sem nova chamada de IA.

Saidas em "PASTA DO CLIENTE/20 JUDICIAL". A IA nao protocola e nao envia nada: toda peca sai com
"PRONTA PARA REVISAO DO(A) ADVOGADO(A) RESPONSAVEL" e as pendencias em vermelho.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caso_judicial as cj  # noqa: E402
import checklist  # noqa: E402
import pecas  # noqa: E402

DOCUMENTO_POR_TIPO = {'agravo': 'decisao', 'replica': 'contestacao', 'embargos': 'execucao',
                      'contrarrazoes': 'recurso', 'manifestacao': 'documento'}


def listar_pecas(pasta):
    base, caso = cj.abrir(pasta)
    print(f"\n{cj.nome_cliente(caso)} | etapa: {caso.get('etapa', '-')}")
    ck = caso.get('judicial_checklist')
    if ck:
        print(f"Checklist {ck['gerado_em'][:16]}: {ck['bloqueia']} bloqueio(s), {ck['atencao']} atenção, {ck['ok']} ok")
    for p in caso.get('judicial') or []:
        print(f"  {p['gerada_em'][:16]}  {p['tipo']:13} {p.get('banco') or '-':24} "
              f"{p.get('pendencias', '?')} pendência(s)  {os.path.basename(p['arquivo'])}")
    if not caso.get('judicial'):
        print('  Nenhuma peça gerada ainda.')


def main():
    ap = argparse.ArgumentParser(description='Fase judicial (peças) - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('checklist', help='checklist pré-protocolo')
    c.add_argument('pasta')
    c.add_argument('--banco')

    i = sub.add_parser('inicial', help='minuta da ação mandamental')
    i.add_argument('pasta')
    i.add_argument('--banco')
    i.add_argument('--revisional', action='store_true', help='c/c revisão contratual')
    i.add_argument('--federal', action='store_true', help='força Justiça Federal (automático se o réu é a Caixa)')
    i.add_argument('--instrucao', help='orientação extra do advogado para esta peça')
    i.add_argument('--simular', action='store_true')
    i.add_argument('--resposta', help='reprocessa uma resposta bruta da IA já salva (sem nova chamada)')

    for tipo, arg in DOCUMENTO_POR_TIPO.items():
        p = sub.add_parser(tipo, help=pecas.TIPOS[tipo]['nome'])
        p.add_argument('pasta')
        p.add_argument(f'--{arg}', required=(tipo != 'manifestacao'))
        p.add_argument('--banco')
        p.add_argument('--instrucao', required=(tipo == 'manifestacao'))
        p.add_argument('--federal', action='store_true')
        p.add_argument('--simular', action='store_true')
        p.add_argument('--resposta', help='reprocessa uma resposta bruta da IA já salva (sem nova chamada)')

    d = sub.add_parser('docx', help='refaz o .docx/.pdf a partir do texto marcado salvo')
    d.add_argument('arquivo_md')
    d.add_argument('--saida')

    l = sub.add_parser('pecas', help='peças geradas no caso')
    l.add_argument('pasta')

    args = ap.parse_args()
    if args.cmd == 'checklist':
        checklist.gerar(args.pasta, args.banco)
    elif args.cmd == 'inicial':
        pecas.gerar('inicial', args.pasta, banco=args.banco, instrucao=args.instrucao, revisional=args.revisional,
                    federal=args.federal, simular=args.simular, resposta=args.resposta)
    elif args.cmd in DOCUMENTO_POR_TIPO:
        pecas.gerar(args.cmd, args.pasta, banco=args.banco, documento=getattr(args, DOCUMENTO_POR_TIPO[args.cmd]),
                    instrucao=args.instrucao, federal=args.federal, simular=args.simular, resposta=args.resposta)
    elif args.cmd == 'docx':
        saida, pdf, pend = pecas.renderizar(args.arquivo_md, args.saida)
        print(f'OK  {saida}\nPDF {pdf or "(não gerado)"}\nPendências em vermelho: {len(pend)}')
    elif args.cmd == 'pecas':
        listar_pecas(args.pasta)


if __name__ == '__main__':
    main()

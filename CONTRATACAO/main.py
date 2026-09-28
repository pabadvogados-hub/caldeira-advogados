"""
FASE DE CONTRATACAO - Caldeira Advogados Associados

  Novo cliente (reuniao de fechamento do Closer):
    python CONTRATACAO/main.py novo "TRANSCRICAO.pdf" "CNH.pdf" "CEDULA_BB.pdf" --cadastro CADASTRO.txt
        gera pasta + Relatorio de Triagem + contrato/procuracao/declaracao + resumo do Financeiro.
        NADA sai do escritorio. Revise os documentos e depois rode "enviar".
    ... --enviar                  gera e ja envia (se nao houver pendencia nos documentos)
    ... --enviar --criar-tarefas  tambem abre as tarefas por cargo no ADVBOX

  Enviar depois de revisar (os .docx podem ser editados no Word antes):
    python CONTRATACAO/main.py enviar "CAMINHO DA PASTA DO CLIENTE" [--criar-tarefas]

  Acompanhar assinaturas e cobrar documentos (agendar 3x ao dia):
    python CONTRATACAO/main.py acompanhar            (simula)
    python CONTRATACAO/main.py acompanhar --enviar

  Situacao de todos os casos:
    python CONTRATACAO/main.py painel

  Demonstracao com caso ficticio (nao envia nada):
    python CONTRATACAO/main.py exemplo
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import date, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, RAIZ)

import acompanhamento  # noqa: E402
import analise_ia  # noqa: E402
import documentos  # noqa: E402
import envio  # noqa: E402
import mensagens  # noqa: E402
import pasta_cliente  # noqa: E402
import relatorio_triagem  # noqa: E402
from docx_caldeira import docx_para_pdf  # noqa: E402
from extrator import ler_arquivo, ler_cadastro  # noqa: E402


def _ok(txt):
    print(f'   OK  {txt}')


def resumo_financeiro(base, caso):
    q, h, c = caso['qualificacao'], caso['triagem'].get('honorarios') or {}, caso.get('cadastro', {})
    linhas = [
        'RESUMO PARA O FINANCEIRO (organizar os pagamentos no Asaas)',
        '',
        f"Cliente: {q.get('nome')}",
        f"CPF: {q.get('cpf')}",
        f"Telefone: {q.get('telefone')}   E-mail: {q.get('email')}",
        f"Contrato nº {caso['campos'].get('NUMERO_CONTRATO')} de {caso['data_contrato_br']}",
        '',
        'Honorarios combinados (conferir com o Closer):',
        f"  Entrada: {c.get('honorarios_entrada') or h.get('entrada') or '-'}",
        f"  Forma de pagamento: {c.get('honorarios_pagamento') or h.get('parcelas') or '-'}",
        f"  Exito: {c.get('honorarios_exito') or h.get('exito') or '-'}",
        f"  Observacao: {h.get('observacao') or '-'}",
    ]
    if caso.get('asaas'):
        linhas += ['', 'Cobrancas criadas no Asaas:'] + [f"  {l['descricao']}: {l['link']}" for l in caso['asaas']]
    caminho = os.path.join(base, pasta_cliente.CONTRATACAO, 'RESUMO PARA O FINANCEIRO.txt')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    return caminho


def novo(transcricao, docs, cadastro_path, enviar=False, criar_tarefas=False):
    print('\n=== FASE DE CONTRATACAO: NOVO CLIENTE ===')
    cadastro = ler_cadastro(cadastro_path)

    print('1. Lendo a reuniao e os documentos...')
    texto_reuniao = ler_arquivo(transcricao)
    if len(texto_reuniao.strip()) < 200:
        raise SystemExit(f'ERRO: nao consegui ler a transcricao ({transcricao}).')
    textos_docs = {}
    for d in docs:
        textos_docs[d] = ler_arquivo(d)
        print(f'   {os.path.basename(d)}: {len(textos_docs[d])} caracteres')
    texto_docs = ''.join(f'\n--- DOCUMENTO: {os.path.basename(d)} ---\n{t[:40000]}' for d, t in textos_docs.items())

    print('2. IA: qualificacao do cliente...')
    qualif = analise_ia.qualificacao(texto_reuniao, texto_docs, cadastro)
    _ok(f"{qualif.get('nome')} | CPF {qualif.get('cpf') or '-'}")
    print('3. IA: relatorio de triagem (pode levar alguns minutos)...')
    triagem = analise_ia.triagem(texto_reuniao, texto_docs, cadastro)
    _ok(f"{len(triagem.get('operacoes') or [])} operacao(oes), {len(triagem.get('gatilhos') or [])} gatilho(s)")

    print('4. Pasta do cliente...')
    base = pasta_cliente.criar(qualif.get('nome'))
    destino_transc = os.path.join(base, pasta_cliente.CONTRATACAO, 'TRANSCRICAO DA REUNIAO' + os.path.splitext(transcricao)[1])
    shutil.copy2(transcricao, destino_transc)
    for d in docs:
        item, _ = pasta_cliente.guardar_documento(base, d, textos_docs.get(d, ''))
        _ok(f'{os.path.basename(d)} -> {item or "DOCUMENTOS DO CLIENTE"}')
    _ok(base)

    inicio = documentos.data_contrato(cadastro, triagem)
    prazos = documentos.prazos_do_caso(inicio)
    status = relatorio_triagem.status_documentos(triagem, pasta_cliente.arquivos_por_item(base))

    print('5. Relatorio de Triagem...')
    nome_arq = pasta_cliente.nome_pasta(qualif.get('nome')).title()
    rel = os.path.join(base, pasta_cliente.CONTRATACAO,
                       f"{nome_arq} - Relatorio de Triagem - {date.today().strftime('%d-%m-%Y')}.docx")
    relatorio_triagem.gerar(rel, triagem, qualif, prazos, status)
    docx_para_pdf(rel)
    _ok(os.path.basename(rel))

    print('6. Contrato, procuracao e declaracao...')
    gerados, campos = documentos.gerar(base, qualif, triagem, cadastro)
    for g in gerados:
        pend = f" | PENDENTE: {', '.join(g['pendencias'][:4])}" if g['pendencias'] else ''
        _ok(f"{g['documento']}{pend}")

    caso = {
        'id': f"{pasta_cliente.nome_pasta(qualif.get('nome'))}-{datetime.now().strftime('%Y%m%d%H%M')}",
        'etapa': 'DOCUMENTOS GERADOS',
        'data_contrato': inicio.isoformat(),
        'data_contrato_br': inicio.strftime('%d/%m/%Y'),
        'cadastro': cadastro,
        'qualificacao': qualif,
        'triagem': triagem,
        'campos': campos,
        'prazos': prazos,
        'documentos': gerados,
        'documentos_status': status,
    }
    resumo_financeiro(base, caso)
    pasta_cliente.salvar_caso(base, caso)

    if enviar:
        enviar_caso(base, criar_tarefas)
    else:
        print('\nNada foi enviado. Revise os documentos na pasta e depois rode:')
        print(f'   python CONTRATACAO/main.py enviar "{base}"')
    _resumo_final(base)
    return base


def enviar_caso(base, criar_tarefas=False):
    caso = pasta_cliente.ler_caso(base)
    if not caso:
        raise SystemExit(f'ERRO: {base} nao tem 00 CONTRATACAO/caso.json')
    print('\n=== ENVIOS ===')
    # confere os documentos como estao AGORA (podem ter sido editados no Word)
    for d in caso['documentos']:
        d['pendencias'] = documentos.pendencias_no_arquivo(d['arquivo'])

    if not caso.get('zapsign'):
        links = envio.assinatura(caso, caso['documentos'])
        if links:
            caso['zapsign'], caso['enviado_em'] = links, date.today().isoformat()
            caso['etapa'] = 'AGUARDANDO ASSINATURA'
            falta = acompanhamento.faltando(base, caso)
            texto = mensagens.assinatura_e_documentos(caso['qualificacao']['nome'],
                                                      [l for l in links if l.get('link')], falta)
            with open(os.path.join(base, pasta_cliente.CONTRATACAO, 'MENSAGEM AO CLIENTE.txt'), 'w',
                      encoding='utf-8') as f:
                f.write(texto)
            caso['whatsapp_assinatura'] = envio.whatsapp(caso['qualificacao'].get('telefone'), texto)
    else:
        print('   ZapSign: ja enviado antes, nao reenviei.')

    if caso.get('zapsign'):
        # so cadastra e cobra depois que o cliente recebeu os documentos para assinar
        if not caso.get('advbox'):
            caso['advbox'] = envio.advbox(caso, base)
        if not caso.get('asaas'):
            caso['asaas'] = envio.honorarios(caso)
            resumo_financeiro(base, caso)
        if criar_tarefas and not caso.get('tarefas'):
            caso['tarefas'] = envio.tarefas(caso, base)
    pasta_cliente.salvar_caso(base, caso)


def _resumo_final(base):
    caso = pasta_cliente.ler_caso(base)
    print('\n=== RESUMO ===')
    print(f"Cliente: {caso['qualificacao'].get('nome')}")
    print(f'Pasta:   {base}')
    for p in caso['prazos']:
        print(f"  {p['data']}  {p['marco']} ({p['responsavel']})")
    avisos = caso['qualificacao'].get('_avisos') or []
    if avisos:
        print('Conferir: ' + '; '.join(avisos))
    travas = envio.travas(caso['documentos'])
    if travas:
        print('Antes de enviar para assinatura, resolver:')
        for t in travas:
            print(f'  - {t}')


def exemplo():
    ex = os.path.join(RAIZ, 'exemplos')
    return novo(os.path.join(ex, 'TRANSCRICAO_EXEMPLO.txt'), [os.path.join(ex, 'RG_EXEMPLO.txt')],
                os.path.join(ex, 'CADASTRO_EXEMPLO.txt'))


def main():
    ap = argparse.ArgumentParser(description='Fase de contratacao - Caldeira Advogados Associados')
    sub = ap.add_subparsers(dest='cmd', required=True)
    n = sub.add_parser('novo')
    n.add_argument('transcricao')
    n.add_argument('documentos', nargs='*')
    n.add_argument('--cadastro')
    n.add_argument('--enviar', action='store_true')
    n.add_argument('--criar-tarefas', action='store_true')
    e = sub.add_parser('enviar')
    e.add_argument('pasta')
    e.add_argument('--criar-tarefas', action='store_true')
    a = sub.add_parser('acompanhar')
    a.add_argument('--enviar', action='store_true')
    sub.add_parser('painel')
    sub.add_parser('exemplo')
    args = ap.parse_args()

    if args.cmd == 'novo':
        novo(args.transcricao, args.documentos, args.cadastro, args.enviar, args.criar_tarefas)
    elif args.cmd == 'enviar':
        enviar_caso(args.pasta, args.criar_tarefas)
        _resumo_final(args.pasta)
    elif args.cmd == 'acompanhar':
        acompanhamento.acompanhar(args.enviar)
    elif args.cmd == 'painel':
        acompanhamento.painel()
    elif args.cmd == 'exemplo':
        exemplo()


if __name__ == '__main__':
    main()

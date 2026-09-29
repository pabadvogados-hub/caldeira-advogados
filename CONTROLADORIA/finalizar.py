"""
FASE 6 - FINALIZACAO do caso.

  python CONTROLADORIA/main.py finalizar "PASTA DO CLIENTE" --motivo "acordo cumprido"
  ... --atualizar-advbox    grava a data de encerramento no processo do ADVBOX (pede confirmacao)

1. Checklist de encerramento: tarefas abertas no ADVBOX, prazos futuros nas varreduras,
   assinaturas pendentes, cobranca de honorarios, aviso final ao cliente, agenda.
2. Com confirmacao: caso['etapa'] = 'ENCERRADO' (+ bloco 'encerramento' no caso.json),
   Termo de Encerramento no timbrado e a pasta vai para ARQUIVO/AGRONEGOCIO/ANO/
   (PASTA_ARQUIVO_CLIENTES no .env; padrao: PASTA_CLIENTES_RAIZ/ARQUIVO).
A API do ADVBOX nao conclui tarefas: as abertas precisam ser concluidas la, a mao.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum  # noqa: E402
import saidas_varredura  # noqa: E402
from configuracao import pasta_arquivo  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402

OK, PENDENTE, CONFERIR = 'OK', 'PENDENTE', 'CONFERIR'


def _perguntar(texto):
    try:
        return input(texto).strip().lower()
    except EOFError:
        return 'n'


def checklist(base, caso):
    itens = []
    pid = (caso.get('advbox') or {}).get('processo_id')
    hoje = comum.hoje()
    # 1. ADVBOX
    if pid and comum.tem_advbox():
        import advbox_integration as advbox
        try:
            tarefas = [comum.normalizar_tarefa(t) for t in advbox.listar_tarefas_ritmado(lawsuit_id=str(pid))]
            abertas = [t for t in tarefas if any(not p['concluida_em'] for p in t['pessoas'])]
            itens.append(('Tarefas abertas no ADVBOX', PENDENTE if abertas else OK,
                          f"{len(abertas)} aberta(s): " + '; '.join(f"{t['tipo']} ({comum.br(t['prazo'])})"
                                                                     for t in abertas[:6]) if abertas else 'nenhuma'))
        except Exception as e:
            itens.append(('Tarefas abertas no ADVBOX', CONFERIR, f'não consegui ler ({str(e)[:60]})'))
    else:
        itens.append(('Tarefas abertas no ADVBOX', CONFERIR,
                      'conferir no ADVBOX' + ('' if pid else ' (caso sem processo_id no caso.json)')))
    itens.append(('Fase do processo no ADVBOX', CONFERIR,
                  'mudar para a fase de encerrado/arquivado no ADVBOX (ou --atualizar-advbox grava a data de encerramento)'))
    # 2. prazos futuros vistos nas varreduras
    numeros = {comum.digitos(p.get('numero_processo')) for p in comum.pecas_judiciais(caso)} - {''}
    futuros = [i for i in saidas_varredura.historico() if (str(i.get('advbox_processo_id')) == str(pid) and pid)
               or comum.digitos(i.get('processo')) in numeros]
    futuros = [i for i in futuros if i.get('fatal_iso') and comum.data(i['fatal_iso']) >= hoje]
    itens.append(('Prazos em aberto (varreduras do DJEN)', PENDENTE if futuros else OK,
                  '; '.join(f"{i['rotulo']} até {i['fatal']}" for i in futuros) or 'nenhum'))
    # 3. assinaturas e financeiro
    pend_ass = [l_['documento'] for l_ in caso.get('zapsign') or [] if l_.get('status') != 'assinado']
    itens.append(('Documentos para assinatura', PENDENTE if pend_ass else OK, ', '.join(pend_ass) or 'nada pendente'))
    itens.append(('Honorários / êxito', CONFERIR,
                  'conferir com o Financeiro parcelas em aberto e honorários de êxito'
                  + (' (há cobranças no Asaas)' if caso.get('asaas') else '')))
    # 4. cliente, agenda e registros
    itens.append(('Aviso final ao cliente', CONFERIR, 'mensagem de encerramento (modelo no Termo), revisada pelo advogado'))
    itens.append(('Agenda', CONFERIR, 'retirar compromissos futuros deste cliente da agenda'))
    itens.append(('Registros', OK, 'caso.json marcado ENCERRADO + Termo de Encerramento na pasta'))
    return itens


def mensagem_final(caso):
    from envio_cliente import primeiro_nome
    from config.escritorio import ESCRITORIO
    return (f"Olá, {primeiro_nome(comum.nome_do_caso(caso))}! Aqui é do {ESCRITORIO['nome']}. "
            "Passando para avisar que o seu caso foi encerrado no escritório. [PREENCHER: resultado em palavras "
            "simples]. Guardamos toda a documentação e, se precisar de qualquer coisa, é só chamar por aqui. "
            f"Obrigado pela confiança!\n\n{ESCRITORIO['nome']}")


def termo(base, caso, itens, motivo, destino):
    from pasta_cliente import CONTRATACAO, nome_pasta
    doc = novo_documento()
    titulo(doc, 'Termo de Encerramento do Caso')
    paragrafo(doc, comum.nome_do_caso(caso), rotulo='Cliente', espaco=1.0)
    paragrafo(doc, caso.get('data_contrato_br') or comum.br(caso.get('data_contrato')), rotulo='Contrato', espaco=1.0)
    paragrafo(doc, datetime.now().strftime('%d/%m/%Y %H:%M'), rotulo='Encerrado em', espaco=1.0)
    paragrafo(doc, motivo or '[PREENCHER motivo do encerramento]', rotulo='Motivo', espaco=1.0)
    paragrafo(doc, destino, rotulo='Pasta arquivada em', espaco=1.0)
    secao(doc, 'Checklist de encerramento')
    tabela(doc, ['Item', 'Situação', 'Detalhe'], [[a, b, c] for a, b, c in itens], [5, 2.2, 8.5])
    secao(doc, 'Mensagem final ao cliente (revisar antes de enviar)')
    paragrafo(doc, mensagem_final(caso))
    lista(doc, ['Tarefas abertas precisam ser concluídas no ADVBOX (a API não conclui tarefas).',
                'Documentos originais do cliente: devolver ou registrar a guarda.'], tamanho=10)
    caminho = os.path.join(base, CONTRATACAO,
                           f"{nome_pasta(comum.nome_do_caso(caso)).title()} - Termo de Encerramento - "
                           f"{datetime.now():%d-%m-%Y}.docx")
    doc.save(caminho)
    return caminho


def executar(pasta, motivo='', atualizar_advbox=False, sim=False):
    from pasta_cliente import PASTA_AREA, ler_caso, salvar_caso
    print('\n=== FASE 6: FINALIZAÇÃO DO CASO ===')
    base = os.path.abspath(pasta)
    caso = ler_caso(base)
    if not caso:
        raise SystemExit(f'ERRO: não achei 00 CONTRATACAO/caso.json em "{base}".')
    if caso.get('etapa') == 'ENCERRADO':
        print('   Este caso já está ENCERRADO.')
        return None
    itens = checklist(base, caso)
    for a, b, c in itens:
        print(f'   [{b:8}] {a}: {c}')
    pendentes = [a for a, b, _ in itens if b == PENDENTE]
    if not sim:
        pergunta = (f'\n   Há {len(pendentes)} pendência(s). Encerrar mesmo assim? (s/N): ' if pendentes
                    else '\n   Confirmar o encerramento e mover a pasta para o ARQUIVO? (s/N): ')
        if _perguntar(pergunta) != 's':
            print('   Nada foi alterado.')
            return None

    destino_raiz = os.path.join(pasta_arquivo(), PASTA_AREA, str(comum.hoje().year))
    os.makedirs(destino_raiz, exist_ok=True)
    destino = os.path.join(destino_raiz, os.path.basename(base.rstrip('\\/')))
    n = 2
    while os.path.exists(destino):
        destino = os.path.join(destino_raiz, f'{os.path.basename(base)} ({n})')
        n += 1

    caso['etapa'] = 'ENCERRADO'
    caso['encerramento'] = {'data': comum.hoje().isoformat(), 'motivo': motivo, 'pasta_original': base,
                            'pasta_arquivo': destino, 'checklist': [{'item': a, 'situacao': b, 'detalhe': c}
                                                                   for a, b, c in itens]}
    salvar_caso(base, caso)
    arq = termo(base, caso, itens, motivo, destino)
    print(f'   Termo: {os.path.basename(arq)}')

    pid = (caso.get('advbox') or {}).get('processo_id')
    if atualizar_advbox:
        if not (pid and comum.tem_advbox()):
            print('   ADVBOX: sem processo_id ou sem ADVBOX_API_TOKEN, nada gravado.')
        elif sim or _perguntar(f'   Gravar a data de encerramento no processo {pid} do ADVBOX? (s/N): ') == 's':
            import advbox_integration as advbox
            advbox.atualizar_processo(pid, {'status_closure': comum.hoje().isoformat()})
    shutil.move(base, destino)
    print(f'   Pasta arquivada em: {destino}')
    print('   Caso ENCERRADO. Conferir os itens CONFERIR/PENDENTE do Termo.')
    return destino

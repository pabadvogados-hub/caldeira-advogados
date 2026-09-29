"""
Relatorio/feedback do Adv. Extrajudicial ao Gestor Juridico (manual de funcoes): situacao por banco,
prazos do caso, respostas e propostas, proxima acao e o que falta para o caso seguir ao judicial.
Montado so com o caso.json e a pasta do cliente (sem IA). Sai em 10 EXTRAJUDICIAL (.docx + .pdf).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime  # noqa: E402

from docx.shared import Pt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro as reg  # noqa: E402
from docx_caldeira import docx_para_pdf, lista, novo_documento, paragrafo, secao, tabela, titulo  # noqa: E402


def pronto_para_judicial(caso):
    """Bancos que ja podem ir ao judicial e o que falta na pasta para a inicial."""
    bancos = reg.bancos_ativos(caso)
    prontos = [b for b in bancos
               if reg.situacao(reg.ultima(caso, b) or {}) in ('SEM RESPOSTA', 'SEM ACORDO', 'ENCAMINHADO AO JUDICIAL')]
    return bancos, prontos


def falta_para_inicial(base, caso):
    falta = []
    if not reg.arquivos_item(base, 'contratos'):
        falta.append('Cédulas e contratos (pasta 03): nenhum arquivo.')
    if not reg.arquivos_item(base, 'frustracao'):
        falta.append('Laudo de frustração de safra / capacidade de pagamento (pasta 06): nenhum arquivo.')
    if not reg.procuracao_assinada(base):
        falta.append('Procuração assinada (00 CONTRATACAO): não encontrada.')
    for b in reg.bancos_ativos(caso):
        notifs = reg.notificacoes_do_banco(caso, b)
        if not any(n.get('enviada_em') for n in notifs):
            falta.append(f'{b}: notificação ainda não enviada.')
        elif not any(n.get('resposta') for n in notifs):
            falta.append(f'{b}: registrar a resposta ou a ausência de resposta (prova da pretensão resistida).')
    return falta


def gerar(base, caso):
    ext = reg.extrajudicial(caso)
    prazos = reg.prazos_caso(caso)
    h = reg.hoje()
    doc = novo_documento()
    titulo(doc, 'Relatório da Fase Extrajudicial')
    paragrafo(doc, 'Adv. Extrajudicial para o Gestor Jurídico · documento interno', tamanho=10).alignment = 1
    paragrafo(doc, reg.nome_cliente(caso), rotulo='Cliente')
    paragrafo(doc, caso.get('data_contrato_br') or '-', rotulo='Contrato assinado em')
    paragrafo(doc, datetime.now().strftime('%d/%m/%Y %H:%M'), rotulo='Gerado em')

    secao(doc, '1. Alertas')
    alertas = reg.alertas_caso(caso)
    lista(doc, alertas or ['Nenhum alerta de prazo.'])

    secao(doc, '2. Prazos do caso')
    linhas = []
    todos_notificados = all(any(n.get('enviada_em') for n in reg.notificacoes_do_banco(caso, b))
                            for b in reg.bancos_ativos(caso))
    for chave, rotulo in (('notificacao', 'Notificação aos bancos'), ('inicial', 'Protocolo da inicial (máximo)')):
        d = prazos.get(chave)
        falta = f'{(d - h).days} dia(s)' if d else '-'
        if chave == 'notificacao' and todos_notificados:
            falta = 'cumprido (todos notificados)'
        linhas.append([rotulo, reg.br(d) if d else '[CONFERIR]', falta])
    tabela(doc, ['Marco', 'Limite', 'Falta'], linhas, [7.5, 4, 4.2])

    secao(doc, '3. Situação por banco')
    linhas = []
    for b in reg.bancos_ativos(caso):
        notifs = reg.notificacoes_do_banco(caso, b)
        n = notifs[-1] if notifs else {}
        resp = n.get('resposta') or {}
        resposta = ('sem resposta' if resp.get('tipo') == 'sem_resposta'
                    else f"recebida {reg.br(resp.get('data'))}" if resp else '-')
        linhas.append([b, f"{n.get('tipo', '-')} ({len(notifs)}ª)" if notifs else 'não gerada',
                       reg.br(n.get('enviada_em')) if n.get('enviada_em') else '-',
                       reg.br(n.get('prazo_resposta')) if n.get('prazo_resposta') else '-',
                       resposta, reg.situacao(n) if notifs else 'A NOTIFICAR'])
    tabela(doc, ['Banco', 'Notificação', 'Enviada', 'Prazo resp.', 'Resposta', 'Situação'], linhas,
           [3.3, 2.8, 2.2, 2.2, 2.5, 2.7], tamanho=8)

    fora = [b for b in reg.bancos_do_caso(caso) if b not in reg.bancos_ativos(caso)]
    if fora:
        paragrafo(doc, ', '.join(fora) + ' - notificar só se o Gestor decidir.',
                  rotulo='Fora da fase extrajudicial', tamanho=10)

    secao(doc, '4. Próxima ação por banco')
    lista(doc, [f'{b}: {reg.proxima_acao_banco(caso, b)}' for b in reg.bancos_ativos(caso)] or ['-'])

    props = [(n['banco'], p) for n in ext['notificacoes'] for p in n.get('propostas') or []]
    if props:
        secao(doc, '5. Propostas recebidas (decisão do Gestor)')
        lista(doc, [f"{b} ({reg.br(p.get('recebida_em'))}): {p.get('resumo') or '-'} "
                    f"Parecer: {os.path.basename(p.get('parecer') or '')}" for b, p in props], tamanho=10)

    recl = [(n['banco'], n['consumidor_gov']) for n in ext['notificacoes'] if n.get('consumidor_gov')]
    if recl:
        secao(doc, '6. Reclamações no consumidor.gov.br')
        lista(doc, [f"{b}: texto de {reg.br(r.get('gerado_em'))}; protocolo "
                    f"{r.get('protocolo') or 'ainda não registrado'}" for b, r in recl])

    secao(doc, '7. Para seguir ao judicial')
    bancos, prontos = pronto_para_judicial(caso)
    if prontos:
        paragrafo(doc, ', '.join(prontos), rotulo='Via extrajudicial sem acordo')
    falta = falta_para_inicial(base, caso)
    lista(doc, falta or ['Pasta completa para a inicial (conferir com o Adv. Judicial).'])

    pend = [(n['banco'], n.get('pendencias') or []) for n in ext['notificacoes']
            if not n.get('enviada_em') and n.get('pendencias')]
    if pend:
        secao(doc, '8. Minutas com marcas a resolver')
        lista(doc, [f"{b}: {', '.join(p[:6])}{' ...' if len(p) > 6 else ''}" for b, p in pend], tamanho=10)

    p = paragrafo(doc, 'Relatório gerado a partir do registro do caso. PRONTO PARA REVISÃO do Gestor Jurídico. '
                       'Decisões sobre propostas, acordo e ida ao judicial são do Gestor.', negrito=True, tamanho=10)
    p.paragraph_format.space_before = Pt(18)
    caminho = os.path.join(reg.pasta_extra(base), f"{reg.nome_arquivo_cliente(caso)} - Relatorio Extrajudicial ao "
                                                  f"Gestor - {h.strftime('%d-%m-%Y')}.docx")
    doc.save(caminho)
    pdf = docx_para_pdf(caminho)
    ext['relatorios'].append({'arquivo': caminho, 'pdf': pdf, 'gerado_em': reg.iso(h)})
    return caminho, alertas

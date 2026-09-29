"""
Proposta do banco -> PARECER PARA O GESTOR JURIDICO.

A IA compara a proposta com os dados do caso (operacoes, vencimentos, perda relatada, laudos) e com o
pedido do escritorio (DNA: carencia de 2 a 4 anos + 10 a 15 parcelas anuais, mantidos os encargos),
e aponta vantagens, riscos, clausulas de atencao e uma contraproposta. NUNCA aceita nem recusa:
pelo manual, toda proposta vai ao Gestor antes de qualquer resposta ao banco.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

from docx.shared import Pt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro as reg  # noqa: E402
from docx_caldeira import docx_para_pdf, lista, novo_documento, paragrafo, secao, tabela, titulo  # noqa: E402
from CONTRATACAO.extrator import ler_arquivo  # noqa: E402
from config.escritorio import ESCRITORIO  # noqa: E402

MODELO = os.getenv('MODELO_TRIAGEM', 'claude-opus-5')
REFERENCIA_ESCRITORIO = ('carência de 02 a 04 anos + 10 a 15 parcelas anuais, mantidos os encargos originalmente '
                         'pactuados (MCR 2.6.4: prorrogação "aos mesmos encargos financeiros")')


def _s(desc=''):
    return {'type': 'string', 'description': desc} if desc else {'type': 'string'}


def _obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def _lista(item):
    return {'type': 'array', 'items': item}


SCHEMA = _obj({
    'resumo_da_proposta': _s('o que o banco propoe, em 2 a 5 frases, so com o que esta escrito na proposta'),
    'condicoes': _lista(_obj({
        'item': _s('entrada, carencia, prazo, numero de parcelas, taxa, encargos, garantias, confissao de divida etc.'),
        'proposta_do_banco': _s('como esta na proposta; vazio se a proposta nao fala disso'),
        'pedido_do_escritorio': _s('o que a notificacao pediu ou o padrao do escritorio; vazio se nao se aplica'),
        'avaliacao': _s('favoravel, desfavoravel ou neutro, e por que, em uma frase'),
    })),
    'operacoes_abrangidas': _s('quais operacoes do caso a proposta cobre e quais ficam de fora'),
    'compatibilidade_capacidade_pagamento': _s('a proposta cabe na capacidade de pagamento relatada/do laudo? o que falta para saber'),
    'vantagens': _lista(_s()),
    'riscos': _lista(_s()),
    'clausulas_de_atencao': _lista(_s('confissao de divida, renuncia a discutir, troca de cedula rural por CCB, '
                                      'vencimento antecipado, garantia nova, entrada, aval, debito automatico etc.')),
    'contraproposta_sugerida': _obj({
        'carencia': _s(), 'prazo_parcelas': _s(), 'encargos': _s(), 'outras_condicoes': _s(),
        'justificativa': _s('por que e defensavel, com base nos dados do caso'),
    }),
    'perguntas_ao_banco': _lista(_s()),
    'informacoes_faltando': _lista(_s('dado ou documento que falta para o Gestor decidir')),
    'pontos_para_decisao_do_gestor': _lista(_s('o que o Gestor precisa decidir; sem recomendar aceitar ou recusar')),
})


def _sistema():
    e = ESCRITORIO
    sistema = f"""Voce e o analista juridico do Adv. Extrajudicial do {e['nome']} ({e['cidade']}/{e['uf']}), escritorio que defende o produtor rural contra bancos e cooperativas. Um banco respondeu a notificacao extrajudicial com uma PROPOSTA. Voce prepara o PARECER PARA O GESTOR JURIDICO, que decide.

Regras:
- Voce nao aceita nem recusa a proposta e nao recomenda aceitar ou recusar. Aponte fatos, vantagens, riscos e o que decidir. A decisao e do Gestor Juridico.
- Use somente o que esta na proposta, nos dados do caso e nos laudos. Nunca invente taxa, valor, prazo, data ou clausula. O que a proposta nao disser vai para "informacoes_faltando" ou "perguntas_ao_banco".
- Referencia do escritorio para o pedido: {REFERENCIA_ESCRITORIO}. A carencia e o numero de parcelas saem do laudo de capacidade de pagamento, quando houver.
- Pontos que o material de referencia mostra como sensiveis: exigencia de entrada/pagamento antecipado como condicao para prorrogar; troca de cedula rural por CCB ou renegociacao com recursos livres (pode tirar a operacao do regime do credito rural); confissao de divida e renuncia a discutir encargos; encargos acima dos pactuados; garantias novas ou aval novo; proposta que cobre so parte das operacoes; proposta aprovada e nao implementada vira argumento do banco em juizo (registre isso como risco quando couber).
- A contraproposta deve ser defensavel com os dados do caso; se faltar laudo, diga que os numeros dependem dele.
- Portugues formal, objetivo, frases curtas."""
    dna = ambiente.ler_base('DNA_PECAS.md')
    if dna:
        sistema += f'\n\n<material_de_referencia>\n{dna}\n</material_de_referencia>\n'
    return sistema


def analisar_ia(caso, banco, n, texto_proposta, laudos):
    import ia
    t = caso.get('triagem') or {}
    dados = {
        'credor': banco,
        'operacoes_com_este_credor': reg.operacoes_do_banco(caso, banco),
        'atividade_rural': t.get('atividade_rural'),
        'linha_do_tempo': t.get('linha_do_tempo'),
        'pedido_da_notificacao': n.get('pedido') or f'nao registrado; referencia do escritorio: {REFERENCIA_ESCRITORIO}',
        'notificacao_enviada_em': reg.br(n.get('enviada_em')) if n.get('enviada_em') else 'nao registrado',
    }
    conteudo = (f'<dados_do_caso>\n{json.dumps(dados, ensure_ascii=False, indent=1)}\n</dados_do_caso>\n\n'
                f'<proposta_do_banco>\n{texto_proposta[:60000]}\n</proposta_do_banco>\n\n'
                f"<laudos>\n{laudos or '(nenhum laudo na pasta 06 ainda)'}\n</laudos>\n\n"
                'Monte o parecer para o Gestor Juridico.')
    return ia.json_por_schema(MODELO, _sistema(), conteudo, SCHEMA, 16000)


def analisar_sem_ia(caso, banco, n, texto_proposta):
    p = '[PREENCHER]'
    return {
        'resumo_da_proposta': f'[PREENCHER resumo da proposta] Trecho: {texto_proposta[:600]}',
        'condicoes': [{'item': i, 'proposta_do_banco': p, 'pedido_do_escritorio': ped, 'avaliacao': p}
                      for i, ped in (('Entrada / pagamento inicial', 'sem entrada'),
                                     ('Carência', f"{(n.get('pedido') or {}).get('carencia_anos', '02 a 04')} anos"),
                                     ('Parcelas anuais', f"{(n.get('pedido') or {}).get('parcelas_anuais', '10 a 15')}"),
                                     ('Encargos', 'mantidos os pactuados'),
                                     ('Garantias', 'sem garantia nova'))],
        'operacoes_abrangidas': p, 'compatibilidade_capacidade_pagamento': p,
        'vantagens': [p], 'riscos': [p], 'clausulas_de_atencao': [p],
        'contraproposta_sugerida': {'carencia': p, 'prazo_parcelas': p, 'encargos': p, 'outras_condicoes': p,
                                    'justificativa': p},
        'perguntas_ao_banco': [p], 'informacoes_faltando': [p],
        'pontos_para_decisao_do_gestor': ['Aceitar, contrapropor ou seguir para o judicial (decisão do Gestor).'],
    }


def _docx(caminho, caso, banco, n, a, arquivo_proposta):
    doc = novo_documento()
    titulo(doc, 'Parecer para o Gestor Jurídico')
    paragrafo(doc, f'Proposta do {banco} · documento interno do Adv. Extrajudicial', tamanho=10).alignment = 1
    paragrafo(doc, reg.nome_cliente(caso), rotulo='Cliente')
    paragrafo(doc, banco, rotulo='Banco')
    paragrafo(doc, os.path.basename(arquivo_proposta), rotulo='Proposta analisada')
    paragrafo(doc, reg.br(n.get('enviada_em')) if n.get('enviada_em') else 'não registrada', rotulo='Notificação enviada em')
    paragrafo(doc, reg.br(reg.hoje()), rotulo='Parecer de')

    secao(doc, '1. Resumo da proposta')
    paragrafo(doc, a.get('resumo_da_proposta'), recuo=True)
    secao(doc, '2. Proposta x pedido do escritório')
    tabela(doc, ['Item', 'Proposta do banco', 'Pedido do escritório', 'Avaliação'],
           [[c.get('item'), c.get('proposta_do_banco'), c.get('pedido_do_escritorio'), c.get('avaliacao')]
            for c in a.get('condicoes') or []], [3.2, 4.3, 3.8, 4.4])
    secao(doc, '3. Operações abrangidas')
    paragrafo(doc, a.get('operacoes_abrangidas'), recuo=True)
    secao(doc, '4. Capacidade de pagamento')
    paragrafo(doc, a.get('compatibilidade_capacidade_pagamento'), recuo=True)
    secao(doc, '5. Vantagens')
    lista(doc, a.get('vantagens') or ['-'])
    secao(doc, '6. Riscos')
    lista(doc, a.get('riscos') or ['-'])
    secao(doc, '7. Cláusulas que pedem atenção')
    lista(doc, a.get('clausulas_de_atencao') or ['-'])
    secao(doc, '8. Contraproposta sugerida')
    cp = a.get('contraproposta_sugerida') or {}
    for rotulo, chave in (('Carência', 'carencia'), ('Prazo e parcelas', 'prazo_parcelas'), ('Encargos', 'encargos'),
                          ('Outras condições', 'outras_condicoes'), ('Justificativa', 'justificativa')):
        paragrafo(doc, cp.get(chave) or '-', rotulo=rotulo)
    secao(doc, '9. Perguntas ao banco')
    lista(doc, a.get('perguntas_ao_banco') or ['-'])
    secao(doc, '10. Informações que faltam')
    lista(doc, a.get('informacoes_faltando') or ['-'])
    secao(doc, '11. O que o Gestor Jurídico decide')
    lista(doc, a.get('pontos_para_decisao_do_gestor') or ['-'])
    p = paragrafo(doc, 'PARECER PRONTO PARA REVISÃO DO GESTOR JURÍDICO. A IA não aceita nem recusa proposta e nada '
                       'é respondido ao banco antes da decisão do Gestor. Registrar a decisão com: '
                       'python EXTRAJUDICIAL/main.py decisao "PASTA" --banco X --resultado acordo|sem-acordo',
                  negrito=True, tamanho=10)
    p.paragraph_format.space_before = Pt(18)
    doc.save(caminho)
    return caminho


def analisar(base, caso, banco, arquivo, usar_ia=True):
    n = reg.ultima(caso, banco)
    if not n:
        raise SystemExit(f'ERRO: não há notificação ao {banco} neste caso (gere/registre a notificação antes).')
    if not os.path.exists(arquivo):
        raise SystemExit(f'ERRO: arquivo não encontrado: {arquivo}')
    texto = ler_arquivo(arquivo)
    if len(texto.strip()) < 30:
        raise SystemExit('ERRO: não consegui ler a proposta (PDF escaneado sem OCR?). Mande em .txt ou instale o Tesseract.')
    pasta = reg.pasta_extra(base)
    data = reg.hoje().strftime('%d-%m-%Y')
    raiz = f'{reg.nome_arquivo_cliente(caso)} - Proposta {reg.arquivo_seguro(banco).upper()} - {data}'
    copia = os.path.join(pasta, raiz + os.path.splitext(arquivo)[1].lower())
    if os.path.abspath(arquivo) != os.path.abspath(copia):
        shutil.copy2(arquivo, copia)

    if usar_ia and ambiente.tem_credencial('ANTHROPIC_API_KEY'):
        print(f'   {banco}: IA analisando a proposta (pode levar alguns minutos)...')
        a = analisar_ia(caso, banco, n, texto, reg.texto_documentos(base, 'frustracao', limite_total=40000))
    else:
        print(f'   {banco}: sem IA (sem ANTHROPIC_API_KEY ou --sem-ia): parecer-esqueleto com [PREENCHER].')
        a = analisar_sem_ia(caso, banco, n, texto)
    parecer = _docx(os.path.join(pasta, f'{reg.nome_arquivo_cliente(caso)} - Parecer Proposta '
                                        f'{reg.arquivo_seguro(banco).upper()} - {data}.docx'),
                    caso, banco, n, a, copia)
    pdf = docx_para_pdf(parecer)
    if not n.get('resposta'):
        n['resposta'] = {'tipo': 'recebida', 'data': reg.iso(reg.hoje()), 'arquivo': copia,
                         'trecho': texto[:400], 'registrada_em': reg.iso(reg.hoje())}
    n.setdefault('propostas', []).append({'arquivo': copia, 'parecer': parecer, 'pdf': pdf,
                                          'recebida_em': reg.iso(reg.hoje()), 'gerado_em': reg.iso(reg.hoje()),
                                          'resumo': ' '.join((a.get('resumo_da_proposta') or '').split())[:600]})
    reg.evento(n, 'Proposta do banco recebida; parecer ao Gestor gerado')
    return parecer, a

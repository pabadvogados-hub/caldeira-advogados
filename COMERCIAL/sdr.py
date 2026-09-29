"""
SDR DE IA - qualificacao do lead antes do Closer.

Le a conversa do lead (export do WhatsApp / Atende Direito, .txt; tambem .pdf/.docx) e devolve:
- JSON com os dados colhidos (produtor rural? credito rural? bancos, valores, vencimentos, perda de
  safra e causa, regiao, execucao/cobranca, urgencia), dados faltantes e a proxima pergunta;
- NOTA 0-100 calculada por regra fixa (config_comercial.py), para ser igual para todo lead;
- RESUMO PARA O CLOSER (.txt para colar no CRM + .docx no timbrado) com a proposta sugerida.
  Valores de honorarios: so os da tabela do escritorio (config_comercial.PROPOSTAS); vazio = [DEFINIR].

E pre-qualificacao COMERCIAL: nao e parecer juridico e nao decide estrategia (isso e do Gestor Juridico).
Sem ANTHROPIC_API_KEY (ou com --sem-ia) faz uma pre-analise por palavras-chave, marcada como tal.
"""
import json
import os
import re
from datetime import datetime

import ambiente
import ia
from config_comercial import (NOTA_MINIMA_QUALIFICADO, PESOS_DIVIDA_RURAL, PESOS_PREVIDENCIARIO, PROPOSTAS,
                              UFS_ATENDIMENTO)

MODELO_SDR = os.getenv('MODELO_SDR') or os.getenv('MODELO_EXTRACAO') or 'claude-sonnet-5'
DEFINIR = '[DEFINIR PELO ESCRITÓRIO]'
SNI = ['SIM', 'NAO', 'NAO INFORMADO']


def _s(desc=''):
    return {'type': 'string', 'description': desc} if desc else {'type': 'string'}


def _e(opcoes, desc=''):
    d = {'type': 'string', 'enum': opcoes}
    if desc:
        d['description'] = desc
    return d


def _obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def _lista(item):
    return {'type': 'array', 'items': item}


SCHEMA = _obj({
    'area': _e(['DIVIDA_RURAL_BANCO', 'PREVIDENCIARIO_RURAL', 'OUTRO', 'INDEFINIDO'],
               'assunto principal do lead'),
    'nome_lead': _s('como o lead se apresentou, ou vazio'),
    'telefone': _s('se aparecer na conversa, ou vazio'),
    'municipio': _s('municipio onde produz/mora, ou vazio'),
    'uf': _s('sigla da UF, ou vazio'),
    'produtor_rural': _e(SNI, 'e produtor rural (pessoa fisica ou empresa do produtor)?'),
    'atividade': _s('soja, milho, gado de corte, leite, cafe etc., como foi dito'),
    'area_hectares': _s('area/propriedade como foi dita, ou vazio'),
    'tem_credito_rural': _e(SNI, 'tem divida com banco/cooperativa ligada a atividade rural?'),
    'bancos': _lista(_obj({
        'banco': _s('banco ou cooperativa como foi dito'),
        'tipo_operacao': _s('custeio, investimento, CPR, CCB, cedula rural, maquinario etc., ou vazio'),
        'valor_aproximado': _s('como foi dito, ou vazio'),
        'vencimento': _s('data/mes/safra de vencimento como foi dito, ou vazio'),
        'situacao': _s('em dia, vencida, renegociada, em execucao, nao informado'),
    })),
    'valor_total_aproximado': _s('soma aproximada das dividas, como foi dita; vazio se nao disse'),
    'proximo_vencimento': _s('o vencimento mais proximo mencionado, ou vazio'),
    'ja_venceu': _e(SNI, 'ha parcela ja vencida?'),
    'perda_safra': _e(SNI, 'teve frustracao de safra, perda de producao ou queda forte de receita?'),
    'causa_perda': _s('seca, excesso de chuva, praga, doenca, queda de preco, custo alto etc., ou vazio'),
    'safra_afetada': _s('ex.: soja 2025/2026, ou vazio'),
    'cobranca_em_andamento': _e(SNI, 'ha execucao, protesto, negativacao, busca e apreensao, leilao ou cobranca?'),
    'detalhe_cobranca': _s('o que esta acontecendo, ou vazio'),
    'avalistas_garantias': _s('avalistas, hipoteca, penhor, alienacao fiduciaria mencionados, ou vazio'),
    'ja_pediu_prorrogacao': _e(SNI, 'ja pediu prorrogacao/renegociacao ao banco?'),
    'resposta_banco': _s('o que o banco respondeu, ou vazio'),
    'urgencia': _e(['ALTA', 'MEDIA', 'BAIXA']),
    'motivo_urgencia': _s('fato que justifica a urgencia'),
    'previdenciario': _obj({
        'beneficio': _s('salario-maternidade, BPC/LOAS, aposentadoria rural etc., ou vazio'),
        'trabalho_rural': _e(SNI, 'trabalha/trabalhou na roca em regime de economia familiar?'),
        'situacao': _s('data do parto, idade, deficiencia, pedido negado no INSS etc., ou vazio'),
        'documentos_rurais': _e(SNI, 'tem algum documento rural (nota de produtor, ITR, CAR, sindicato)?'),
    }),
    'dados_faltantes': _lista(_s('informacao que o SDR ainda precisa colher')),
    'proxima_pergunta': _s('UMA pergunta curta, no tom do escritorio, para o SDR mandar agora'),
    'sinais_alerta': _lista(_s('ex.: quer garantia de resultado, nao e produtor, so quer consulta gratis, '
                               'ja tem advogado no caso, pediu preco por mensagem')),
    'pacote_sugerido': _e(list(PROPOSTAS), 'qual servico da tabela do escritorio combina com o caso'),
    'observacao_proposta': _s('por que esse servico; o que o Closer deve confirmar antes de propor'),
    'resumo_closer': _s('4 a 8 linhas para o Closer ligar ja sabendo do caso; so fatos da conversa'),
    'trechos': _lista(_obj({'tema': _s(), 'trecho': _s('citacao literal curta da conversa')})),
})


def _secao(texto, inicio, fim):
    i = texto.find(inicio)
    if i < 0:
        return ''
    j = texto.find(fim, i + len(inicio))
    return texto[i:j if j > 0 else None]


def _referencia():
    dna = ambiente.ler_base('DNA_PECAS.md')
    partes = [_secao(dna, '## 4. FATOS QUE AS PEÇAS SEMPRE TÊM', '## 5.'),
              _secao(dna, '### 7.5 Pontos de risco', '## 8.')]
    return '\n'.join(p for p in partes if p)


def sistema():
    ufs = ', '.join(UFS_ATENDIMENTO)
    return f"""Voce e o SDR (pre-atendimento comercial) do Caldeira Advogados Associados, de Cacoal/RO. O escritorio defende o produtor rural contra bancos e cooperativas de credito (prorrogacao e alongamento de divida rural, defesa em execucao) e tambem atende previdenciario rural (salario-maternidade, BPC, aposentadoria rural). Regiao de atendimento: {ufs} (Rondonia e norte do Mato Grosso).

Voce recebe a conversa de um lead (mensagens do WhatsApp) e preenche a ficha de qualificacao para o Closer, que vai ligar para fechar o contrato ja sabendo do caso.

Regras:
- Use somente o que o lead disse na conversa. Nunca invente banco, valor, data, municipio ou nome. O que nao foi dito fica vazio ou "NAO INFORMADO" e entra em "dados_faltantes".
- Valores e datas como foram ditos ("uns 800 mil", "vence em marco").
- "urgencia" ALTA: parcela vencida ou vencendo em ate 30 dias, execucao, busca e apreensao, leilao, penhora, negativacao, avalista sendo cobrado. MEDIA: vencimento em ate 90 dias ou perda de safra recente sem cobranca. BAIXA: o resto.
- "proxima_pergunta": uma pergunta so, curta, simples, respeitosa, no jeito de falar do produtor (sem juridiques), sobre o dado mais importante que falta. Nunca pergunte senha, CPF ou dado bancario.
- "pacote_sugerido": EXTRAJUDICIAL (so pedido ao banco, divida ainda nao cobrada judicialmente), EXTRAJUDICIAL_JUDICIAL (caso padrao de prorrogacao: pedido ao banco e acao se nao atender), EMBARGOS_EXECUCAO (ja existe execucao), PREVIDENCIARIO_RURAL, ou AVALIAR (fora do padrao ou faltam dados basicos). Nao escreva valores de honorarios: quem define e o escritorio.
- "sinais_alerta": pontos que o Closer precisa tratar (pede garantia de resultado, nao e produtor, divida nao e rural, ja tem advogado, desconfianca, pediu preco por mensagem).
- "resumo_closer": linguagem simples e direta, terceira pessoa, so fatos da conversa.
- Isto e pre-qualificacao comercial: nao de parecer juridico e nao afirme que o lead tem direito.
- Todo texto que voce escrever (resumo, pergunta, faltantes, alertas, observacao) vai para a equipe e para o lead:
  escreva em portugues correto, COM acentuacao.

<o_que_o_escritorio_precisa_saber_de_cada_caso>
{_referencia()}
</o_que_o_escritorio_precisa_saber_de_cada_caso>
"""


# ============================================================
# LEITURA DA CONVERSA
# ============================================================

LINHA_WPP = re.compile(r'^\[?(\d{1,2}/\d{1,2}/\d{2,4})[ ,]+(\d{1,2}:\d{2})(?::\d{2})?\]?\s*(?:-\s*)?([^:]{1,60}):\s?(.*)$')


def ler_conversa(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    if ext in ('.txt', '.csv', '.md', ''):
        for cod in ('utf-8-sig', 'latin-1'):
            try:
                with open(caminho, encoding=cod) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
    import sys
    sys.path.insert(0, os.path.join(ambiente.RAIZ, 'CONTRATACAO'))
    from extrator import ler_arquivo  # CONTRATACAO/extrator.py (pdf, docx, legenda)
    return ler_arquivo(caminho)


def falas(texto):
    """[(autor, mensagem)] de um export do WhatsApp; linhas de continuacao entram na fala anterior."""
    saida = []
    for linha in texto.splitlines():
        m = LINHA_WPP.match(linha.strip())
        if m:
            saida.append([m.group(3).strip(), m.group(4).strip()])
        elif saida and linha.strip():
            saida[-1][1] += ' ' + linha.strip()
    return saida


# ============================================================
# NOTA (regra fixa, igual para todo lead)
# ============================================================

def _preenchido(v):
    return bool(v) and str(v).strip().upper() not in ('', 'NAO INFORMADO', 'NÃO INFORMADO', '-')


def pontuar(d):
    motivos, nota = [], 0

    def soma(cond, pontos, ok, falta):
        nonlocal nota
        if cond:
            nota += pontos
            motivos.append(f'+{pontos} {ok}')
        else:
            motivos.append(f' 0 {falta}')

    if d.get('area') == 'PREVIDENCIARIO_RURAL':
        p = d.get('previdenciario') or {}
        w = PESOS_PREVIDENCIARIO
        soma(_preenchido(p.get('beneficio')), w['beneficio'], f"benefício: {p.get('beneficio')}", 'benefício não informado')
        soma(p.get('trabalho_rural') == 'SIM', w['trabalho_rural'], 'trabalho rural confirmado', 'trabalho rural não confirmado')
        soma(_preenchido(p.get('situacao')), w['situacao'], 'situação informada', 'situação não informada')
        soma(p.get('documentos_rurais') == 'SIM', w['documentos'], 'tem documento rural', 'documento rural não confirmado')
        return nota, motivos

    w = PESOS_DIVIDA_RURAL
    bancos = [b for b in d.get('bancos') or [] if _preenchido(b.get('banco'))]
    tem_valor = _preenchido(d.get('valor_total_aproximado')) or any(_preenchido(b.get('valor_aproximado')) for b in bancos)
    tem_venc = (_preenchido(d.get('proximo_vencimento')) or d.get('ja_venceu') == 'SIM'
                or any(_preenchido(b.get('vencimento')) for b in bancos))
    soma(d.get('produtor_rural') == 'SIM', w['produtor_rural'], 'produtor rural confirmado', 'não confirmou ser produtor rural')
    soma(d.get('tem_credito_rural') == 'SIM', w['credito_rural'], 'dívida rural com banco/cooperativa',
         'dívida rural não confirmada')
    soma(bool(bancos), w['banco'], 'banco(s): ' + ', '.join(b['banco'] for b in bancos), 'banco não informado')
    soma(tem_valor, w['valor'], 'valor aproximado informado', 'valor não informado')
    soma(tem_venc, w['vencimento'], 'vencimento informado', 'vencimento não informado')
    soma(d.get('perda_safra') == 'SIM' and _preenchido(d.get('causa_perda')), w['perda'],
         f"perda/queda de receita: {d.get('causa_perda')}", 'perda de safra e causa não informadas')
    uf = (d.get('uf') or '').strip().upper()
    soma(uf in UFS_ATENDIMENTO, w['regiao'], f'região de atendimento ({uf})', 'região não informada ou fora de RO/MT')
    soma(d.get('cobranca_em_andamento') == 'SIM' or d.get('ja_venceu') == 'SIM' or d.get('urgencia') == 'ALTA',
         w['cobranca'], 'urgência: cobrança/vencimento', 'sem cobrança ou vencimento próximo informado')
    return nota, motivos


def classificar(d):
    nota, motivos = pontuar(d)
    area = d.get('area')
    if area == 'OUTRO':
        status = 'FORA DO FOCO'
    elif area == 'DIVIDA_RURAL_BANCO' and (d.get('produtor_rural') == 'NAO' or d.get('tem_credito_rural') == 'NAO'):
        status = 'FORA DO FOCO'
    elif nota >= NOTA_MINIMA_QUALIFICADO and (area == 'PREVIDENCIARIO_RURAL' or (
            d.get('produtor_rural') == 'SIM' and d.get('tem_credito_rural') == 'SIM')):
        status = 'QUALIFICADO'
    else:
        status = 'EM QUALIFICACAO'
    if str(d.get('_modo', '')).startswith('palavras'):
        status = 'PRE-ANALISE SEM IA (conferir)'   # palavra-chave nunca qualifica sozinha
    pacote = d.get('pacote_sugerido') or 'AVALIAR'
    tabela = PROPOSTAS.get(pacote, PROPOSTAS['AVALIAR'])
    proposta = {
        'pacote': pacote,
        'servico': tabela['servico'],
        'entrada': tabela.get('entrada') or DEFINIR,
        'parcelas': tabela.get('parcelas') or DEFINIR,
        'exito': tabela.get('exito') or DEFINIR,
        'observacao': d.get('observacao_proposta', ''),
    }
    return {'status': status, 'qualificado': status == 'QUALIFICADO', 'nota': nota, 'motivos': motivos,
            'proposta': proposta}


# ============================================================
# PRE-ANALISE SEM IA (palavras-chave) - so para nao ficar parado sem credencial
# ============================================================

BANCOS = ['Banco do Brasil', 'Sicoob', 'Sicredi', 'Cresol', 'Banco da Amazônia', 'Basa', 'Caixa', 'Bradesco',
          'Santander', 'Itaú', 'Rabobank', 'John Deere', 'CNH', 'BNDES', 'Unicred', 'Banco do Nordeste']


def _tem(texto, palavras):
    return any(re.search(r'\b' + p, texto, re.I) for p in palavras)


def pre_analise_sem_ia(texto):
    conversa = falas(texto)
    lead = conversa[0][0] if conversa else ''
    do_lead = ' '.join(m for a, m in conversa if a == lead) or texto
    bancos = []
    for b in BANCOS:
        if re.search(r'\b' + re.escape(b) + r'\b', do_lead, re.I) or (b == 'Banco do Brasil' and re.search(r'\bBB\b', do_lead)):
            bancos.append({'banco': b, 'tipo_operacao': '', 'valor_aproximado': '', 'vencimento': '', 'situacao': 'NAO INFORMADO'})
    valores = re.findall(r'(?:R\$\s?[\d.,]+(?:\s?(?:mil|milh[õo]es?|mi))?|\b\d[\d.,]*\s?(?:mil|milh[õo]es?|mi)\b)', do_lead, re.I)
    rural = _tem(do_lead, ['soja', 'milho', 'gado', 'boi', 'leite', 'lavoura', 'safra', 'fazenda', 'sítio', 'sitio',
                           'produtor', 'plant', 'rebanho', 'arroba', 'caf[eé]', 'cacau', 'pasto'])
    prev = _tem(do_lead, ['sal[aá]rio.maternidade', 'BPC', 'LOAS', 'aposentadoria', 'INSS'])
    perda = _tem(do_lead, ['seca', 'estiagem', 'chuva', 'praga', 'lagarta', 'quebr', 'frustra', 'perdi', 'perda',
                           'pre[cç]o caiu', 'n[aã]o colhi'])
    cobranca = _tem(do_lead, ['execu', 'protest', 'negativ', 'serasa', 'oficial de justi', 'busca e apreens',
                              'leil[aã]o', 'penhor', 'cobran'])
    venc = re.findall(r'venc\w*[^.?!]{0,40}', do_lead, re.I)
    uf = next((u for u in UFS_ATENDIMENTO if re.search(r'\b' + u + r'\b', do_lead)), '')
    if not uf and re.search(r'rond[oô]nia', do_lead, re.I):
        uf = 'RO'
    if not uf and re.search(r'mato grosso', do_lead, re.I):
        uf = 'MT'
    sn = lambda c: 'SIM' if c else 'NAO INFORMADO'  # noqa: E731
    faltando = [x for x, ok in (('banco', bancos), ('valor aproximado', valores), ('vencimento', venc),
                                ('perda de safra e causa', perda), ('município/UF', uf)) if not ok]
    area = 'PREVIDENCIARIO_RURAL' if prev and not bancos else ('DIVIDA_RURAL_BANCO' if bancos or rural else 'INDEFINIDO')
    return {
        'area': area, 'nome_lead': lead, 'telefone': '', 'municipio': '', 'uf': uf,
        'produtor_rural': sn(rural), 'atividade': '', 'area_hectares': '',
        'tem_credito_rural': sn(bancos and rural), 'bancos': bancos,
        'valor_total_aproximado': '; '.join(valores[:3]), 'proximo_vencimento': '; '.join(v.strip() for v in venc[:2]),
        'ja_venceu': sn(re.search(r'venceu|vencid|atrasad', do_lead, re.I)),
        'perda_safra': sn(perda), 'causa_perda': 'citada na conversa (conferir)' if perda else '', 'safra_afetada': '',
        'cobranca_em_andamento': sn(cobranca), 'detalhe_cobranca': '', 'avalistas_garantias': '',
        'ja_pediu_prorrogacao': 'NAO INFORMADO', 'resposta_banco': '',
        'urgencia': 'ALTA' if cobranca else 'MEDIA', 'motivo_urgencia': 'cobrança citada' if cobranca else '',
        'previdenciario': {'beneficio': 'citado (conferir)' if prev else '', 'trabalho_rural': sn(prev and rural),
                           'situacao': '', 'documentos_rurais': 'NAO INFORMADO'},
        'dados_faltantes': faltando, 'proxima_pergunta': '',
        'sinais_alerta': ['PRE-ANALISE SEM IA (palavras-chave): conferir tudo lendo a conversa']
        + (['lead perguntou sobre garantia de resultado'] if re.search(r'garant', do_lead, re.I) else []),
        'pacote_sugerido': 'EMBARGOS_EXECUCAO' if re.search(r'execu', do_lead, re.I) else 'AVALIAR',
        'observacao_proposta': '', 'resumo_closer': '', 'trechos': [],
    }


# ============================================================
# SAIDAS
# ============================================================

def resumo_texto(d, c):
    L = []
    add = L.append
    add('RESUMO PARA O CLOSER - pré-qualificação comercial (não é análise jurídica)')
    add(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    add('')
    add(f"LEAD: {d.get('nome_lead') or '-'} | Tel.: {d.get('telefone') or '-'} | "
        f"{d.get('municipio') or '-'}/{d.get('uf') or '-'}")
    add(f"STATUS: {c['status']} | NOTA {c['nota']}/100 (mínimo {NOTA_MINIMA_QUALIFICADO}) | URGÊNCIA {d.get('urgencia')}"
        + (f" - {d['motivo_urgencia']}" if d.get('motivo_urgencia') else ''))
    add(f"ÁREA: {d.get('area')}")
    add('')
    if d.get('resumo_closer'):
        add('O CASO')
        add(d['resumo_closer'])
        add('')
    add('O QUE JÁ SABEMOS')
    for rot, chave in (('Produtor rural', 'produtor_rural'), ('Atividade', 'atividade'), ('Área', 'area_hectares'),
                       ('Dívida rural com banco', 'tem_credito_rural'), ('Total aproximado', 'valor_total_aproximado'),
                       ('Próximo vencimento', 'proximo_vencimento'), ('Já venceu parcela', 'ja_venceu'),
                       ('Perda de safra', 'perda_safra'), ('Causa', 'causa_perda'), ('Safra', 'safra_afetada'),
                       ('Cobrança/execução', 'cobranca_em_andamento'), ('Detalhe', 'detalhe_cobranca'),
                       ('Avalistas/garantias', 'avalistas_garantias'), ('Já pediu prorrogação', 'ja_pediu_prorrogacao'),
                       ('Resposta do banco', 'resposta_banco')):
        if _preenchido(d.get(chave)):
            add(f'  {rot}: {d[chave]}')
    for b in d.get('bancos') or []:
        add(f"  Banco: {b.get('banco')} | {b.get('tipo_operacao') or '-'} | {b.get('valor_aproximado') or '-'} | "
            f"venc. {b.get('vencimento') or '-'} | {b.get('situacao') or '-'}")
    if d.get('area') == 'PREVIDENCIARIO_RURAL':
        p = d.get('previdenciario') or {}
        add(f"  Benefício: {p.get('beneficio') or '-'} | trabalho rural: {p.get('trabalho_rural')} | "
            f"situação: {p.get('situacao') or '-'} | documentos rurais: {p.get('documentos_rurais')}")
    add('')
    add('PONTUAÇÃO')
    L += [f'  {m}' for m in c['motivos']]
    if d.get('dados_faltantes'):
        add('')
        add('FALTA SABER (o Closer confirma na reunião)')
        L += [f'  - {x}' for x in d['dados_faltantes']]
    if d.get('proxima_pergunta'):
        add('')
        add(f"PRÓXIMA PERGUNTA DO SDR: {d['proxima_pergunta']}")
    if d.get('sinais_alerta'):
        add('')
        add('SINAIS DE ALERTA')
        L += [f'  - {x}' for x in d['sinais_alerta']]
    p = c['proposta']
    add('')
    add('PROPOSTA SUGERIDA (o escritório define os valores)')
    add(f"  Serviço: {p['servico']}")
    add(f"  Entrada: {p['entrada']} | Parcelas: {p['parcelas']} | Êxito: {p['exito']}")
    if p.get('observacao'):
        add(f"  Observação: {p['observacao']}")
    if d.get('trechos'):
        add('')
        add('TRECHOS DA CONVERSA')
        L += [f"  [{t.get('tema')}] \"{t.get('trecho')}\"" for t in d['trechos']]
    add('')
    add('Lembrete: nenhuma promessa de resultado ao lead (Provimento 205/2021). A estratégia é do Gestor Jurídico.')
    return '\n'.join(L) + '\n'


def resumo_docx(d, c, caminho):
    from docx_caldeira import lista, novo_documento, paragrafo, secao, tabela, titulo
    doc = novo_documento()
    titulo(doc, 'Resumo para o Closer')
    paragrafo(doc, 'Pré-qualificação comercial feita a partir da conversa do lead. Não é análise jurídica.', tamanho=10)
    paragrafo(doc, f"{d.get('nome_lead') or '-'} - {d.get('municipio') or '-'}/{d.get('uf') or '-'}", 'Lead')
    paragrafo(doc, f"{c['status']} - nota {c['nota']}/100 - urgência {d.get('urgencia')}", 'Status')
    if d.get('resumo_closer'):
        secao(doc, 'O caso')
        paragrafo(doc, d['resumo_closer'])
    if d.get('bancos'):
        secao(doc, 'Dívidas citadas')
        tabela(doc, ['Banco', 'Operação', 'Valor', 'Vencimento', 'Situação'],
               [[b.get('banco'), b.get('tipo_operacao'), b.get('valor_aproximado'), b.get('vencimento'),
                 b.get('situacao')] for b in d['bancos']], [3.5, 3.2, 3, 3, 3])
    secao(doc, 'Pontuação')
    lista(doc, c['motivos'], tamanho=10)
    if d.get('dados_faltantes'):
        secao(doc, 'Falta saber')
        lista(doc, d['dados_faltantes'])
    if d.get('sinais_alerta'):
        secao(doc, 'Sinais de alerta')
        lista(doc, d['sinais_alerta'])
    p = c['proposta']
    secao(doc, 'Proposta sugerida')
    paragrafo(doc, p['servico'], 'Serviço')
    paragrafo(doc, f"Entrada: {p['entrada']} | Parcelas: {p['parcelas']} | Êxito: {p['exito']}", 'Honorários')
    if p.get('observacao'):
        paragrafo(doc, p['observacao'], 'Observação')
    doc.save(caminho)
    return caminho


def qualificar(texto, sem_ia=False):
    if sem_ia or not ambiente.tem_credencial('ANTHROPIC_API_KEY'):
        if not sem_ia:
            print('   aviso: ANTHROPIC_API_KEY ausente; fazendo pre-analise por palavras-chave')
        dados = pre_analise_sem_ia(texto)
        dados['_modo'] = 'palavras-chave (sem IA)'
    else:
        conteudo = f'<conversa_do_lead>\n{texto[:60000]}\n</conversa_do_lead>\n\nPreencha a ficha de qualificacao deste lead.'
        dados = ia.json_por_schema(MODELO_SDR, sistema(), conteudo, SCHEMA, max_tokens=8000)
        dados['_modo'] = f'IA ({MODELO_SDR})'
    if not dados.get('nome_lead'):
        conversa = falas(texto)
        if conversa:   # quem abriu a conversa, como aparece no export (nao e nome confirmado)
            dados['nome_lead'] = f'{conversa[0][0]} (nome no WhatsApp)'
    return dados, classificar(dados)


def _nome_arquivo(txt):
    txt = re.sub(r'[^\w\- ]', '', (txt or 'lead').strip(), flags=re.U)[:40].strip() or 'lead'
    return txt.replace(' ', '_')


def qualificar_arquivo(caminho, sem_ia=False, saida=None):
    print('\n=== SDR: QUALIFICACAO DO LEAD ===')
    texto = ler_conversa(caminho)
    if len(texto.strip()) < 30:
        raise SystemExit(f'ERRO: conversa vazia ou ilegivel ({caminho})')
    print(f'1. Conversa: {os.path.basename(caminho)} ({len(texto)} caracteres)')
    print('2. Qualificando...')
    dados, c = qualificar(texto, sem_ia)
    pasta = saida or ambiente.pasta_saida('sdr')
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_{_nome_arquivo(dados.get('nome_lead'))}")
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'arquivo': os.path.abspath(caminho), 'classificacao': c, 'dados': dados}, f, ensure_ascii=False, indent=1)
    texto_resumo = resumo_texto(dados, c)
    with open(base + ' - Resumo para o Closer.txt', 'w', encoding='utf-8') as f:
        f.write(texto_resumo)
    try:
        resumo_docx(dados, c, base + ' - Resumo para o Closer.docx')
    except Exception as e:  # o .txt ja basta; docx e conveniencia
        print(f'   aviso: docx nao gerado ({e})')
    print(f"3. {c['status']} | nota {c['nota']}/100 | urgencia {dados.get('urgencia')} | modo: {dados['_modo']}")
    print('\n' + texto_resumo)
    print(f'Arquivos: {base}.json | ... - Resumo para o Closer.txt/.docx')
    return base

"""
Motor de pecas da FASE JUDICIAL.

Para cada tipo de peca: esqueleto (BASE_CONHECIMENTO/ESQUELETOS) + DNA das pecas do escritorio +
dados do caso.json + texto dos documentos da pasta (cedulas, laudos, notificacao) e, conforme o tipo,
o documento-base (decisao, contestacao, execucao, recurso). A IA devolve o texto com marcacao simples;
o motor confere as citacoes contra o DNA, poe cabecalho/fecho fixos e gera .docx + .pdf no timbrado.

Nada e protocolado nem enviado. Toda peca sai com "PRONTA PARA REVISAO DO(A) ADVOGADO(A) RESPONSAVEL".
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402  (carrega .env e caminhos)
from datetime import date, datetime  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caso_judicial as cj  # noqa: E402
import conferencia  # noqa: E402
import formatar  # noqa: E402
from valores import brl, ler_valor, por_extenso  # noqa: E402
from CONTRATACAO.extrator import ler_arquivo  # noqa: E402
from config.escritorio import ESCRITORIO, OUTORGADOS  # noqa: E402
from docx_caldeira import docx_para_pdf  # noqa: E402

ESQUELETOS = os.path.join(ambiente.BASE_CONHECIMENTO, 'ESQUELETOS')

TITULO_INICIAL = ('AÇÃO MANDAMENTAL DE PRORROGAÇÃO COMPULSÓRIA DE DÍVIDA RURAL COM PEDIDO DE TUTELA '
                  'PROVISÓRIA ANTECIPADA EM CARÁTER DE URGÊNCIA')
TITULO_INICIAL_REVISIONAL = ('AÇÃO MANDAMENTAL DE PRORROGAÇÃO COMPULSÓRIA DE DÍVIDA RURAL C/C REVISÃO CONTRATUAL '
                             'E PEDIDO DE TUTELA PROVISÓRIA DE URGÊNCIA')

# perfil: 'inicial' = com laranja (como as iniciais do escritorio); 'sobrio' = tudo preto
# (replicas, embargos e contrarrazoes do escritorio sao pretas - DNA 8.1). Trocar aqui se o escritorio preferir.
TIPOS = {
    'inicial': {'nome': 'Petição Inicial - Ação Mandamental', 'arquivo': 'Inicial Mandamental',
                'esqueleto': 'INICIAL_MANDAMENTAL.md', 'perfil': 'inicial', 'esforco': 'high',
                'max_tokens': 128000, 'etapa': 'JUDICIAL - INICIAL EM REVISAO', 'valor_causa': 'soma'},
    'agravo': {'nome': 'Agravo de Instrumento (liminar negada)', 'arquivo': 'Agravo de Instrumento',
               'esqueleto': 'AGRAVO_INSTRUMENTO.md', 'perfil': 'sobrio', 'esforco': 'high', 'max_tokens': 96000,
               'etapa': 'JUDICIAL - AGRAVO EM REVISAO', 'rotulo_doc': 'DECISÃO AGRAVADA (liminar negada)'},
    'replica': {'nome': 'Impugnação/Réplica à Contestação', 'arquivo': 'Replica',
                'esqueleto': 'REPLICA.md', 'perfil': 'sobrio', 'esforco': 'high', 'max_tokens': 96000,
                'etapa': 'JUDICIAL - REPLICA EM REVISAO', 'rotulo_doc': 'CONTESTAÇÃO DO BANCO'},
    'embargos': {'nome': 'Embargos à Execução', 'arquivo': 'Embargos a Execucao',
                 'esqueleto': 'EMBARGOS_EXECUCAO.md', 'perfil': 'sobrio', 'esforco': 'high', 'max_tokens': 96000,
                 'etapa': 'JUDICIAL - EMBARGOS EM REVISAO', 'valor_causa': 'preencher',
                 'rotulo_doc': 'EXECUÇÃO DO BANCO (petição inicial, título e cálculo)'},
    'contrarrazoes': {'nome': 'Contrarrazões Recursais', 'arquivo': 'Contrarrazoes',
                      'esqueleto': 'CONTRARRAZOES.md', 'perfil': 'sobrio', 'esforco': 'high', 'max_tokens': 96000,
                      'etapa': 'JUDICIAL - CONTRARRAZOES EM REVISAO', 'rotulo_doc': 'RECURSO DO BANCO'},
    'manifestacao': {'nome': 'Manifestação / Petição de Andamento', 'arquivo': 'Manifestacao',
                     'esqueleto': 'MANIFESTACAO.md', 'perfil': 'sobrio', 'esforco': 'medium', 'max_tokens': 32000,
                     'etapa': None, 'rotulo_doc': 'DOCUMENTO DE REFERÊNCIA (intimação, despacho, comprovante)'},
}

FECHO_IA = re.compile(r'^(::\s*|@@\s*)?(termos em que|nestes termos|pede deferimento|requer (o )?deferimento|'
                      r'local e data|na data e hora|cacoal\s*[/-]|.*assinatura (digital|eletr)|augusto|lorena|'
                      r'oab/?\s*ro|assinaturas|revisao|pronta para revis|d[aá]-se [aà] causa|'
                      r'por fim, solicita que todas as intima|atribui-se [aà] causa|_{3,})', re.I)


# ============================================================
# BLOCOS FIXOS (o que nao pode depender da IA)
# ============================================================

def _feminino(q):
    """Genero pelo estado civil ("casada", "solteira"...). A nacionalidade nao serve: a IA grava "brasileira"."""
    ec = cj.norm(q.get('estado_civil'))
    if re.search(r'\b(casada|solteira|divorciada|viuva|separada|convivente)\b', ec):
        return True
    if re.search(r'\b(casado|solteiro|divorciado|viuvo|separado)\b', ec):
        return False
    return None


def qualificacao_autor(caso):
    q = dict(caso.get('qualificacao') or {})
    f = _feminino(q)
    nac = cj.norm(q.get('nacionalidade'))
    if nac in ('brasileira', 'brasileiro', 'brasil'):
        q['nacionalidade'] = 'brasileira' if f else ('brasileiro' if f is False else 'brasileiro(a)')
    v = lambda campo, rotulo: q.get(campo) or f'[PREENCHER {rotulo}]'  # noqa: E731
    nome = (q.get('nome') or '[PREENCHER nome completo]').upper()
    rg = f"{q['rg']} {q.get('orgao_emissor') or ''}".strip() if q.get('rg') else '[PREENCHER RG e órgão emissor]'
    end = ', '.join(x for x in (q.get('logradouro'), f"n° {q['numero']}" if q.get('numero') else '',
                                f"Bairro: {q['bairro']}" if q.get('bairro') else '') if x) or '[PREENCHER endereço]'
    cidade = f"{q['cidade']}/{q.get('uf') or '[PREENCHER UF]'}" if q.get('cidade') else '[PREENCHER município/UF]'
    cep = f", CEP {q['cep']}" if q.get('cep') else ''
    g = lambda masc, fem: fem if f else (masc if f is False else f'{masc}(a)')  # noqa: E731
    return (f"^^{nome}^^, {v('nacionalidade', 'nacionalidade')}, {v('estado_civil', 'estado civil')}, "
            f"{v('profissao', 'profissão')}, maior e capaz, devidamente {g('inscrito', 'inscrita')} no CPF "
            f"sob o n. {v('cpf', 'CPF')}, {g('portador', 'portadora')} da cédula de identidade n° {rg}, "
            f"residente e {g('domiciliado', 'domiciliada')} na {end}, município de {cidade}{cep}, "
            f"vem por meio de seus advogados subscritos propor:")


def comarca_sugerida(caso):
    q = caso.get('qualificacao') or {}
    if q.get('cidade') and (q.get('uf') or '').upper() in ('RO', ''):
        return q['cidade'].upper()
    mun = ((caso.get('triagem') or {}).get('atividade_rural') or {}).get('municipio_propriedade')
    return mun.upper() if mun else '[PREENCHER COMARCA]'


def enderecamento_inicial(caso, federal):
    if federal:
        return ('EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DA __ VARA FEDERAL CÍVEL DA SUBSEÇÃO JUDICIÁRIA DE JI-PARANÁ-RO. '
                '[CONFERIR foro: réu Caixa = Justiça Federal; ver conexão com ação anterior]')
    return (f'EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DA __ VARA CÍVEL DA COMARCA DE {comarca_sugerida(caso)} – ESTADO DE '
            'RONDÔNIA [CONFERIR foro: domicílio do produtor ou agência do banco; decisão do Coordenador]')


def valor_da_causa(caso, banco):
    """Soma das dividas discutidas com o banco. Retorna (valor|None, texto_da_frase, observacao)."""
    ops = cj.operacoes_do_banco(caso, banco) if banco else cj.operacoes(caso)
    soma, faltando, aproximado = 0.0, [], False
    for o in ops:
        v, aprox = ler_valor(o.get('valor'))
        if v is None:
            faltando.append(o.get('instrumento') or o.get('banco') or 'operação')
        else:
            soma += v
            aproximado = aproximado or aprox or 'aprox' in cj.norm(o.get('observacao'))
    if not ops or faltando:
        obs = (f'parcial com valores conhecidos: {brl(soma)}; sem valor: {", ".join(faltando)}' if soma else
               'nenhuma operação com valor no caso')
        return None, (f'Dá-se à causa o valor de [PREENCHER valor da causa = soma das dívidas discutidas ({obs})].'), obs
    frase = f'Dá-se à causa o valor de ^^{brl(soma)}^^ ({por_extenso(soma)}).'
    if aproximado:
        frase += ' [CONFERIR: soma de valores ditos na reunião como aproximados; usar o valor/saldo das cédulas]'
    return soma, frase, 'aproximado' if aproximado else ''


def frase_intimacoes():
    nomes = [f"{a['nome']}, {a['oab']}" for a in OUTORGADOS]
    lista = nomes[0] if len(nomes) == 1 else ', '.join(nomes[:-1]) + ' e ' + nomes[-1]
    plural = len(nomes) > 1
    return ('Por fim, solicita que todas as intimações deste processo sejam realizadas, necessariamente, em nome '
            f"{'dos seguintes advogados' if plural else 'do seguinte advogado'}, sob pena de nulidade processual: "
            f'{lista}.')


def fecho(tipo, frase_valor=None):
    linhas = ['', frase_intimacoes()]
    if frase_valor:
        linhas += ['', frase_valor]
    linhas += ['', '@@REVISAO', '', ':: Termos em que, pede deferimento.', '',
               ':: Local e data certificados digitalmente.', '', '@@ASSINATURAS']
    return '\n'.join(linhas)


# ============================================================
# PROMPT
# ============================================================

MARCACAO = """FORMATO DE SAÍDA (marcação simples; uma instrução por linha; nada de Markdown além disto):
!! TEXTO        endereçamento (em caixa alta)
== TEXTO        nome da peça/ação, centralizado
# TEXTO         título de seção (ex.: # I. DA GRATUIDADE DE JUSTIÇA)
## TEXTO        subtítulo (ex.: ## 1) DAS CIRCUNSTÂNCIAS NATURAIS ADVERSAS EM RONDÔNIA)
### TEXTO       sub-subtítulo (ex.: ### a) Estiagem severa e déficit hídrico)
> TEXTO         citação de lei, ementa ou decisão (uma linha por parágrafo citado)
- TEXTO         item de lista
| a | b |       tabela (primeira linha = cabeçalho)
@@ TEXTO        legenda de imagem centralizada (ex.: @@ [PREENCHER: IMAGEM 01 – DECRETO ... colar imagem])
linha comum     parágrafo do corpo (cada parágrafo numa linha; linha em branco entre parágrafos)
No meio do texto: **negrito**, ^^NOME DA PARTE ou VALOR^^ (destaque do escritório), *itálico* (latim, "in verbis").
Pendências: [PREENCHER o que falta] e [CONFERIR: motivo] (saem em vermelho e travam o protocolo)."""


def _sistema(tipo):
    cfg = TIPOS[tipo]
    e = ESCRITORIO
    with open(os.path.join(ESQUELETOS, cfg['esqueleto']), encoding='utf-8') as f:
        esqueleto = f.read()
    dna = ambiente.ler_base('DNA_PECAS.md')
    return f"""Você é advogado(a) redator(a) sênior do {e['nome']} ({e['cidade']}/{e['uf']}), escritório de defesa do produtor rural contra bancos e cooperativas de crédito (prorrogação e alongamento compulsório de dívida rural, tutela de urgência, embargos). Você escreve a MINUTA da peça "{cfg['nome']}", que o(a) advogado(a) responsável e o Coordenador Jurídico vão revisar. A IA nunca protocola.

REGRAS INEGOCIÁVEIS
1. Fatos, nomes, números, datas, valores, cédulas, áreas, rebanho, eventos: SOMENTE dos DADOS DO CASO e dos DOCUMENTOS enviados. Faltou: [PREENCHER descrição do que falta]. Aproximado, duvidoso ou contraditório entre fontes: [CONFERIR: motivo].
2. Jurisprudência, súmulas, decisões-paradigma e ementas: SOMENTE as que estão no DNA DAS PEÇAS abaixo, com número, órgão, relator e data exatamente como o DNA traz; transcreva ementa só quando o DNA traz o texto. Não cite julgado de memória nem "Tema" numerado. Onde o DNA marca [CONFERIR] ou aponta divergência, reproduza a marca [CONFERIR: ...] na peça.
3. Legislação (CF, CPC, CC, CDC, Lei 4.829/65, DL 167/67, Lei 8.171/91, Lei 9.138/95, MCR): cite artigos que você conhece com segurança; transcrição literal só do que está no DNA ou de texto legal de que tenha certeza.
4. Fatos regionais (decretos, arroba, incêndios, IDARON, enchentes): só como o DNA traz e só quando batem com o período e a atividade do cliente. Lavoura e pecuária não se misturam (erro do DNA §10).
5. Os nomes de clientes de casos anteriores que aparecem no DNA NUNCA entram na peça. As decisões-paradigma entram só pelo número e trecho que o DNA lista. O banco/cooperativa réu é o informado nos parâmetros: nunca troque o nome da instituição (erro do DNA §10).
6. Estilo do escritório (DNA §8): enfático e protetivo do produtor, frases de efeito do DNA, partes pelo polo ("o Autor", "o Requerido", "a Instituição Financeira", "o Embargante", "o Agravante"), terceira pessoa, português jurídico correto, parágrafos completos. Nada de conversa com o leitor, nada de nota da IA dentro da peça além das marcas [PREENCHER]/[CONFERIR].
7. Siga o ESQUELETO na ordem. Linhas entre {{{{ }}}} do esqueleto são instruções: siga, nunca copie. Tópico que não se aplica ao caso: omita e renumere. Não escreva o que o esqueleto diz que o sistema insere (cabeçalho fixo da inicial, intimações, valor da causa, aviso de revisão, fecho, local/data, assinaturas).
8. Extensão: completa e densa como as peças do escritório, sem enchimento e sem repetir parágrafos.

{MARCACAO}

Responda SOMENTE com o texto da peça nesse formato, sem comentários antes ou depois e sem bloco de código.

<dna_das_pecas_do_escritorio>
{dna}
</dna_das_pecas_do_escritorio>

<esqueleto tipo="{tipo}">
{esqueleto}
</esqueleto>
"""


def _dados_caso(caso, banco, tipo):
    t = caso.get('triagem') or {}
    fora = ('telefone', 'email', 'origem', 'indicante')  # nao entram na peca: nao vao para a IA
    q = {k: v for k, v in (caso.get('qualificacao') or {}).items() if not k.startswith('_') and v and k not in fora}
    ops = cj.operacoes_do_banco(caso, banco) if (banco and tipo == 'inicial') else cj.operacoes(caso)
    return {
        'cliente': q,
        'data_do_contrato_com_o_escritorio': caso.get('data_contrato_br'),
        'resumo_do_caso': t.get('resumo_caso'),
        'atividade_rural': t.get('atividade_rural'),
        'operacoes' + ('_com_o_reu' if tipo == 'inicial' and banco else ''): ops,
        'outras_operacoes_de_outros_bancos': [o.get('banco') for o in cj.operacoes(caso)
                                               if banco and not cj.mesmo_banco(o.get('banco') or '', banco)],
        'linha_do_tempo': t.get('linha_do_tempo'),
        'gatilhos': t.get('gatilhos'),
        'riscos_apontados_na_triagem': t.get('riscos'),
        'estrategia_candidata_da_triagem': t.get('estrategia_candidata'),
        'trechos_da_reuniao': t.get('trechos'),
        'notificacao_extrajudicial': [r for r in cj.extrajudicial(caso)
                                      if not banco or cj.mesmo_banco(r.get('banco') or '', banco)],
        'prazos_internos': caso.get('prazos'),
        'pecas_judiciais_ja_geradas': [{k: p.get(k) for k in ('tipo', 'banco', 'gerada_em')}
                                       for p in caso.get('judicial') or []],
        'checklist_pre_protocolo': (caso.get('judicial_checklist') or {}).get('pendencias'),
    }


def _documentos_da_pasta(base, caso, banco, tipo, docs):
    """Texto dos documentos relevantes da pasta, por tipo de peca."""
    partes = []
    laudos = [d for d in docs if cj.eh_laudo_safra(d) or cj.eh_laudo_financeiro(d)]
    extra = [d for d in docs if d.pasta == cj.EXTRAJUDICIAL
             and (not banco or cj.banco_no_texto(banco, d.nome, curto=True) or cj.banco_no_texto(banco, d.texto[:3000]))]
    transc = [d for d in docs if d.pasta == cj.CONTRATACAO and 'transcri' in d.nome.lower()]
    if tipo == 'inicial':
        ced = cj.cedulas_do_banco(docs, banco) if banco else [d for d in docs if cj.eh_cedula(d)]
        partes.append(cj.ler_textos(ced, 25000, 60000, 'CÉDULA/CONTRATO: '))
        partes.append(cj.ler_textos(laudos, 40000, 70000, 'LAUDO: '))
        partes.append(cj.ler_textos(extra, 15000, 30000, 'EXTRAJUDICIAL: '))
        partes.append(cj.ler_textos(transc, 30000, 30000, 'REUNIÃO DE FECHAMENTO: '))
    else:
        partes.append(cj.ler_textos(laudos, 15000, 30000, 'LAUDO: '))
        if tipo == 'embargos':
            ced = cj.cedulas_do_banco(docs, banco) if banco else [d for d in docs if cj.eh_cedula(d)]
            partes.append(cj.ler_textos(ced, 15000, 30000, 'CÉDULA/CONTRATO: '))
        inicial = next((p for p in reversed(caso.get('judicial') or []) if p.get('tipo') == 'inicial'
                        and os.path.exists(p.get('arquivo') or '')), None)
        if inicial:
            partes.append(f"\n--- MINUTA DA INICIAL DO ESCRITÓRIO ({os.path.basename(inicial['arquivo'])}; "
                          f"conferir se foi a versão protocolada) ---\n{ler_arquivo(inicial['arquivo'])[:40000]}\n")
    return ''.join(p for p in partes if p.strip())


# ============================================================
# POS-PROCESSAMENTO
# ============================================================

def _limpar(texto, tipo, titulo_fixo=None):
    linhas = [l.rstrip() for l in texto.replace('\r\n', '\n').split('\n') if not l.strip().startswith('```')]
    # a inicial ja tem enderecamento, qualificacao do autor e titulo escritos pelo sistema
    if tipo == 'inicial':
        while linhas and (not linhas[0].strip() or linhas[0].lstrip().startswith(('!!', '==')) or
                          'EXCELENT' in linhas[0].upper() or 'vem por meio de seus advogados' in linhas[0] or
                          (titulo_fixo and cj.norm(linhas[0]) == cj.norm(titulo_fixo))):
            linhas.pop(0)
    # fecho, intimacoes, valor da causa e assinaturas sao do sistema
    while linhas and (not linhas[-1].strip() or FECHO_IA.match(linhas[-1].strip())):
        linhas.pop()
    texto = '\n'.join(linhas)
    texto = re.sub(r'\{\{.*?\}\}', '', texto)  # instrucao de esqueleto copiada
    return re.sub(r'\n{3,}', '\n\n', texto).strip()


def _nome_saida(base, caso, tipo, banco):
    b = re.sub(r'[<>:"/\\|?*]', '', banco or '').strip()
    b = f' - {b[:40]}' if b else ''
    nome = f"{cj.nome_arquivo(caso)} - {TIPOS[tipo]['arquivo']}{b} - {date.today():%d-%m-%Y}"
    pasta = cj.pasta_judicial(base)
    if os.path.exists(os.path.join(pasta, nome + '.docx')):
        nome += f' {datetime.now():%Hh%M}'
    return os.path.join(pasta, nome + '.docx')


def renderizar(caminho_md, saida_docx=None):
    """Refaz o .docx (e o PDF) a partir do texto marcado salvo em 20 JUDICIAL/_texto_ia."""
    with open(caminho_md, encoding='utf-8') as f:
        texto = f.read()
    meta = dict(re.findall(r'(\w+)=([^\s]+)', texto.split('\n', 1)[0])) if texto.startswith('%%') else {}
    saida = saida_docx or meta.get('docx', '').replace('|', ' ') or os.path.splitext(caminho_md)[0] + '.docx'
    pend = formatar.montar_docx(texto, saida, meta.get('perfil', 'inicial'))
    pdf = docx_para_pdf(saida)
    return saida, pdf, pend


# ============================================================
# GERACAO
# ============================================================

def gerar(tipo, pasta, banco=None, documento=None, instrucao=None, revisional=False, federal=False, simular=False,
          resposta=None):
    """resposta: caminho de uma 'resposta bruta da IA.txt' ja salva -> reprocessa sem nova chamada de IA."""
    cfg = TIPOS[tipo]
    base, caso = cj.abrir(pasta)
    print(f"\n=== {cfg['nome'].upper()}: {cj.nome_cliente(caso)} ===")

    # documento-base (contestacao, decisao, execucao, recurso)
    texto_doc = ''
    if documento:
        documento = os.path.abspath(documento.strip().strip('"'))
        if not os.path.exists(documento):
            raise SystemExit(f'ERRO: arquivo nao encontrado: {documento}')
        texto_doc = ler_arquivo(documento)
        if len(texto_doc.strip()) < 200:
            raise SystemExit(f'ERRO: nao consegui ler o texto de {os.path.basename(documento)} '
                             '(PDF escaneado? instalar o Tesseract para OCR).')
        if not os.path.abspath(documento).startswith(os.path.abspath(base)):
            destino = os.path.join(cj.pasta_judicial(base), os.path.basename(documento))
            if not os.path.exists(destino):
                shutil.copy2(documento, destino)
                print(f'   Documento-base copiado para 20 JUDICIAL: {os.path.basename(documento)}')

    # banco (uma acao por banco)
    if tipo == 'inicial':
        banco = cj.escolher_banco(caso, banco)
        if not banco:
            print('   AVISO: caso sem operacoes; o reu fica [PREENCHER].')
    elif banco:
        banco = cj.escolher_banco(caso, banco)
    else:
        lista = cj.bancos(caso)
        no_doc = [b for b in lista if texto_doc and cj.banco_no_texto(b, texto_doc[:20000])]
        banco = lista[0] if len(lista) == 1 else (no_doc[0] if len(no_doc) == 1 else '')
    federal = bool(federal or (banco and cj.eh_caixa(banco)))
    print(f"   Banco: {banco or '[a IA tira do documento]'} | Foro: {'FEDERAL' if federal else 'ESTADUAL'}"
          + (' | c/c REVISIONAL' if revisional else ''))

    docs = cj.inventario(base)
    print(f'   Lendo documentos da pasta ({len(docs)} arquivo(s))...')
    textos_pasta = _documentos_da_pasta(base, caso, banco, tipo, docs)

    # blocos fixos
    cabecalho, frase_valor, valor = '', None, None
    titulo_fixo = TITULO_INICIAL_REVISIONAL if revisional else TITULO_INICIAL
    parametros = [f'Tipo de peça: {cfg["nome"]}', f'Banco/cooperativa réu: {banco or "[tirar do documento]"}',
                  f"Foro: {'Justiça Federal (réu Caixa Econômica Federal)' if federal else 'Justiça Estadual de Rondônia'}",
                  f"Pedido de revisão contratual (c/c revisional): {'SIM' if revisional else 'NÃO'}",
                  f'Data de hoje: {date.today():%d/%m/%Y}']
    if tipo == 'inicial':
        valor, frase_valor, obs_valor = valor_da_causa(caso, banco)
        cabecalho = '\n'.join(['!! ' + enderecamento_inicial(caso, federal), '', qualificacao_autor(caso), '',
                               '== ' + titulo_fixo, ''])
        if valor:
            custas = valor * 0.02
            parametros.append(f'Valor da causa (soma das operações com o réu): {brl(valor)} ({por_extenso(valor)})'
                              + (' [valores aproximados: marcar CONFERIR onde usar]' if obs_valor else ''))
            parametros.append(f'Custas iniciais de 2% sobre o valor da causa: {brl(custas)} ({por_extenso(custas)})')
        else:
            parametros.append(f'Valor da causa: [PREENCHER] ({obs_valor}); custas de 2%: [PREENCHER]')
        parametros.append('O sistema já escreveu o endereçamento, a qualificação do autor e o título. '
                          'Comece pela qualificação do réu.')
    elif tipo == 'agravo':
        tribunal = ('TRIBUNAL REGIONAL FEDERAL DA 1ª REGIÃO' if federal
                    else 'TRIBUNAL DE JUSTIÇA DO ESTADO DE RONDÔNIA')
        parametros.append(f'Tribunal do agravo: {tribunal}')
    if cfg.get('valor_causa') == 'preencher':
        frase_valor = ('Dá-se à causa o valor de [PREENCHER valor da causa: valor executado ou do excesso '
                       'impugnado, conforme o art. 292 do CPC].')

    conteudo = '<parametros>\n' + '\n'.join(parametros) + '\n</parametros>\n\n'
    conteudo += ('<dados_do_caso>\n' + json.dumps(_dados_caso(caso, banco, tipo), ensure_ascii=False, indent=1)
                 + '\n</dados_do_caso>\n\n')
    if textos_pasta:
        conteudo += f'<documentos_da_pasta_do_cliente>\n{textos_pasta}\n</documentos_da_pasta_do_cliente>\n\n'
    if texto_doc:
        conteudo += (f"<documento_base tipo=\"{cfg.get('rotulo_doc', 'DOCUMENTO')}\" "
                     f"arquivo=\"{os.path.basename(documento)}\">\n{texto_doc[:150000]}\n</documento_base>\n\n")
    if instrucao:
        conteudo += f'<instrucao_do_advogado>\n{instrucao}\n</instrucao_do_advogado>\n\n'
    conteudo += f"Escreva agora a minuta completa da peça \"{cfg['nome']}\", seguindo o esqueleto e as regras."

    sistema = _sistema(tipo)
    saida = _nome_saida(base, caso, tipo, banco)
    pasta_txt = cj.pasta_judicial(base, cj.TEXTO_IA)
    base_md = os.path.join(pasta_txt, os.path.splitext(os.path.basename(saida))[0])
    if simular:
        with open(base_md + ' - PROMPT.txt', 'w', encoding='utf-8') as f:
            f.write(f'=== SISTEMA ===\n{sistema}\n\n=== CONTEUDO ===\n{conteudo}')
        print(f'   SIMULACAO: prompt salvo em {base_md} - PROMPT.txt ({len(sistema) + len(conteudo):,} caracteres). '
              'Nenhuma chamada de IA.')
        return None

    if resposta:
        with open(resposta, encoding='utf-8') as f:
            bruto = f.read()
        print(f'   Reprocessando a resposta já salva ({os.path.basename(resposta)}), sem nova chamada de IA.')
    else:
        print(f"   IA: escrevendo a minuta ({len(sistema) + len(conteudo):,} caracteres de entrada; "
              'pode levar alguns minutos)...')
        import ia  # so importa quando vai chamar (precisa da ANTHROPIC_API_KEY)
        bruto = ia.texto_longo(sistema, conteudo, max_tokens=cfg['max_tokens'], esforco=cfg['esforco'])
        with open(base_md + ' - resposta bruta da IA.txt', 'w', encoding='utf-8') as f:
            f.write(bruto)

    corpo = _limpar(bruto, tipo, titulo_fixo)
    referencias = [texto_doc, textos_pasta, json.dumps(caso, ensure_ascii=False), instrucao or '']
    corpo, avisos = conferencia.conferir(corpo, ambiente.ler_base('DNA_PECAS.md'), *referencias)
    final = (f"%% tipo={tipo} perfil={cfg['perfil']} banco={(banco or '-').replace(' ', '_')} "
             f"docx={saida.replace(' ', '|')}\n" + cabecalho + '\n' + corpo + '\n' + fecho(tipo, frase_valor) + '\n')
    caminho_md = base_md + '.md'
    with open(caminho_md, 'w', encoding='utf-8') as f:
        f.write(final)

    pend = formatar.montar_docx(final, saida, cfg['perfil'])
    pdf = docx_para_pdf(saida)
    cj.registrar_peca(base, tipo, saida, banco, pdf, cfg['etapa'], {
        'texto_marcado': caminho_md, 'pendencias': len(pend), 'citacoes_marcadas': len(avisos),
        'documento_base': documento, 'revisional': revisional, 'federal': federal})

    print(f'\n   OK  {saida}')
    print(f"   PDF {pdf or '(não gerado: instalar Word ou LibreOffice)'}")
    print(f'   Pendências em vermelho ([PREENCHER]/[CONFERIR]): {len(pend)}')
    if avisos:
        print(f'   Citações/pontos marcados pela conferência com o DNA: {len(avisos)}')
        for a in avisos[:12]:
            print(f'     - {a}')
    print('   PRONTA PARA REVISÃO DO(A) ADVOGADO(A) RESPONSÁVEL. A IA não protocola.')
    return {'docx': saida, 'pdf': pdf, 'texto': caminho_md, 'pendencias': pend, 'avisos': avisos}

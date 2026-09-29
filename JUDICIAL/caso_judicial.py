"""
Leitura da pasta do cliente para a FASE JUDICIAL: caso.json, operacoes por banco,
inventario dos documentos (cedulas, laudos, notificacoes, respostas) e registro das pecas.

A pasta e a criada pela fase de contratacao (CONTRATACAO/pasta_cliente.py):
    NOME DO CLIENTE/00 CONTRATACAO/caso.json, DOCUMENTOS DO CLIENTE/..., 10 EXTRAJUDICIAL/, 20 JUDICIAL/
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime  # noqa: E402

from CONTRATACAO import pasta_cliente  # noqa: E402
from CONTRATACAO.extrator import ler_arquivo  # noqa: E402
from config.escritorio import SUBPASTAS_CLIENTE  # noqa: E402

CONTRATACAO = SUBPASTAS_CLIENTE[0]
EXTRAJUDICIAL = next((s for s in SUBPASTAS_CLIENTE if 'EXTRAJUDICIAL' in s.upper()), '10 EXTRAJUDICIAL')
JUDICIAL = next((s for s in SUBPASTAS_CLIENTE if 'JUDICIAL' in s.upper() and 'EXTRA' not in s.upper()), '20 JUDICIAL')
TEXTO_IA = '_texto_ia'   # subpasta de 20 JUDICIAL com o texto marcado de cada peca (para refazer o .docx)

# palavras que nao identificam banco nenhum
GENERICAS = {'banco', 'bco', 'cooperativa', 'coop', 'de', 'do', 'da', 'dos', 'das', 'credito', 'e', 'sa', 's',
             'a', 'ltda', 'livre', 'admissao', 'associados', 'investimento', 'interacao', 'solidaria',
             'agencia', 'ag', 'sistema', 'central'}
PALAVRAS_CEDULA = ('cedula', 'ccr', 'ccb', 'cpr', 'nota de credito', 'ncr', 'contrato', 'aditivo', 'renegocia',
                   'repactua', 'financiamento')


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9$ ]+', ' ', sem_acento(str(s or '')).lower())).strip()


# ============================================================
# CASO
# ============================================================

def abrir(pasta):
    """Aceita a pasta do cliente (ou uma subpasta dela, ou o caso.json). Retorna (base, caso)."""
    base = os.path.abspath(pasta.strip().strip('"'))
    if os.path.isfile(base):
        base = os.path.dirname(base)
    if os.path.basename(base).upper() in [s.upper() for s in SUBPASTAS_CLIENTE]:
        base = os.path.dirname(base)
    caso = pasta_cliente.ler_caso(base)
    if not caso:
        raise SystemExit(f'ERRO: nao achei {CONTRATACAO}/caso.json em "{base}". '
                         'A pasta precisa ter passado pela fase de contratacao.')
    os.makedirs(os.path.join(base, JUDICIAL), exist_ok=True)
    return base, caso


def pasta_judicial(base, *partes):
    caminho = os.path.join(base, JUDICIAL, *partes)
    os.makedirs(caminho, exist_ok=True)
    return caminho


def nome_cliente(caso):
    return ((caso.get('qualificacao') or {}).get('nome') or '').strip()


def nome_arquivo(caso):
    return pasta_cliente.nome_pasta(nome_cliente(caso)).title()


def registrar(base, alteracao):
    """Rele o caso.json na hora de gravar (outro modulo pode ter mexido) e aplica a alteracao."""
    caso = pasta_cliente.ler_caso(base)
    alteracao(caso)
    pasta_cliente.salvar_caso(base, caso)
    return caso


def registrar_peca(base, tipo, arquivo, banco='', pdf=None, etapa=None, extra=None):
    item = {'tipo': tipo, 'arquivo': arquivo, 'pdf': pdf, 'banco': banco,
            'gerada_em': datetime.now().isoformat(timespec='seconds')}
    item.update(extra or {})

    def alt(caso):
        caso.setdefault('judicial', []).append(item)
        if etapa:
            caso['etapa'] = etapa
    return registrar(base, alt)


# ============================================================
# OPERACOES E BANCOS
# ============================================================

def operacoes(caso):
    """Operacoes do caso: a lista conferida (se algum modulo gravou 'operacoes') ou a da triagem."""
    ops = caso.get('operacoes') or (caso.get('triagem') or {}).get('operacoes') or []
    return [o for o in ops if isinstance(o, dict)]


# bancos cujo nome tem palavra comum demais para buscar sozinha ("brasil", "amazonia", "caixa")
APELIDOS = {
    'banco do brasil': ['banco do brasil', 'bb'],
    'caixa economica': ['caixa economica', 'cef'],
    'banco da amazonia': ['banco da amazonia', 'basa'],
    'banco do nordeste': ['banco do nordeste', 'bnb'],
}
# marcas de cooperativa: "Sicoob Credip" e "Sicoob Amazonia" sao credores diferentes
MARCAS = {'sicoob', 'sicredi', 'cresol', 'unicred', 'uniprime', 'ailos'}


def tokens_banco(nome):
    return [t for t in norm(nome).split() if t not in GENERICAS and len(t) > 2]


def chave_banco(nome):
    n = norm(nome)
    if n in ('caixa', 'a caixa'):
        return 'caixa economica'
    for chave, apelidos in APELIDOS.items():
        if chave in n or n in apelidos:
            return chave
    toks = tokens_banco(nome)
    return ' '.join([t for t in toks if t in MARCAS] + [t for t in toks if t not in MARCAS]) or n


def mesmo_banco(a, b):
    ka, kb = chave_banco(a), chave_banco(b)
    if ka == kb:
        return True
    if ka in APELIDOS or kb in APELIDOS:
        return False
    ta, tb = set(ka.split()), set(kb.split())
    if ta & MARCAS != tb & MARCAS:
        return False
    ra, rb = ta - MARCAS, tb - MARCAS
    return True if not ra or not rb else bool(ra & rb)


def termos_banco(banco):
    k = chave_banco(banco)
    if k in APELIDOS:
        return APELIDOS[k]
    toks = k.split()
    return [t for t in toks if t not in MARCAS] or toks


def banco_no_texto(banco, texto, curto=False):
    """O banco aparece no texto? Apelido curto (bb, cef, basa) so vale com curto=True (nome de arquivo)."""
    alvo = ' ' + norm(texto) + ' '
    for termo in termos_banco(banco):
        if len(termo) <= 4 and not curto and termo not in MARCAS:
            continue
        if f' {termo} ' in alvo:
            return True
    return False


def bancos(caso):
    vistos = []
    for o in operacoes(caso):
        b = (o.get('banco') or '').strip()
        if b and not any(mesmo_banco(b, v) for v in vistos):
            vistos.append(b)
    return vistos


def operacoes_do_banco(caso, banco):
    return [o for o in operacoes(caso) if mesmo_banco(o.get('banco') or '', banco)]


def escolher_banco(caso, banco=None):
    """Banco da peca: o informado em --banco ou, se o caso so tem um, esse. Senao, erro com a lista."""
    lista = bancos(caso)
    if banco:
        for b in lista:
            if mesmo_banco(b, banco):
                return b
        print(f'   AVISO: "{banco}" nao aparece nas operacoes do caso ({", ".join(lista) or "nenhuma"}). '
              'Seguindo com o nome informado.')
        return banco
    lista = [b for b in lista if not eh_nao_bancario(b)]
    if len(lista) == 1:
        return lista[0]
    if not lista:
        return ''
    raise SystemExit('ERRO: o caso tem mais de um banco. Uma acao por banco. Informe --banco com um destes: '
                     + '; '.join(lista))


NAO_BANCARIO = ('nao instituicao financeira', 'nao e banco', 'nao e instituicao', 'cerealista', 'trading',
                'revenda', 'fornecedor', 'armazem', 'agroindustria', 'frigorifico')


def eh_nao_bancario(nome):
    """Credor que nao e banco/cooperativa de credito (CPR com cerealista, revenda de insumos): fora da mandamental."""
    n = norm(nome)
    return any(k in n for k in NAO_BANCARIO)


def eh_caixa(banco):
    n = norm(banco)
    return n in ('cef', 'caixa') or ('caixa' in n and ('economica' in n or 'federal' in n))


def extrajudicial(caso):
    """Lista {banco, enviada_em, resposta, ...} gravada pelo modulo extrajudicial (se existir)."""
    dados = caso.get('extrajudicial') or []
    if isinstance(dados, dict):
        dados = dados.get('notificacoes') or dados.get('lista') or [dados]
    return [d for d in dados if isinstance(d, dict)]


# ============================================================
# DOCUMENTOS DA PASTA
# ============================================================

class Documento:
    def __init__(self, base, caminho):
        self.caminho = caminho
        self.rel = os.path.relpath(caminho, base)
        self.nome = os.path.basename(caminho)
        self.pasta = self.rel.split(os.sep)[0]
        self.subpasta = os.path.basename(os.path.dirname(caminho))
        self._texto = None

    @property
    def texto(self):
        if self._texto is None:
            self._texto = ler_arquivo(self.caminho) or ''
        return self._texto

    def alvo(self, com_texto=True, limite=4000):
        """Nome + subpasta + inicio do texto, normalizados, para reconhecer o documento."""
        txt = self.texto[:limite] if com_texto else ''
        return norm(f'{self.subpasta} {self.nome} {txt}')


def inventario(base):
    docs = []
    for raiz, pastas, arquivos in os.walk(base):
        pastas[:] = [p for p in pastas if not p.startswith('_')]
        for a in sorted(arquivos):
            if a.startswith('~$') or not a.lower().endswith(pasta_cliente.EXTENSOES_DOC):
                continue
            if a.lower() == 'caso.json':
                continue
            docs.append(Documento(base, os.path.join(raiz, a)))
    return docs


def _tem(alvo, *palavras):
    return any(p in alvo for p in palavras)


def eh_laudo_financeiro(doc):
    n = norm(doc.nome + ' ' + doc.subpasta)
    if _tem(n, 'laudo', 'parecer') and _tem(n, 'financeir', 'capacidade', 'contab', 'pagamento'):
        return True
    t = norm(doc.texto[:3000])
    return _tem(n, 'laudo', 'parecer') and _tem(t, 'capacidade de pagamento', 'parecer tecnico financeiro',
                                                 'laudo financeiro', 'estimativa de pagamento')


def eh_laudo_safra(doc):
    if eh_laudo_financeiro(doc):
        return False
    n = norm(doc.nome + ' ' + doc.subpasta)
    if _tem(n, 'laudo', 'declaracao de perda', 'parecer tecnico agr', 'vistoria') and \
            _tem(n, 'safra', 'agrari', 'agronom', 'frustra', 'perda', 'climat', 'estiagem', 'tecnico'):
        return True
    t = norm(doc.texto[:3000])
    return _tem(n, 'laudo') and _tem(t, 'frustracao de safra', 'laudo agrario', 'laudo agronomico',
                                      'perda de safra', 'deficit hidrico')


def tem_art(doc):
    t = doc.texto
    return bool(re.search(r'anota[cç][aã]o de responsabilidade t[eé]cnica|\bART\s*(n[º°o.]|\d)', t, re.I)) or \
        bool(re.search(r'(^|[\s_\-])ART([\s_\-.]|$)', doc.nome))


def tem_vistoria(doc):
    return bool(re.search(r'vistoria|in loco|visita t[eé]cnica|visita (?:a|à) propriedade', doc.texto, re.I))


def tem_crea(doc):
    return bool(re.search(r'\bCREA\b', doc.texto))


GERADOS_PELO_ESCRITORIO = ('honorario', 'procura', 'declara', 'relatorio', 'triagem', 'notifica', 'checklist',
                           'resumo', 'mensagem', 'transcri', 'laudo', 'parecer')


def eh_cedula(doc):
    """Cedula/contrato do banco: so o que veio do cliente/banco, nunca documento gerado pelo escritorio."""
    if doc.pasta != pasta_cliente.DOCS:
        return False
    n = norm(doc.nome)
    if _tem(n, *GERADOS_PELO_ESCRITORIO):
        return False
    return doc.subpasta.upper().startswith('03') or _tem(n, *PALAVRAS_CEDULA)


def cedulas_do_banco(docs, banco):
    achados = []
    for d in docs:
        if not eh_cedula(d):
            continue
        if banco_no_texto(banco, d.nome, curto=True) or banco_no_texto(banco, d.texto[:6000]):
            achados.append(d)
    return achados


def ler_textos(docs, limite_por_doc=30000, limite_total=120000, rotulo=''):
    """Junta o texto de varios documentos para mandar a IA (com limite)."""
    partes, total = [], 0
    for d in docs:
        t = (d.texto or '').strip()
        if not t:
            partes.append(f'\n--- {rotulo}{d.rel}: [sem texto legivel - arquivo escaneado sem OCR?] ---\n')
            continue
        t = t[:limite_por_doc]
        if total + len(t) > limite_total:
            partes.append(f'\n--- {rotulo}{d.rel}: [nao enviado, limite de texto atingido] ---\n')
            continue
        partes.append(f'\n--- {rotulo}{d.rel} ---\n{t}\n')
        total += len(t)
    return ''.join(partes)

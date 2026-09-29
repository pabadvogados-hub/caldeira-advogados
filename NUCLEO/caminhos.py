"""
Caminhos de arquivo gravados no caso.json, portaveis entre Windows e Mac.

O mesmo caso e aberto de maquinas diferentes, cada uma vendo a pasta do servidor de um jeito:
    Windows: Z:\\CLIENTES\\AGRONEGOCIO\\FULANO\\00 CONTRATACAO\\contrato.docx
             \\\\SERVIDOR\\CLIENTES\\AGRONEGOCIO\\FULANO\\00 CONTRATACAO\\contrato.docx
    Mac:     /Volumes/CLIENTES/AGRONEGOCIO/FULANO/00 CONTRATACAO/contrato.docx

Por isso o caso.json guarda o caminho RELATIVO a pasta do cliente, sempre com "/":
    "00 CONTRATACAO/contrato.docx"
(o relativo tambem sobrevive quando a pasta e movida para o ARQUIVO na finalizacao).

    relativo(base, caminho)   para GRAVAR
    resolver(base, caminho)   para LER: aceita o relativo novo e o absoluto antigo. Absoluto que
                              nao existe nesta maquina (gravado em outra) e remontado a partir da
                              subpasta conhecida do cliente (00 CONTRATACAO, DOCUMENTOS DO CLIENTE,
                              10 EXTRAJUDICIAL, 20 JUDICIAL) debaixo da base atual. Aceita \\ e /.
    caso_para_gravar(base, caso) / caso_lido(base, caso)
                              aplicam as duas regras em todos os caminhos do caso.json
                              (usados por CONTRATACAO/pasta_cliente.py: salvar_caso / ler_caso).
    pasta_do_cliente(caminho) acha a pasta do cliente gravada em outra maquina (relatorios em SAIDA/).
    base_do_arquivo(caminho)  pasta do cliente que contem um arquivo (sobe ate a subpasta conhecida).

Em memoria os modulos continuam trabalhando com caminho absoluto desta maquina.
"""
import copy
import os
import re
import unicodedata

SUBPASTAS_PADRAO = ('00 CONTRATACAO', 'DOCUMENTOS DO CLIENTE', '10 EXTRAJUDICIAL', '20 JUDICIAL')
PASTA_AREA_PADRAO = 'AGRONEGOCIO'

# C:\ , C:/ , \\SERVIDOR\ , //SERVIDOR/  (absoluto do Windows, reconhecido em qualquer sistema)
_ABSOLUTO_WINDOWS = re.compile(r'^(?:[A-Za-z]:[\\/]|\\\\|//)')
_MAX_TAMANHO = 1000   # texto longo nao e caminho


def _config():
    try:
        from config.escritorio import PASTA_AREA, SUBPASTAS_CLIENTE
        return list(SUBPASTAS_CLIENTE), PASTA_AREA
    except Exception:  # noqa: BLE001 - funciona mesmo sem o config no sys.path
        return list(SUBPASTAS_PADRAO), PASTA_AREA_PADRAO


def subpastas_conhecidas():
    subs, _ = _config()
    return tuple(dict.fromkeys(s.upper() for s in subs + list(SUBPASTAS_PADRAO)))


def _nfc(texto):
    # o Mac pode devolver nome de arquivo com acento decomposto (NFD); grava sempre composto
    return unicodedata.normalize('NFC', texto)


def partes(caminho):
    """Pedacos do caminho, aceitando \\ e / misturados."""
    return [p for p in re.split(r'[\\/]+', caminho or '') if p]


def eh_absoluto(caminho):
    """Absoluto de QUALQUER sistema (Z:\\..., \\\\SERVIDOR\\..., /Volumes/...), nao so do atual."""
    c = (caminho or '').strip()
    return bool(_ABSOLUTO_WINDOWS.match(c)) or c.startswith(('/', '\\')) or os.path.isabs(c)


def _indice_subpasta(ps):
    conhecidas = subpastas_conhecidas()
    for i, p in enumerate(ps):
        if p.upper() in conhecidas:
            return i
    return None


def _parece_texto(valor):
    return '\n' in valor or len(valor) > _MAX_TAMANHO


def relativo(base, caminho):
    """Caminho para gravar no caso.json: relativo a pasta do cliente, com "/".
    Arquivo fora da pasta do cliente (ex.: Downloads) continua absoluto. None/'' voltam como vieram."""
    if not caminho or not isinstance(caminho, str):
        return caminho
    c = caminho.strip()
    if not eh_absoluto(c):
        return _nfc('/'.join(partes(c)))
    # 1) absoluto desta maquina dentro da base atual
    if base and os.path.isabs(c):
        try:
            rel = os.path.relpath(os.path.abspath(c), os.path.abspath(base))
        except ValueError:   # Windows: drives diferentes
            rel = None
        if rel and rel != '.' and not rel.startswith('..') and not os.path.isabs(rel):
            return _nfc('/'.join(partes(rel)))
    # 2) absoluto de outra maquina: a partir da subpasta conhecida do cliente
    ps = partes(c)
    i = _indice_subpasta(ps)
    if i is not None:
        return _nfc('/'.join(ps[i:]))
    return caminho


def resolver(base, caminho):
    """Caminho para usar nesta maquina. Aceita relativo (novo) e absoluto (antigo, de qualquer sistema)."""
    if not caminho or not isinstance(caminho, str):
        return caminho
    c = caminho.strip()
    if not eh_absoluto(c):
        return os.path.join(base, *partes(c)) if base else c
    if os.path.isabs(c) and os.path.exists(c):
        return c
    ps = partes(c)
    i = _indice_subpasta(ps)
    if base and i is not None:
        return os.path.join(base, *ps[i:])
    return c


def _relativo_gravavel(valor):
    """True se o texto e um caminho relativo que comeca numa subpasta do cliente ("00 CONTRATACAO/x.docx")."""
    ps = partes(valor)
    return len(ps) >= 2 and not eh_absoluto(valor) and _indice_subpasta(ps) == 0


def _percorrer(obj, funcao):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _percorrer(v, funcao)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _percorrer(v, funcao)
        return obj
    if isinstance(obj, str) and obj and not _parece_texto(obj):
        return funcao(obj)
    return obj


def caso_para_gravar(base, caso):
    """Copia do caso com os caminhos da pasta do cliente em relativo (o dict original nao muda)."""
    def trocar(valor):
        if not eh_absoluto(valor):
            return valor
        rel = relativo(base, valor)
        return rel if rel is not valor and _relativo_gravavel(rel) else valor
    return _percorrer(copy.deepcopy(caso), trocar)


def caso_lido(base, caso):
    """Resolve (no proprio dict) os caminhos do caso.json para esta maquina. Aceita casos antigos."""
    def trocar(valor):
        if eh_absoluto(valor):
            return resolver(base, valor) if _indice_subpasta(partes(valor)) is not None else valor
        if _relativo_gravavel(valor):
            return resolver(base, valor)
        return valor
    return _percorrer(caso, trocar)


def base_do_arquivo(caminho):
    """Pasta do cliente que contem este arquivo (sobe ate a subpasta conhecida). None se nao achar."""
    atual = os.path.dirname(os.path.abspath(caminho))
    conhecidas = subpastas_conhecidas()
    while True:
        pai = os.path.dirname(atual)
        if os.path.basename(atual).upper() in conhecidas:
            return pai
        if not pai or pai == atual:
            return None
        atual = pai


def pasta_do_cliente(caminho, raiz_clientes=None):
    """Pasta do cliente gravada em outra maquina (ex.: Z:\\CLIENTES\\AGRONEGOCIO\\FULANO lida no Mac):
    se nao existir aqui, remonta a partir de AGRONEGOCIO/FULANO debaixo da PASTA_CLIENTES_RAIZ desta maquina."""
    if not caminho or not isinstance(caminho, str) or (os.path.isabs(caminho) and os.path.isdir(caminho)):
        return caminho
    raiz = raiz_clientes or os.getenv('PASTA_CLIENTES_RAIZ')
    if not raiz:
        return caminho
    _, area = _config()
    ps = partes(caminho)
    for i, p in enumerate(ps):
        if p.upper() == area.upper() and i + 1 < len(ps):
            return os.path.join(raiz, *ps[i:])
    return caminho

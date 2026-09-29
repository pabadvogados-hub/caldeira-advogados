"""
Pasta do cliente no servidor do escritorio (ou numa pasta sincronizada do Drive).

RAIZ/AGRONEGOCIO/NOME DO CLIENTE/
    00 CONTRATACAO/            relatorio de triagem, contrato, procuracao, declaracao, caso.json
    DOCUMENTOS DO CLIENTE/     uma subpasta por item do checklist
    10 EXTRAJUDICIAL/          notificacoes e respostas dos bancos
    20 JUDICIAL/               inicial, decisoes

A raiz vem de PASTA_CLIENTES_RAIZ no config/.env de CADA maquina:
    Windows: Z:\\CLIENTES  ou  \\\\SERVIDOR\\CLIENTES
    Mac:     /Volumes/CLIENTES  (depois de conectar em smb://SERVIDOR/CLIENTES pelo Finder)
O caso.json grava os caminhos relativos a pasta do cliente (NUCLEO/caminhos.py), entao o mesmo caso
abre nos dois sistemas.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
import caminhos  # noqa: E402  (caminho relativo no caso.json: Windows e Mac)
import unicodedata
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from config.escritorio import CHECKLIST_DOCUMENTOS, PASTA_AREA, SUBPASTAS_CLIENTE  # noqa: E402

DOCS = 'DOCUMENTOS DO CLIENTE'
CONTRATACAO = SUBPASTAS_CLIENTE[0]
EXTENSOES_DOC = ('.pdf', '.txt', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.docx', '.doc', '.xlsx', '.xls', '.tif', '.tiff')


def _sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def nome_pasta(nome):
    limpo = re.sub(r'\[[^\]]*\]', '', nome or '').strip()
    limpo = re.sub(r'[<>:"/\\|?*]', '', limpo)
    return re.sub(r'\s+', ' ', limpo).upper() or 'CLIENTE SEM NOME'


def raiz_clientes():
    return os.getenv('PASTA_CLIENTES_RAIZ') or os.path.join(RAIZ, 'CLIENTES')


def criar(nome):
    base = os.path.join(raiz_clientes(), PASTA_AREA, nome_pasta(nome))
    for sub in SUBPASTAS_CLIENTE:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    for item in CHECKLIST_DOCUMENTOS:
        if item.get('pasta') and item['pasta'] != CONTRATACAO:
            os.makedirs(os.path.join(base, DOCS, item['pasta']), exist_ok=True)
    return base


def classificar_arquivo(nome_arquivo, texto=''):
    """Descobre a qual item do checklist o arquivo pertence (pelo nome e pelo inicio do texto)."""
    alvo = _sem_acento((nome_arquivo + ' ' + (texto or '')[:1500]).lower())
    melhor, pontos = None, 0
    for item in CHECKLIST_DOCUMENTOS:
        if not item.get('pasta'):
            continue
        p = sum(alvo.count(_sem_acento(k)) for k in item['palavras'])
        # o nome do arquivo pesa mais que o texto
        p += 3 * sum(_sem_acento(k) in _sem_acento(nome_arquivo.lower()) for k in item['palavras'])
        if p > pontos:
            melhor, pontos = item, p
    return melhor


def guardar_documento(base, caminho, texto=''):
    item = classificar_arquivo(os.path.basename(caminho), texto)
    destino_dir = os.path.join(base, DOCS, item['pasta']) if item and item['pasta'] != CONTRATACAO \
        else os.path.join(base, DOCS)
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, os.path.basename(caminho))
    if os.path.abspath(caminho) != os.path.abspath(destino):
        shutil.copy2(caminho, destino)
    return item['id'] if item else None, destino


def arquivos_por_item(base):
    """Lista o que ja esta em cada subpasta do checklist."""
    saida = {}
    for item in CHECKLIST_DOCUMENTOS:
        if not item.get('pasta'):
            continue
        pasta = os.path.join(base, item['pasta'] if item['pasta'] == CONTRATACAO else os.path.join(DOCS, item['pasta']))
        if not os.path.isdir(pasta):
            continue
        achados = []
        for f in sorted(os.listdir(pasta)):
            if not f.lower().endswith(EXTENSOES_DOC):
                continue
            # na pasta de contratacao so conta a procuracao ASSINADA
            if item['pasta'] == CONTRATACAO and not ('procura' in f.lower() and 'assinad' in f.lower()):
                continue
            achados.append(f)
        if achados:
            saida[item['id']] = achados
    return saida


# ============================================================
# ESTADO DO CASO (caso.json)
# ============================================================

def caminho_caso(base):
    return os.path.join(base, CONTRATACAO, 'caso.json')


def ler_caso(base):
    """Le o caso.json e resolve os caminhos de arquivo para esta maquina (Windows ou Mac).
    Aceita caso antigo com caminho absoluto de outra maquina (NUCLEO/caminhos.py)."""
    try:
        with open(caminho_caso(base), encoding='utf-8') as f:
            caso = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return caminhos.caso_lido(os.path.abspath(base), caso) if isinstance(caso, dict) else {}


def salvar_caso(base, caso):
    """Grava o caso.json com os caminhos RELATIVOS a pasta do cliente (com "/"), para abrir igual no
    Windows (Z:\\CLIENTES) e no Mac (/Volumes/CLIENTES). O dict em memoria continua com o absoluto."""
    caso['atualizado_em'] = datetime.now().isoformat(timespec='seconds')
    with open(caminho_caso(base), 'w', encoding='utf-8') as f:
        json.dump(caminhos.caso_para_gravar(os.path.abspath(base), caso), f, ensure_ascii=False, indent=2)


def listar_casos():
    area = os.path.join(raiz_clientes(), PASTA_AREA)
    if not os.path.isdir(area):
        return []
    casos = []
    for nome in sorted(os.listdir(area)):
        base = os.path.join(area, nome)
        caso = ler_caso(base)
        if caso:
            casos.append((base, caso))
    return casos

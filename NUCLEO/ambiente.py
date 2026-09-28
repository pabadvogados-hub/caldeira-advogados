"""
Arranque comum de todos os modulos:

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
    import ambiente          # carrega config/.env e poe NUCLEO, INTEGRACOES e a raiz no sys.path

Depois disso funcionam: `from config.escritorio import ...`, `from docx_caldeira import ...`,
`import ia`, `from advbox_integration import ...` etc.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUCLEO = os.path.join(RAIZ, 'NUCLEO')
INTEGRACOES = os.path.join(RAIZ, 'INTEGRACOES')
BASE_CONHECIMENTO = os.path.join(RAIZ, 'BASE_CONHECIMENTO')
SAIDA = os.path.join(RAIZ, 'SAIDA')   # relatorios gerados (nao versionado)

for caminho in (RAIZ, NUCLEO, INTEGRACOES):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(RAIZ, 'config', '.env'))
except ImportError:
    pass


def tem_credencial(var):
    """True se a variavel do .env esta preenchida de verdade."""
    v = os.getenv(var, '')
    return bool(v) and not v.startswith('SEU') and 'AQUI' not in v.upper()


def ler_base(nome_arquivo):
    """Texto de um arquivo de BASE_CONHECIMENTO (ex.: 'DNA_PECAS.md'), ou '' se nao existir."""
    caminho = os.path.join(BASE_CONHECIMENTO, nome_arquivo)
    if os.path.exists(caminho):
        with open(caminho, encoding='utf-8') as f:
            return f.read()
    return ''


def pasta_saida(*partes):
    caminho = os.path.join(SAIDA, *partes)
    os.makedirs(caminho, exist_ok=True)
    return caminho

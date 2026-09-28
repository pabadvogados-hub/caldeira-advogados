"""
Integracao unificada com Atende Direito - CRM WhatsApp.

Funcoes disponiveis:
  Baixo nivel:
    get_headers() / _headers()
    normalizar_telefone(tel)
    variantes_telefone(tel)

  Contatos:
    buscar_contato_por_telefone(telefone) -> subscriber dict | None
    listar_subscribers(page=1, limit=100) -> (list, has_next)
    extrair_user_ns(contato) -> str | None

  Envio:
    enviar_mensagem_texto(user_ns, mensagem) -> bool
    enviar_arquivo(user_ns, url_arquivo, legenda, tipo) -> bool
    enviar_arquivo_por_telefone(telefone, url_arquivo, legenda, tipo) -> (ok, contato)
    enviar_texto_por_telefone(telefone, mensagem) -> (ok, contato)
    disparar_flow(user_ns, flow_name) -> bool

  Wrappers:
    enviar_mensagem_contratacao(telefone, nome_cliente, links_assinatura) -> bool

Endpoints:
  GET  /api/subscribers?page=N&limit=100
  POST /api/subscriber/send-text
  POST /api/subscriber/send-content
  POST /api/subscriber/send-sub-flow-by-flow-name

Auth: Bearer token ATENDE_DIREITO_TOKEN (.env).
"""
import os
import logging
import requests

log = logging.getLogger('integracoes.atendedireito')

BASE_URL = 'https://app.atendedireito.com.br/api'

# Nome do escritorio usado em assinaturas de mensagens (configuravel via .env)
NOME_ESCRITORIO = os.getenv('NOME_ESCRITORIO', 'Caldeira Advogados Associados')


# ============================================================
# BAIXO NIVEL
# ============================================================

def get_headers():
    """Retorna headers Bearer. None se token ausente."""
    token = os.getenv('ATENDE_DIREITO_TOKEN')
    if not token:
        log.warning('ATENDE_DIREITO_TOKEN ausente no .env')
        return None
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# Alias historico
def _headers():
    return get_headers()


def normalizar_telefone(tel):
    """So digitos, sem DDI 55 inicial."""
    if not tel:
        return ''
    d = ''.join(c for c in str(tel) if c.isdigit())
    if d.startswith('55') and len(d) > 11:
        d = d[2:]
    return d


def _normalizar_telefone(tel):
    return normalizar_telefone(tel)


def variantes_telefone(tel):
    """Gera set com variantes com/sem o 9 do celular (compat cadastros antigos)."""
    d = normalizar_telefone(tel)
    variantes = {d}
    if len(d) == 11 and d[2] == '9':
        variantes.add(d[:2] + d[3:])
    elif len(d) == 10:
        variantes.add(d[:2] + '9' + d[2:])
    return variantes


def _variantes_telefone(tel):
    return variantes_telefone(tel)


def extrair_user_ns(contato):
    """Dado um subscriber dict, retorna o user_ns pronto pra enviar msg."""
    if not isinstance(contato, dict):
        return None
    return contato.get('user_ns') or contato.get('subscriber_ns')


# ============================================================
# CONTATOS
# ============================================================

def listar_subscribers(page=1, limit=100):
    """Retorna (lista_subs, has_next). Tolera falhas de rede (retorna [], False)."""
    headers = get_headers()
    if not headers:
        return [], False
    try:
        r = requests.get(f'{BASE_URL}/subscribers?page={page}&limit={limit}',
                         headers=headers, timeout=30)
    except Exception as e:
        log.warning(f'listar_subscribers pagina {page}: {e}')
        return [], False
    if r.status_code != 200:
        return [], False
    data = r.json() or {}
    subs = data.get('data') or []
    has_next = len(subs) >= limit
    return subs, has_next


def buscar_contato_por_telefone(telefone, max_paginas=50):
    """
    Varre subscribers procurando telefone (em todas as variantes).
    Retorna o subscriber dict completo, ou None.
    """
    vars_set = variantes_telefone(telefone)
    if not vars_set:
        return None

    page = 1
    while page <= max_paginas:
        subs, has_next = listar_subscribers(page=page)
        if not subs:
            return None
        for sub in subs:
            sub_digits = normalizar_telefone(sub.get('phone', '') or '')
            if sub_digits and sub_digits in vars_set:
                return sub
        if not has_next:
            return None
        page += 1
    return None


# ============================================================
# ENVIO DE MENSAGENS
# ============================================================

def enviar_mensagem_texto(user_ns, mensagem):
    """Envia texto puro para um subscriber."""
    headers = get_headers()
    if not headers:
        return False
    payload = {'user_ns': user_ns, 'content': mensagem}
    try:
        r = requests.post(f'{BASE_URL}/subscriber/send-text',
                          headers=headers, json=payload, timeout=30)
    except Exception as e:
        log.warning(f'send-text erro: {e}')
        return False
    if r.status_code in (200, 201):
        return True
    log.warning(f'send-text {r.status_code}: {r.text[:200]}')
    return False


def enviar_arquivo(user_ns, url_arquivo, legenda=None, tipo='file'):
    """
    Envia arquivo via /subscriber/send-content.

    tipo: 'file' (PDF/DOC), 'image', 'video', 'audio'
    url_arquivo: URL publica (HTTP/HTTPS) do arquivo
    legenda: texto opcional precedendo o arquivo
    """
    headers = get_headers()
    if not headers:
        return False

    mensagens = []
    if legenda:
        mensagens.append({'type': 'text', 'text': legenda})
    mensagens.append({'type': tipo, 'url': url_arquivo})

    payload = {
        'user_ns': user_ns,
        'data': {
            'version': 'v1',
            'content': {'messages': mensagens},
        },
    }
    try:
        r = requests.post(f'{BASE_URL}/subscriber/send-content',
                          headers=headers, json=payload, timeout=60)
    except Exception as e:
        log.warning(f'send-content erro: {e}')
        return False
    if r.status_code in (200, 201):
        return True
    log.warning(f'send-content {r.status_code}: {r.text[:300]}')
    return False


def disparar_flow(user_ns, flow_name):
    """
    Dispara um sub-flow (automation) pro subscriber pelo nome do flow.
    Endpoint: POST /subscriber/send-sub-flow-by-flow-name
    """
    headers = get_headers()
    if not headers:
        return False
    payload = {'user_ns': user_ns, 'flow_name': flow_name}
    try:
        r = requests.post(f'{BASE_URL}/subscriber/send-sub-flow-by-flow-name',
                          headers=headers, json=payload, timeout=30)
    except Exception as e:
        log.warning(f'disparar_flow erro: {e}')
        return False
    if r.status_code in (200, 201):
        return True
    log.warning(f'disparar_flow {r.status_code}: {r.text[:200]}')
    return False


# ============================================================
# WRAPPERS POR TELEFONE (busca contato + envia)
# ============================================================

def enviar_texto_por_telefone(telefone, mensagem):
    """Busca contato pelo telefone e envia texto. Retorna (ok, contato|None)."""
    contato = buscar_contato_por_telefone(telefone)
    if not contato:
        return False, None
    user_ns = extrair_user_ns(contato)
    if not user_ns:
        return False, contato
    return enviar_mensagem_texto(user_ns, mensagem), contato


def enviar_arquivo_por_telefone(telefone, url_arquivo, legenda=None, tipo='file'):
    """Busca contato pelo telefone e envia arquivo. Retorna (ok, contato|None)."""
    contato = buscar_contato_por_telefone(telefone)
    if not contato:
        return False, None
    user_ns = extrair_user_ns(contato)
    if not user_ns:
        return False, contato
    return enviar_arquivo(user_ns, url_arquivo, legenda=legenda, tipo=tipo), contato


# ============================================================
# COMPAT: wrapper historico de mensagem de contratacao
# ============================================================

def enviar_mensagem_contratacao(telefone, nome_cliente, links_assinatura):
    """Mensagem padrao pos-intake com links ZapSign. Retorna bool."""
    headers = get_headers()
    if not headers:
        print('   AVISO: Atende Direito nao configurado, pulando envio')
        return False

    print(f'   Buscando contato: {telefone}...')
    contato = buscar_contato_por_telefone(telefone)
    if not contato:
        print(f'   AVISO: Contato {telefone} nao encontrado')
        return False

    user_ns = extrair_user_ns(contato)
    nome_contato = contato.get('first_name', nome_cliente)
    print(f'   Contato encontrado: {contato.get("name", "")} ({user_ns})')

    links_texto = ''
    for link in links_assinatura:
        doc = link.get('documento', '')
        signatario = link.get('signatario', '')
        url = link.get('link', '')
        if nome_cliente.lower() in signatario.lower():
            if 'Contrato' in doc:
                links_texto += f'\n*Contrato de Honorarios:*\n{url}\n'
            elif 'Procuracao' in doc:
                links_texto += f'\n*Procuracao:*\n{url}\n'
            elif 'Declaracao' in doc:
                links_texto += f'\n*Declaracao de Hipossuficiencia:*\n{url}\n'

    mensagem = f"""Prezado(a) {nome_contato},

Os documentos necessarios relativos a fase de contratacao, como contrato de honorarios, procuracao e declaracao de hipossuficiencia, foram elaborados.

Seguem os links para assinatura digital:
{links_texto}
Assim que tiver assinado, damos prosseguimento no seu caso. Quanto mais rapido assinar, mais rapido sera dado entrada no seu processo.

Estamos a disposicao para qualquer duvida.

{NOME_ESCRITORIO}"""
    print('   Enviando mensagem via WhatsApp...')
    ok = enviar_mensagem_texto(user_ns, mensagem)
    print('   Mensagem enviada!' if ok else '   ERRO ao enviar')
    return ok

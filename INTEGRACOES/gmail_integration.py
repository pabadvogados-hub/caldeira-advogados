"""
Integracao com o Gmail do escritorio - SOMENTE RASCUNHO.

Cria o rascunho (users.drafts.create) da notificacao extrajudicial com o PDF anexo e o
e-mail do banco como destinatario. O advogado abre o Gmail, revisa e clica em Enviar.
Este modulo NAO tem funcao de envio e nunca deve ganhar uma.

Credenciais (nunca versionar):
  config/credentials_gmail.json   cliente OAuth "App para computador" do Google Cloud do escritorio
  config/token_gmail.json         criado sozinho na 1a autorizacao
Caminhos alternativos: GMAIL_CREDENCIAIS e GMAIL_TOKEN no config/.env.

Primeira vez (abre o navegador para o login na conta do escritorio):
  python INTEGRACOES/gmail_integration.py autorizar

Escopo: gmail.compose (criar e ler rascunhos). Nao le a caixa de entrada.
"""
import base64
import mimetypes
import os
import sys
from email.message import EmailMessage
from email.utils import formataddr

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
LIMITE_ANEXOS_MB = 20   # o Gmail recusa mensagens acima de ~25 MB


def _caminho(var, padrao):
    return os.getenv(var) or os.path.join(RAIZ, 'config', padrao)


def arquivo_credenciais():
    return _caminho('GMAIL_CREDENCIAIS', 'credentials_gmail.json')


def arquivo_token():
    return _caminho('GMAIL_TOKEN', 'token_gmail.json')


def configurado():
    """True se ha como autenticar (token ja salvo ou cliente OAuth para o 1o login)."""
    return os.path.exists(arquivo_token()) or os.path.exists(arquivo_credenciais())


def _credenciais(permitir_login=True):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if os.path.exists(arquivo_token()):
        creds = Credentials.from_authorized_user_file(arquivo_token(), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not permitir_login:
            raise RuntimeError('Gmail sem token valido. Rode: python INTEGRACOES/gmail_integration.py autorizar')
        if not os.path.exists(arquivo_credenciais()):
            raise RuntimeError(f'Falta {arquivo_credenciais()} (cliente OAuth do Google Cloud do escritorio).')
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(arquivo_credenciais(), SCOPES)
        creds = flow.run_local_server(port=0)
    with open(arquivo_token(), 'w', encoding='utf-8') as f:
        f.write(creds.to_json())
    return creds


def _servico(permitir_login=True):
    from googleapiclient.discovery import build
    return build('gmail', 'v1', credentials=_credenciais(permitir_login), cache_discovery=False)


def conta():
    """E-mail da conta autorizada."""
    return _servico().users().getProfile(userId='me').execute().get('emailAddress')


def _lista(valor):
    if not valor:
        return []
    if isinstance(valor, str):
        valor = valor.replace(';', ',').split(',')
    return [v.strip() for v in valor if v and v.strip()]


def montar_mensagem(para, assunto, corpo, anexos=None, cc=None, nome_remetente=None, remetente=None):
    msg = EmailMessage()
    msg['To'] = ', '.join(_lista(para))
    if _lista(cc):
        msg['Cc'] = ', '.join(_lista(cc))
    if remetente:
        msg['From'] = formataddr((nome_remetente or '', remetente))
    msg['Subject'] = assunto
    msg.set_content(corpo)
    total = 0
    for caminho in anexos or []:
        tamanho = os.path.getsize(caminho)
        total += tamanho
        if total > LIMITE_ANEXOS_MB * 1024 * 1024:
            raise RuntimeError(f'Anexos passam de {LIMITE_ANEXOS_MB} MB. Anexe o restante manualmente no Gmail.')
        tipo, _ = mimetypes.guess_type(caminho)
        principal, sub = (tipo or 'application/octet-stream').split('/', 1)
        with open(caminho, 'rb') as f:
            msg.add_attachment(f.read(), maintype=principal, subtype=sub, filename=os.path.basename(caminho))
    return msg


def criar_rascunho(para, assunto, corpo, anexos=None, cc=None, nome_remetente=None):
    """Cria o rascunho na conta autorizada. Retorna {'id', 'message_id'}. NAO ENVIA."""
    if not _lista(para):
        raise ValueError('Rascunho sem destinatario.')
    msg = montar_mensagem(para, assunto, corpo, anexos, cc, nome_remetente)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = _servico().users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
    return {'id': draft.get('id'), 'message_id': (draft.get('message') or {}).get('id')}


def rascunho_existe(draft_id):
    """True se o rascunho ainda esta no Gmail; False se sumiu (enviado ou apagado); None se nao deu para ver."""
    if not draft_id or not configurado():
        return None
    try:
        from googleapiclient.errors import HttpError
        try:
            _servico(permitir_login=False).users().drafts().get(userId='me', id=draft_id, format='minimal').execute()
            return True
        except HttpError as e:
            if getattr(e, 'status_code', None) == 404 or '404' in str(e):
                return False
            return None
    except Exception:
        return None


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'autorizar':
        print('Abrindo o navegador para autorizar o Gmail do escritorio (somente rascunhos)...')
        print('Conta autorizada:', conta())
        print('Token salvo em', arquivo_token())
    else:
        print('Uso: python INTEGRACOES/gmail_integration.py autorizar')
        print('Configurado:', configurado(), '| credenciais:', arquivo_credenciais())

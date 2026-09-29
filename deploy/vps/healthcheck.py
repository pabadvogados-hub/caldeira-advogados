"""
Healthcheck do sistema: credenciais, API do Claude, ADVBOX, Asaas, ZapSign, Atende Direito,
pasta de clientes e disco. Se algo CAIR, avisa por WhatsApp o numero de ALERTA_WHATSAPP.

  python deploy/vps/healthcheck.py                confere tudo e avisa se algo caiu
  python deploy/vps/healthcheck.py --sem-aviso    so mostra (nao manda WhatsApp)
  python deploy/vps/healthcheck.py --falha NOME   avisa que a rotina NOME falhou
                                                  (chamado pelo systemd, caldeira-alerta@.service)

Regras:
- credencial VAZIA = modulo em modo seguro: aparece no relatorio, nao e "queda" e nao gera aviso
- credencial preenchida e servico sem responder = QUEDA -> WhatsApp (1 aviso por problema a cada
  6 horas) e um aviso de "voltou ao normal" quando resolver
- se o proprio Atende Direito cair, o aviso fica em logs/healthcheck_alertas.log
- nunca mostra o valor de nenhuma credencial; as consultas sao so leitura e nao custam tokens
Roda em Windows (Agendador, 1x ao dia) e na VPS (systemd, de hora em hora).
"""
import argparse
import json
import os
import shutil
import socket
import sys
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, 'NUCLEO'))
import ambiente  # noqa: E402  (carrega config/.env e caminhos)

import requests  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

LOGS = os.path.join(RAIZ, 'logs')
ESTADO = os.path.join(LOGS, 'healthcheck_estado.json')
ALERTAS = os.path.join(LOGS, 'healthcheck_alertas.log')
REPETIR_APOS = timedelta(hours=6)
DISCO_MINIMO_GB = 2
UA = 'CALDEIRA_ADVOGADOS-Advocacia/1.0'


def _get(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        return 'FALHA', f'sem conexao ({type(e).__name__})'
    if r.status_code == 200:
        return 'OK', 'respondeu'
    if r.status_code in (401, 403):
        return 'FALHA', f'credencial recusada (HTTP {r.status_code})'
    return 'FALHA', f'HTTP {r.status_code}'


def _servico(var, url, headers_fn):
    if not ambiente.tem_credencial(var):
        return 'VAZIO', f'{var} nao preenchida (modo seguro)'
    return _get(url, headers_fn(os.getenv(var)))


def checar():
    """Lista de (nome, status, detalhe). status: OK, VAZIO ou FALHA."""
    r = [
        ('API do Claude', *_servico('ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1/models?limit=1',
                                    lambda t: {'x-api-key': t, 'anthropic-version': '2023-06-01'})),
        ('ADVBOX', *_servico('ADVBOX_API_TOKEN', 'https://app.advbox.com.br/api/v1/settings',
                             lambda t: {'Authorization': f'Bearer {t}', 'Accept': 'application/json',
                                        'User-Agent': UA})),
        ('Asaas', *_servico('ASAAS_API_TOKEN', 'https://api.asaas.com/v3/finance/balance',
                            lambda t: {'access_token': t, 'User-Agent': UA})),
        ('ZapSign', *_servico('ZAPSIGN_API_TOKEN', 'https://api.zapsign.com.br/api/v1/docs/?page=1',
                              lambda t: {'Authorization': f'Bearer {t}'})),
        ('Atende Direito', *_servico('ATENDE_DIREITO_TOKEN',
                                     'https://app.atendedireito.com.br/api/subscribers?page=1&limit=1',
                                     lambda t: {'Authorization': f'Bearer {t}'})),
    ]
    pasta = os.getenv('PASTA_CLIENTES_RAIZ', '')
    if not pasta:
        r.append(('Pasta de clientes', 'VAZIO', 'PASTA_CLIENTES_RAIZ nao preenchida'))
    elif os.path.isdir(pasta):
        r.append(('Pasta de clientes', 'OK', 'acessivel'))
    else:
        r.append(('Pasta de clientes', 'FALHA', 'PASTA_CLIENTES_RAIZ nao encontrada (servidor/Drive desconectado?)'))
    livre = shutil.disk_usage(RAIZ).free / 1024 ** 3
    r.append(('Disco', 'OK' if livre >= DISCO_MINIMO_GB else 'FALHA', f'{livre:.1f} GB livres'))
    return r


# ============================================================
# AVISOS
# ============================================================

def _ler_estado():
    try:
        with open(ESTADO, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _salvar_estado(estado):
    os.makedirs(LOGS, exist_ok=True)
    with open(ESTADO, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)


def _registrar(texto):
    os.makedirs(LOGS, exist_ok=True)
    with open(ALERTAS, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] {texto}\n")


def avisar(texto):
    """WhatsApp para ALERTA_WHATSAPP pelo Atende Direito; sempre registra em logs/."""
    _registrar(texto.replace('\n', ' | '))
    numero = os.getenv('ALERTA_WHATSAPP', '')
    if not numero:
        print('   (sem ALERTA_WHATSAPP no .env: aviso so em logs/healthcheck_alertas.log)')
        return False
    if not ambiente.tem_credencial('ATENDE_DIREITO_TOKEN'):
        print('   (sem ATENDE_DIREITO_TOKEN: aviso so em logs/healthcheck_alertas.log)')
        return False
    try:
        from atendedireito_integration import enviar_texto_por_telefone
        ok, _ = enviar_texto_por_telefone(numero, texto)
    except Exception as e:  # noqa: BLE001
        print(f'   aviso nao enviado: {e}')
        return False
    print('   aviso enviado por WhatsApp' if ok else '   aviso NAO enviado (numero nao achado no Atende Direito?)')
    return ok


def _cabecalho():
    return f"[Sistema Caldeira - {socket.gethostname()} - {datetime.now().strftime('%d/%m %H:%M')}]"


def tratar_resultado(resultado, sem_aviso=False):
    estado = _ler_estado()
    agora = datetime.now()
    quedas = {nome: det for nome, st, det in resultado if st == 'FALHA'}
    novos = []
    for nome, det in quedas.items():
        ultimo = estado.get(nome)
        if not ultimo or agora - datetime.fromisoformat(ultimo) >= REPETIR_APOS:
            novos.append(f'- {nome}: {det}')
            estado[nome] = agora.isoformat(timespec='seconds')
    voltaram = [n for n in list(estado) if not n.startswith('rotina:') and n not in quedas]
    for n in voltaram:
        estado.pop(n)
    if sem_aviso:
        return
    if novos:
        avisar(f'{_cabecalho()}\nProblema nas integracoes:\n' + '\n'.join(novos) +
               '\nAs rotinas que dependem disso ficam paradas ate resolver.')
    if voltaram:
        avisar(f"{_cabecalho()}\nVoltou ao normal: {', '.join(voltaram)}.")
    if novos or voltaram or quedas:
        _salvar_estado(estado)


def falha_de_rotina(nome):
    estado = _ler_estado()
    chave = f'rotina:{nome}'
    ultimo = estado.get(chave)
    if ultimo and datetime.now() - datetime.fromisoformat(ultimo) < REPETIR_APOS:
        print(f'Falha de {nome} ja avisada ha menos de 6 horas.')
        return
    estado[chave] = datetime.now().isoformat(timespec='seconds')
    _salvar_estado(estado)
    log = nome.replace('caldeira-', '').replace('.service', '').replace('-', '_')
    avisar(f'{_cabecalho()}\nA rotina automatica "{nome}" falhou.\n'
           f'Ver o log: logs/{log}.log na pasta do sistema (VPS: /opt/caldeira/app/logs/) '
           f'e "systemctl status {nome}".')


def main():
    ap = argparse.ArgumentParser(description='Healthcheck - Caldeira Advogados Associados')
    ap.add_argument('--sem-aviso', action='store_true', help='so mostra, nao manda WhatsApp')
    ap.add_argument('--falha', metavar='NOME', help='avisa que a rotina NOME falhou')
    args = ap.parse_args()
    if args.falha:
        falha_de_rotina(args.falha)
        return 0
    print(f"HEALTHCHECK - {socket.gethostname()} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    resultado = checar()
    for nome, st, det in resultado:
        print(f'  {st:6} {nome:18} {det}')
    tratar_resultado(resultado, args.sem_aviso)
    return 1 if any(st == 'FALHA' for _, st, _ in resultado) else 0


if __name__ == '__main__':
    sys.exit(main())

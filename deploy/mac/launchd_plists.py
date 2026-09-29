"""
Gera e descreve os agentes do launchd (Mac) das rotinas automaticas. So biblioteca padrao.
Chamado por deploy/mac/agendar_tarefas_mac.sh, que tem a TABELA das rotinas (mesma agenda do
deploy/agendar_tarefas_windows.bat).

    python3 launchd_plists.py gerar  --pasta PASTA_DO_SISTEMA --destino ~/Library/LaunchAgents < tabela
    python3 launchd_plists.py listar --destino ~/Library/LaunchAgents
    python3 launchd_plists.py validar --destino PASTA_COM_PLISTS

Linha da tabela:  LOG  FREQ  DIAS  HORAS  COMANDO...
    FREQ  DAILY | WEEKLY | MONTHLY          (igual ao Agendador do Windows)
    DIAS  -  |  MON,TUE,...  |  1,16        (dia da semana ou dia do mes)
    HORAS 09:00,13:00,17:00
Um arquivo br.com.caldeira.<log>.plist por LOG (horarios do mesmo LOG ficam juntos).
"""
import argparse
import glob
import os
import plistlib
import posixpath
import shlex
import sys

PREFIXO = 'br.com.caldeira'
SEMANA = {'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6}
NOME_DIA = {0: 'dom', 1: 'seg', 2: 'ter', 3: 'qua', 4: 'qui', 5: 'sex', 6: 'sab'}
PATH_LAUNCHD = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'


def ler_tabela(texto):
    rotinas = {}
    for n, linha in enumerate(texto.splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith('#'):
            continue
        campos = linha.split(None, 4)
        if len(campos) < 5:
            raise SystemExit(f'ERRO na linha {n} da tabela: {linha}')
        log, freq, dias, horas, comando = campos
        freq = freq.upper()
        if freq not in ('DAILY', 'WEEKLY', 'MONTHLY'):
            raise SystemExit(f'ERRO na linha {n}: frequencia {freq}')
        intervalos = []
        for hora in horas.split(','):
            h, m = (int(x) for x in hora.split(':'))
            if freq == 'DAILY':
                intervalos.append({'Hour': h, 'Minute': m})
            elif freq == 'WEEKLY':
                for d in dias.upper().split(','):
                    intervalos.append({'Weekday': SEMANA[d], 'Hour': h, 'Minute': m})
            else:
                for d in dias.split(','):
                    intervalos.append({'Day': int(d), 'Hour': h, 'Minute': m})
        r = rotinas.setdefault(log, {'log': log, 'comando': shlex.split(comando), 'intervalos': []})
        if r['comando'] != shlex.split(comando):
            raise SystemExit(f'ERRO na linha {n}: o log {log} ja tem outro comando')
        r['intervalos'].extend(intervalos)
    return list(rotinas.values())


def rotulo(log, prefixo=PREFIXO):
    return f"{prefixo}.{log.replace('_', '-')}"


def montar(rotina, pasta, prefixo=PREFIXO):
    # caminhos do Mac (posixpath: o teste roda no Windows e o plist tem que sair com /)
    logs = posixpath.join(pasta, 'logs')
    return {
        'Label': rotulo(rotina['log'], prefixo),
        'ProgramArguments': ['/bin/bash', posixpath.join(pasta, 'deploy', 'mac', 'rodar_rotina.sh'),
                             rotina['log']] + rotina['comando'],
        'WorkingDirectory': pasta,
        'StartCalendarInterval': rotina['intervalos'],
        'EnvironmentVariables': {'PATH': PATH_LAUNCHD, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1',
                                 'LANG': 'pt_BR.UTF-8'},
        # a saida de cada rotina vai para logs/NOME.log (rodar_rotina.sh); aqui so erro do proprio launchd
        'StandardOutPath': posixpath.join(logs, 'launchd.log'),
        'StandardErrorPath': posixpath.join(logs, 'launchd.log'),
        'RunAtLoad': False,
    }


def gerar(pasta, destino, prefixo=PREFIXO, entrada=None):
    rotinas = ler_tabela(entrada if entrada is not None else sys.stdin.read())
    os.makedirs(destino, exist_ok=True)
    feitos = []
    for r in rotinas:
        dados = montar(r, pasta, prefixo)
        arq = os.path.join(destino, dados['Label'] + '.plist')
        with open(arq, 'wb') as f:
            plistlib.dump(dados, f, sort_keys=False)
        feitos.append(arq)
    return feitos


def descrever_agenda(intervalos):
    partes = []
    for i in intervalos:
        hora = f"{i.get('Hour', 0):02d}:{i.get('Minute', 0):02d}"
        if 'Weekday' in i:
            partes.append(f"{NOME_DIA[i['Weekday'] % 7]} {hora}")
        elif 'Day' in i:
            partes.append(f"dia {i['Day']:02d} {hora}")
        else:
            partes.append(f'todo dia {hora}')
    return ', '.join(partes)


def arquivos(destino, prefixo=PREFIXO):
    return sorted(glob.glob(os.path.join(destino, prefixo + '.*.plist')))


def listar(destino, prefixo=PREFIXO):
    achados = arquivos(destino, prefixo)
    if not achados:
        print('  Nenhuma rotina do Caldeira agendada neste Mac.')
        return 0
    for arq in achados:
        with open(arq, 'rb') as f:
            p = plistlib.load(f)
        cmd = ' '.join(p['ProgramArguments'][3:])
        print(f"  {p['Label']}\n      quando: {descrever_agenda(p.get('StartCalendarInterval') or [])}\n"
              f"      comando: {cmd}\n      log: logs/{p['ProgramArguments'][2]}.log")
    return len(achados)


def validar(destino, prefixo=PREFIXO):
    """Confere se cada plist abre e tem os campos que o launchd exige. Devolve a lista de erros."""
    erros = []
    for arq in arquivos(destino, prefixo):
        try:
            with open(arq, 'rb') as f:
                p = plistlib.load(f)
        except Exception as e:  # noqa: BLE001
            erros.append(f'{os.path.basename(arq)}: nao abre ({e})')
            continue
        if p.get('Label') + '.plist' != os.path.basename(arq):
            erros.append(f'{os.path.basename(arq)}: Label diferente do nome do arquivo')
        if not isinstance(p.get('ProgramArguments'), list) or len(p['ProgramArguments']) < 4:
            erros.append(f'{os.path.basename(arq)}: ProgramArguments incompleto')
        for i in p.get('StartCalendarInterval') or [None]:
            if not isinstance(i, dict) or not (0 <= i.get('Hour', -1) <= 23 and 0 <= i.get('Minute', -1) <= 59):
                erros.append(f'{os.path.basename(arq)}: horario invalido {i}')
            elif not (0 <= i.get('Weekday', 0) <= 7 and 1 <= i.get('Day', 1) <= 31):
                erros.append(f'{os.path.basename(arq)}: dia invalido {i}')
    return erros


def main():
    ap = argparse.ArgumentParser(description='Agentes do launchd (Mac) das rotinas do Caldeira')
    ap.add_argument('acao', choices=['gerar', 'listar', 'validar'])
    ap.add_argument('--pasta', help='pasta do sistema no Mac (gerar)')
    ap.add_argument('--destino', default=os.path.expanduser('~/Library/LaunchAgents'))
    ap.add_argument('--prefixo', default=PREFIXO)
    a = ap.parse_args()
    if a.acao == 'gerar':
        if not a.pasta:
            ap.error('gerar precisa de --pasta')
        pasta = a.pasta if a.pasta.startswith('/') else os.path.abspath(a.pasta)
        for arq in gerar(pasta.rstrip('/') or '/', a.destino, a.prefixo):
            print(arq)
    elif a.acao == 'listar':
        listar(a.destino, a.prefixo)
    else:
        erros = validar(a.destino, a.prefixo)
        for e in erros:
            print('  ERRO', e)
        print(f"  {len(arquivos(a.destino, a.prefixo))} plist(s), {len(erros)} erro(s)")
        return 1 if erros else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())

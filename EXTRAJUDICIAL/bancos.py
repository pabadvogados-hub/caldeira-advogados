"""
Base centralizada de e-mails dos bancos e cooperativas (config/bancos_emails.json).

- carregar(): le a base
- achar(banco, municipio): entrada do banco (prefere a agencia do municipio do cliente)
- validar(): confere formato de e-mail, campos vazios e duplicados
- listar(): comando "bancos" (lista + validacao + credores dos casos sem entrada na base)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from registro import mesmo_banco, norm  # noqa: E402

ARQUIVO = os.path.join(ambiente.RAIZ, 'config', 'bancos_emails.json')
EMAIL = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
CAMPOS = ('banco', 'apelidos', 'razao_social', 'cnpj', 'agencia', 'municipio', 'endereco', 'email',
          'email_copia', 'contato', 'observacao', 'conferido_em')


def carregar():
    if not os.path.exists(ARQUIVO):
        return []
    with open(ARQUIVO, encoding='utf-8') as f:
        dados = json.load(f)
    return dados.get('bancos', []) if isinstance(dados, dict) else dados


def casa(entrada, banco):
    nomes = [entrada.get('banco', '')] + list(entrada.get('apelidos') or [])
    return any(mesmo_banco(banco, n) for n in nomes if n)


def entradas_do_banco(banco):
    return [e for e in carregar() if casa(e, banco)]


def achar(banco, municipio=''):
    """Melhor entrada para o banco: a da agencia do municipio do cliente, senao a unica com e-mail."""
    entradas = entradas_do_banco(banco)
    if not entradas:
        return None
    mun = ' '.join(norm(municipio))
    if mun:
        do_municipio = [e for e in entradas if ' '.join(norm(e.get('municipio'))) == mun]
        if do_municipio:
            return next((e for e in do_municipio if e.get('email')), do_municipio[0])
    com_email = [e for e in entradas if e.get('email')]
    if len(com_email) == 1:
        return com_email[0]
    if len(com_email) > 1:
        e = dict(com_email[0])
        e['_ambiguo'] = f'{len(com_email)} agências com e-mail para {banco}; confira qual é a do cliente'
        return e
    return entradas[0]


def emails_validos(txt):
    return [x.strip() for x in re.split(r'[,;]', txt or '') if x.strip() and EMAIL.match(x.strip())]


def validar(entradas=None):
    """Lista de problemas da base (formato, campos vazios, duplicados)."""
    entradas = carregar() if entradas is None else entradas
    problemas, vistos = [], {}
    for i, e in enumerate(entradas, 1):
        rotulo = f"#{i} {e.get('banco') or '(sem nome)'} {e.get('agencia') or ''} {e.get('municipio') or ''}".strip()
        for c in CAMPOS:
            if c not in e:
                problemas.append(f'{rotulo}: falta o campo "{c}"')
        if not e.get('banco'):
            problemas.append(f'{rotulo}: sem nome do banco')
        for campo in ('email', 'email_copia'):
            for x in re.split(r'[,;]', e.get(campo) or ''):
                if x.strip() and not EMAIL.match(x.strip()):
                    problemas.append(f'{rotulo}: {campo} invalido "{x.strip()}"')
        if e.get('email') and not e.get('conferido_em'):
            problemas.append(f'{rotulo}: e-mail sem data de conferencia (conferido_em)')
        chave = (' '.join(norm(e.get('banco'))), ' '.join(norm(e.get('agencia'))), ' '.join(norm(e.get('municipio'))))
        if chave in vistos and any(chave[1:]):
            problemas.append(f'{rotulo}: duplicado da entrada #{vistos[chave]}')
        vistos.setdefault(chave, i)
    return problemas


def listar():
    from registro import bancos_ativos as bancos_do_caso
    from CONTRATACAO.pasta_cliente import listar_casos
    entradas = carregar()
    print(f'\nBase de e-mails: {ARQUIVO}')
    print(f"{'BANCO':26} {'AGENCIA':14} {'MUNICIPIO':18} {'E-MAIL':34} {'CNPJ':18} CONFERIDO")
    for e in entradas:
        print(f"{(e.get('banco') or '')[:26]:26} {(e.get('agencia') or '-')[:14]:14} "
              f"{(e.get('municipio') or '-')[:18]:18} {(e.get('email') or '(VAZIO)')[:34]:34} "
              f"{(e.get('cnpj') or '-')[:18]:18} {e.get('conferido_em') or '-'}")
    vazias = [e for e in entradas if not e.get('email')]
    print(f'\n{len(entradas)} entrada(s); {len(vazias)} sem e-mail (a notificacao sai, o rascunho no Gmail nao).')
    problemas = validar(entradas)
    if problemas:
        print('\nProblemas na base:')
        for p in problemas:
            print(f'  - {p}')
    faltando = {}
    for base, caso in listar_casos():
        for b in bancos_do_caso(caso):
            if not entradas_do_banco(b):
                faltando.setdefault(b, []).append(os.path.basename(base))
    if faltando:
        print('\nCredores dos casos que NAO estao na base (acrescentar uma entrada):')
        for b, clientes in faltando.items():
            print(f"  - {b}: {', '.join(clientes[:5])}")
    return problemas

"""
Envio ao produtor pelo WhatsApp (Atende Direito) SO do que foi revisado.

Regra (igual para avisos e relatorio periodico):
  1. o comando gera um .txt por cliente + INDICE_PARA_REVISAO.csv;
  2. o advogado le, corrige o .txt se precisar, escreve o nome em "revisado_por"
     e marca "enviar" = SIM;
  3. so entao `--enviar`: confere revisor, [PREENCHER]/[CONFERIR] no texto, telefone,
     credencial e pede confirmacao digitada ("SIM"). Cada envio fica anotado em "enviado_em".
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum  # noqa: E402

PENDENCIA = re.compile(r'\[(?:PREENCHER|CONFERIR)[^\]]*\]')
CAMPOS = ['cliente', 'telefone', 'processo', 'assunto', 'texto', 'precisa_preencher', 'origem',
          'revisado_por', 'enviar', 'enviado_em', 'chave']


def primeiro_nome(nome):
    partes = [p for p in re.sub(r'\(.*?\)', '', str(nome or '')).split() if len(p) > 2]
    return partes[0].title() if partes else 'tudo bem'


def ultimo_indice(subpasta):
    """INDICE_PARA_REVISAO.csv mais recente (fora dos de exemplo)."""
    raiz = comum.pasta_saida('controladoria', subpasta)
    pastas = sorted(p for p in os.listdir(raiz) if os.path.isdir(os.path.join(raiz, p)) and 'EXEMPLO' not in p)
    for p in reversed(pastas):
        caminho = os.path.join(raiz, p, 'INDICE_PARA_REVISAO.csv')
        if os.path.exists(caminho):
            return caminho
    return None


def enviar_indice(caminho, so=None):
    if not caminho or not os.path.exists(caminho):
        print('Nenhum índice para revisão encontrado. Gere as mensagens primeiro (sem --enviar).')
        return 1
    linhas = comum.ler_csv(caminho)
    fila = [r for r in linhas if (r.get('enviar') or '').strip().upper() in ('SIM', 'S', 'X')
            and not (r.get('enviado_em') or '').strip()]
    if so:
        fila = [r for r in fila if so.upper() in (r.get('cliente') or '').upper()]
    if not fila:
        print(f'Nada marcado com SIM na coluna "enviar" (ou já enviado). Índice: {caminho}')
        return 0
    sem_revisor = [r for r in fila if not (r.get('revisado_por') or '').strip()]
    if sem_revisor:
        print(f'ERRO: {len(sem_revisor)} mensagem(ns) marcada(s) para envio sem "revisado_por". Nada enviado.')
        return 1
    problemas = []
    for r in fila:
        try:
            with open(r['texto'], encoding='utf-8') as f:
                r['_texto'] = f.read().strip()
        except OSError:
            problemas.append(f"{r['cliente']}: arquivo de texto não encontrado")
            continue
        if PENDENCIA.search(r['_texto']):
            problemas.append(f"{r['cliente']}: ainda tem [PREENCHER]/[CONFERIR] no texto")
        if len(comum.digitos(r.get('telefone'))) < 10:
            problemas.append(f"{r['cliente']}: telefone ausente ou inválido")
    if problemas:
        print('ERRO: corrija antes de enviar (nada foi enviado):')
        for p in problemas:
            print(f'  - {p}')
        return 1
    if not ambiente.tem_credencial('ATENDE_DIREITO_TOKEN'):
        print('Sem ATENDE_DIREITO_TOKEN no config/.env: nada enviado (modo seguro).')
        return 1

    print(f'\n{len(fila)} mensagem(ns) revisada(s) prontas:')
    for r in fila:
        print(f"  - {r['cliente']} ({r['telefone']}): {r['assunto']}")
    try:
        ok = input('Confirma o envio pelo WhatsApp? (digite SIM): ').strip().upper() == 'SIM'
    except EOFError:
        ok = False
    if not ok:
        print('Cancelado.')
        return 0

    from atendedireito_integration import enviar_texto_por_telefone
    enviados = 0
    for r in fila:
        sucesso, _ = enviar_texto_por_telefone(r['telefone'], r['_texto'])
        if sucesso:
            r['enviado_em'] = datetime.now().isoformat(timespec='seconds')
            enviados += 1
            print(f"  [ok] {r['cliente']}")
        else:
            print(f"  [x]  {r['cliente']}: não enviado (contato não achado no Atende Direito?)")
    for r in linhas:
        r.pop('_texto', None)
    comum.salvar_csv(caminho, linhas, list(linhas[0].keys()))
    print(f'\nEnviados: {enviados} de {len(fila)}. Índice atualizado: {caminho}')
    return [r for r in fila if r.get('enviado_em')]

"""
RELATORIO PERIODICO AO PRODUTOR (a cada 15 ou 30 dias).

Para cada cliente ativo (processos do ADVBOX + casos das pastas ainda antes da acao):
  - o que aconteceu no periodo (movimentacoes do ADVBOX + publicacoes classificadas pela
    varredura), traduzido para a linguagem do dia a dia;
  - o que vem agora (pela fase), sem prometer resultado;
  - documentos que ainda faltam, se houver.
Modelo fixo (nada inventado); o que nao da para afirmar vira [PREENCHER ...].

Sai: SAIDA/controladoria/relatorios_clientes/AAAA-MM-DD_HHMM/ + INDICE_PARA_REVISAO.csv
Envio: `relatorio-clientes --enviar` (so revisado, pelo Atende Direito). A periodicidade
e controlada por cliente: so entra quem nao recebeu relatorio nos ultimos N dias.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classificador  # noqa: E402
import comum  # noqa: E402
import envio_cliente  # noqa: E402
import saidas_varredura  # noqa: E402
from avisos import nome_proprio  # noqa: E402
from config.escritorio import ESCRITORIO  # noqa: E402

ASSINATURA = ESCRITORIO['nome']
try:  # frases amigaveis dos documentos, as mesmas da cobranca da fase de contratacao
    from mensagens import COMO_MANDAR  # CONTRATACAO/mensagens.py
except Exception:
    COMO_MANDAR = {}

# publicacao classificada -> frase simples
FRASE_CATEGORIA = {
    'LIMINAR_DEFERIDA': 'o juiz concedeu a liminar (a proteção de urgência) a seu favor',
    'LIMINAR_INDEFERIDA': 'o juiz negou, por enquanto, o pedido de urgência; estamos avaliando o recurso',
    'REPLICA': 'o banco apresentou a defesa dele e nós estamos preparando a resposta',
    'CONTESTACAO_JUNTADA': 'o banco apresentou a defesa dele no processo',
    'MANIFESTACAO': 'o juiz pediu uma manifestação nossa, que está sendo feita dentro do prazo',
    'CUSTAS_EMENDA': 'o juiz pediu um ajuste ou o pagamento de custas para o processo seguir; estamos cuidando disso',
    'AUDIENCIA': 'foi marcada audiência',
    'PERICIA': 'o juiz determinou a perícia técnica',
    'SENTENCA_FAVORAVEL': 'saiu a sentença, a seu favor',
    'SENTENCA_DESFAVORAVEL': 'saiu a sentença (vamos te ligar para explicar e decidir o recurso)',
    'SENTENCA': 'saiu a sentença (vamos te explicar o resultado)',
    'RECURSO': 'o processo teve andamento no Tribunal (fase de recurso)',
    'EXECUCAO_PENHORA': 'o banco pediu medidas de cobrança no processo de execução; estamos cuidando da sua defesa',
    'EMBARGOS_DECLARACAO': 'o juiz respondeu a um pedido de esclarecimento da decisão',
    'TRANSITO_JULGADO': 'o processo terminou na Justiça (não cabe mais recurso)',
    'DESPACHO': 'o processo teve andamentos de rotina',
}

# movimentacao do ADVBOX/tribunal -> frase simples (a primeira regra que casar)
TRADUCAO = [
    (r'senten', 'foi dada a sentença'),
    (r'tutela|liminar', 'houve decisão sobre o pedido de urgência'),
    (r'audienc', 'houve movimentação sobre audiência'),
    (r'pericia|laudo|perito', 'houve movimentação sobre a perícia'),
    (r'contesta', 'o banco apresentou a defesa dele'),
    (r'replica|impugnacao a contestacao', 'apresentamos a resposta à defesa do banco'),
    (r'cita', 'o banco foi citado (avisado oficialmente da ação)'),
    (r'distribu', 'a ação foi distribuída (entrou na Justiça)'),
    (r'custas', 'houve movimentação sobre as custas do processo'),
    (r'conclus', 'o processo foi para o juiz analisar'),
    (r'remet|remessa|recebid', 'o processo foi enviado entre setores ou para o Tribunal'),
    (r'juntada|peticao', 'foram juntados documentos ou petições ao processo'),
    (r'expedi|intima|mandado|oficio', 'o cartório fez comunicações do processo (intimações, ofícios)'),
    (r'decorri|decurso|prazo', 'terminou um prazo do processo'),
    (r'despacho|decisao|expediente', 'o juiz deu andamento ao processo'),
]

# fase (ADVBOX ou caso) -> proximo passo tipico. E rascunho: o advogado confirma na revisao.
PROXIMO = [
    (r'extrajud|notifica', 'aguardamos a resposta do banco à notificação; sem resposta, seguimos para a ação na Justiça'),
    (r'contrata|documento', 'estamos reunindo os documentos para notificar o banco'),
    (r'inicial|distribu|liminar|urgen', 'o juiz vai analisar o pedido de urgência e mandar avisar o banco'),
    (r'contest|replica', 'vamos responder à defesa do banco, ponto a ponto'),
    (r'instru|pericia|prova', 'é a fase das provas (documentos, perícia, testemunhas); depois o juiz decide'),
    (r'senten|conclus', 'aguardamos a decisão do juiz; assim que sair, explicamos o que ela significa'),
    (r'recurs|tribunal|apela|agravo', 'o Tribunal vai reanalisar o caso; essa fase costuma demorar mais'),
    (r'execu|cumprimento', 'seguimos acompanhando o cumprimento e a cobrança no processo'),
]


def traduzir(descricao):
    t = classificador.norm(descricao)
    for rx, frase in TRADUCAO:
        if re.search(rx, t):
            return frase
    return 'outros andamentos de rotina'


def proximo_passo(fase):
    t = classificador.norm(fase)
    for rx, frase in PROXIMO:
        if re.search(rx, t):
            return frase
    return '[PREENCHER: próximo passo]'


def _registro():
    return os.path.join(comum.pasta_saida('controladoria'), '_relatorios_clientes.json')


def _ler_registro():
    try:
        with open(_registro(), encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _chave(nome):
    return classificador.norm(re.sub(r'\(.*?\)', '', nome or '')).strip().upper()


def montar_clientes(dias, exemplo=False):
    """Lista de clientes com o que aconteceu no periodo."""
    fim = comum.hoje()
    inicio = fim - timedelta(days=dias)
    procs = comum.processos(exemplo)
    if procs is None:
        comum.aviso_sem_advbox('os processos judiciais')
        procs = []
    ativos = [p for p in procs if comum.processo_ativo(p)]
    movs = comum.movimentacoes(inicio, fim, exemplo) or []
    por_proc = defaultdict(list)
    for m in movs:
        por_proc[str(m['processo_id'])].append(m)
    publicadas = defaultdict(list)
    for i in saidas_varredura.historico(inicio, fim, exemplo):
        if i.get('advbox_processo_id'):
            publicadas[str(i['advbox_processo_id'])].append(i)

    clientes = {}
    for p in ativos:
        nome = comum.cliente_do_processo(p) or 'CLIENTE SEM NOME'
        c = clientes.setdefault(_chave(nome), {'cliente': nome, 'telefone': '', 'processos': [], 'faltando': [],
                                               'fase': p.get('stage') or ''})
        c['telefone'] = c['telefone'] or comum.telefone_do_processo(p, exemplo)
        linhas = [FRASE_CATEGORIA.get(i['categoria'], '') + (f" ({i['evento_data']} {i['evento_hora']})".rstrip()
                  if i.get('evento_data') else '') for i in publicadas.get(str(p['id']), [])
                  if i.get('prazo_nosso') != 'NÃO']
        linhas += [traduzir(m['descricao']) for m in sorted(por_proc.get(str(p['id']), []), key=lambda m: m['data'])]
        vistas, unicas = set(), []
        for l_ in linhas:
            if l_ and l_ not in vistas:
                vistas.add(l_)
                unicas.append(l_)
        c['processos'].append({'numero': p.get('process_number') or '', 'banco': p.get('parte_contraria') or '',
                               'fase': p.get('stage') or '', 'aconteceu': unicas})

    for base, caso in comum.casos(exemplo):
        nome = comum.nome_do_caso(caso)
        c = clientes.get(_chave(nome))
        faltando = [COMO_MANDAR.get(s.get('id'), s['nome']) for s in comum.documentos_faltando(caso)]
        if c:
            c['faltando'] = faltando
            c['telefone'] = c['telefone'] or (caso.get('qualificacao') or {}).get('telefone', '')
            continue
        fase = comum.fase_do_caso(caso)
        aconteceu = []
        enviada = comum.notificacao_enviada_em(caso)
        if enviada and enviada >= inicio:
            aconteceu.append(f'enviamos a notificação ao banco em {comum.br(enviada)}')
        if caso.get('documentos_completos_em') and (comum.data(caso['documentos_completos_em']) or fim) >= inicio:
            aconteceu.append('recebemos todos os documentos que faltavam')
        bancos = ', '.join(sorted({nome_proprio(o.get('banco')) for o in (caso.get('triagem') or {}).get('operacoes') or []
                                   if o.get('banco')}))
        clientes[_chave(nome)] = {'cliente': nome, 'telefone': (caso.get('qualificacao') or {}).get('telefone', ''),
                                  'fase': fase, 'faltando': faltando,
                                  'processos': [{'numero': '', 'banco': bancos, 'fase': fase, 'aconteceu': aconteceu}]}
    return list(clientes.values())


def texto_cliente(c, dias):
    nome = envio_cliente.primeiro_nome(c['cliente'])
    partes = [f'Olá, {nome}! Aqui é do {ASSINATURA}.', '',
              f'Passando para contar como está o seu caso nos últimos {dias} dias.']
    sem_movimento = True
    for p in c['processos']:
        banco = nome_proprio(p['banco']) if p['banco'] else ''
        partes.append('')
        cab = ('Processo' if p['numero'] else 'Seu caso') + (f" contra {banco}" if banco else '') \
            + (f" (nº {p['numero']})" if p['numero'] else '')
        partes.append(cab + ':')
        if p['aconteceu']:
            sem_movimento = False
            partes += [f'- {a[0].upper() + a[1:]}' for a in p['aconteceu']]
        else:
            partes.append('- Neste período não houve movimentação nova. A Justiça tem o tempo dela; seguimos '
                          'acompanhando todos os dias.')
        partes.append(f"Próximo passo: {proximo_passo(p['fase'])}.")
    partes.append('')
    if c['faltando']:
        partes.append('Para o seu caso andar mais rápido, ainda precisamos de: ' + '; '.join(c['faltando'])
                      + '. Pode mandar foto por aqui mesmo.')
    else:
        partes.append('Você não precisa fazer nada agora. Qualquer novidade importante, a gente avisa na hora.')
    partes += ['Se o banco entrar em contato, não negocie direto: fale com a gente antes.', '',
               'Qualquer dúvida, é só responder esta mensagem.', '', ASSINATURA]
    return '\n'.join(partes), sem_movimento


def gerar(dias=30, exemplo=False):
    print(f'\n=== RELATÓRIO DE ANDAMENTO AOS CLIENTES ({dias} dias) ===')
    registro = {} if exemplo else _ler_registro()
    hoje = comum.hoje()
    clientes = montar_clientes(dias, exemplo)
    fila = [c for c in clientes if not registro.get(_chave(c['cliente']))
            or (hoje - comum.data(registro[_chave(c['cliente'])])).days >= dias]
    print(f'   {len(clientes)} cliente(s) ativo(s); {len(fila)} sem relatório nos últimos {dias} dias.')
    if not fila:
        return None
    pasta = comum.pasta_saida('controladoria', 'relatorios_clientes',
                              datetime.now().strftime('%Y-%m-%d_%H%M') + ('_EXEMPLO' if exemplo else ''))
    indice = []
    for n, c in enumerate(sorted(fila, key=lambda x: x['cliente']), 1):
        texto, sem_mov = texto_cliente(c, dias)
        nome_arq = re.sub(r'[<>:"/\\|?*]', '', c['cliente'])[:60].strip()
        arq = os.path.join(pasta, f"{n:03d} - {nome_arq}.txt")
        with open(arq, 'w', encoding='utf-8') as f:
            f.write(texto)
        tel = c['telefone'] or '[PREENCHER telefone]'
        pend = 'SIM' if envio_cliente.PENDENCIA.search(texto + ' ' + tel) else 'nao'
        indice.append({'cliente': c['cliente'], 'telefone': tel,
                       'processo': ', '.join(p['numero'] for p in c['processos'] if p['numero']),
                       'assunto': f'Relatório de {dias} dias', 'texto': arq, 'precisa_preencher': pend,
                       'origem': 'modelo fixo', 'revisado_por': '', 'enviar': '', 'enviado_em': '',
                       'chave': _chave(c['cliente']), 'fase': c['fase'],
                       'sem_movimento': 'SIM' if sem_mov else ''})
    csv_ = comum.salvar_csv(os.path.join(pasta, 'INDICE_PARA_REVISAO.csv'), indice,
                            envio_cliente.CAMPOS + ['fase', 'sem_movimento'])
    print(f"   {len(indice)} relatório(s) em {pasta}")
    print(f"   {sum(1 for r in indice if r['precisa_preencher'] == 'SIM')} com [PREENCHER] | "
          f"{sum(1 for r in indice if r['sem_movimento'])} sem movimentação no período (conferir se não está parado)")
    print(f'   Revisão: {csv_}')
    print('   PRÓXIMO PASSO (humano): revisar cada .txt, "revisado_por" + "enviar"=SIM e rodar '
          'python CONTROLADORIA/main.py relatorio-clientes --enviar')
    return csv_


def enviar(so=None):
    enviados = envio_cliente.enviar_indice(envio_cliente.ultimo_indice('relatorios_clientes'), so)
    if isinstance(enviados, list) and enviados:
        registro = _ler_registro()
        for r in enviados:
            registro[r.get('chave') or _chave(r['cliente'])] = comum.hoje().isoformat()
        with open(_registro(), 'w', encoding='utf-8') as f:
            json.dump(registro, f, ensure_ascii=False, indent=1)
    return enviados

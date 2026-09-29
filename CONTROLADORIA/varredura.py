"""
VARREDURA da Controladoria (fase 5 - acompanhamento processual).

  DJEN por OAB  ->  cruza com o ADVBOX (/lawsuits pelo numero do processo)
  ->  classifica (classificador.py; --ia refina o que ficou em REVISAO_MANUAL)
  ->  prazo fatal PRELIMINAR + prazo interno D-3 (prazos.py)
  ->  providencia / peca sugerida / responsavel
  ->  relatorio DOCX (timbrado) + CSV + agenda .ics + JSON (historico) em SAIDA/controladoria/
  ->  com --criar-tarefas: tarefa no ADVBOX para o responsavel, confirmando item a item.

Nada sai do escritorio sem --criar-tarefas E ADVBOX_API_TOKEN. A IA nao protocola.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime, timedelta  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classificador  # noqa: E402
import comum  # noqa: E402
import dados_exemplo as ex  # noqa: E402
import prazos  # noqa: E402
from configuracao import ACOES, DIAS_ANTES_FATAL, TAG_TAREFA  # noqa: E402

ORDEM_GRAVIDADE = {'ALTA': 0, 'MEDIA': 1, 'BAIXA': 2}


# ============================================================
# 1. COLETA
# ============================================================

def coletar_djen(dias, exemplo=False):
    """Resumos das comunicacoes (sem repeticao) + lista de OABs consultadas."""
    import comunica_djen
    if exemplo:
        brutos = ex.djen()
        oabs = comunica_djen.oabs_monitoradas()
        print(f'   MODO EXEMPLO: {len(brutos)} publicações fictícias (o DJEN não foi consultado)')
    else:
        oabs = comunica_djen.oabs_monitoradas()
        fim = comum.hoje()
        inicio = fim - timedelta(days=max(1, int(dias)) - 1)
        brutos = []
        for numero, uf in oabs:
            print(f'   DJEN: OAB {numero}/{uf} de {comum.br(inicio)} a {comum.br(fim)}...')
            try:
                achados = comunica_djen.consultar(oab_numero=numero, oab_uf=uf,
                                                  data_inicio=inicio.isoformat(), data_fim=fim.isoformat())
            except RuntimeError as e:
                print(f'   AVISO: DJEN falhou para {numero}/{uf}: {e}')
                continue
            print(f'         {len(achados)} comunicação(ões)')
            brutos.extend(achados)
    vistos, chaves, resumos = set(), set(), []
    for b in brutos:
        if b.get('id') in vistos:
            continue
        vistos.add(b.get('id'))
        r = comunica_djen.resumir(b)
        # a mesma publicacao sai uma vez por advogado: fica uma so
        chave = (comum.digitos(r['processo']), r.get('tipo_documento'), (r.get('texto') or '')[:400])
        if chave in chaves:
            continue
        chaves.add(chave)
        resumos.append(r)
    return resumos, oabs


def casos_por_processo(exemplo=False):
    """{id do processo no ADVBOX ou numero (digitos): (pasta, caso)} para achar a pasta do cliente."""
    mapa = {}
    for base, caso in comum.casos(exemplo):
        pid = (caso.get('advbox') or {}).get('processo_id')
        if pid:
            mapa[str(pid)] = (base, caso)
        for p in comum.pecas_judiciais(caso):
            num = comum.digitos(p.get('numero_processo'))
            if num:
                mapa[num] = (base, caso)
        num = comum.digitos(caso.get('numero_processo'))
        if num:
            mapa[num] = (base, caso)
    return mapa


# ============================================================
# 2. MONTAGEM DE CADA ITEM
# ============================================================

def _responsavel(categoria, processo, exemplo):
    """Coordenador para o que e estrategico; senao o responsavel do processo no ADVBOX."""
    cargo = ACOES[categoria]['cargo']
    if cargo != 'COORDENADOR_JURIDICO' and processo:
        uid = str(processo.get('responsible_id') or processo.get('users_id') or '')
        nome = processo.get('responsible') or ''
        if not uid and nome and not exemplo and comum.tem_advbox():
            try:
                import advbox_integration as advbox
                uid = str(advbox.id_usuario_por_nome(nome) or '')
            except Exception:
                uid = ''
        if uid or nome:
            return comum.rotulo_pessoa(uid, nome, exemplo), uid, comum.cargo_do_usuario(uid, nome, exemplo) or cargo
    return (comum.rotulo_pessoa(comum.id_do_cargo(cargo, exemplo), None, exemplo) if comum.id_do_cargo(cargo, exemplo)
            else comum.CARGO_LEGIVEL.get(cargo, cargo)), comum.id_do_cargo(cargo, exemplo), cargo


def montar_item(r, cls, processo=None, caso_ref=None, exemplo=False):
    acao = ACOES[cls['categoria']]
    hoje = comum.hoje()
    disp = comum.data(r.get('data'))
    publicacao = prazos.data_publicacao(disp) if disp else None
    fatal = prazos.prazo_fatal(disp, cls['prazo_dias'], cls['prazo_corridos']) if cls['prazo_dias'] else None
    ev = cls.get('evento') or {}
    if cls['categoria'] == 'AUDIENCIA' and ev.get('data'):
        fatal = comum.data(ev['data'])  # a "data fatal" da audiencia e o proprio dia
    interno, atrasado = prazos.prazo_interno(fatal, DIAS_ANTES_FATAL, hoje) if fatal else (None, False)
    if not fatal and publicacao:
        if acao.get('acompanhar_dias'):
            interno = prazos.somar_dias_uteis(publicacao, acao['acompanhar_dias'])
        elif cls['categoria'] in ('REVISAO_MANUAL', 'TRANSITO_JULGADO'):
            interno = prazos.somar_dias_uteis(publicacao, 2)
    restantes = prazos.dias_uteis_entre(hoje, fatal) if fatal else None

    gravidade = acao['gravidade']
    if not cls['prazo_nosso']:
        gravidade = 'BAIXA'
    elif restantes is not None and restantes <= 5:
        gravidade = 'ALTA'
    elif cls['categoria'] == 'AUDIENCIA' and fatal and (fatal - hoje).days <= 10:
        gravidade = 'ALTA'

    resp_nome, resp_id, resp_cargo = _responsavel(cls['categoria'], processo, exemplo)
    base = caso_ref[0] if caso_ref else ''
    cliente = comum.cliente_do_processo(processo) if processo else ''
    if not cliente and caso_ref:
        cliente = comum.nome_do_caso(caso_ref[1])
    if not cliente:
        nossos = [n for n, p in r.get('polos') or [] if p == cls['polo']]
        cliente = (nossos[0] + ' (pelo DJEN)') if nossos else ''
    contrarios = [n for n, p in r.get('polos') or [] if p and p != cls['polo']]

    if ev.get('data') and not prazos.dia_util(comum.data(ev['data']), contar_recesso=True):
        cls['observacoes'].append(f"A data da {ev['tipo'].lower()} ({ev['data']}) cai em fim de semana/feriado: conferir.")
    providencia = acao['providencia'] if cls['prazo_nosso'] else 'Prazo da parte contrária: só acompanhar.'
    comando = acao['comando'].format(pasta=base or 'PASTA DO CLIENTE') if acao['comando'] else ''
    return {
        'id_djen': r.get('id'),
        'processo': r.get('processo') or '',
        'cliente': cliente or 'NÃO ENCONTRADO NO ADVBOX - conferir',
        'parte_contraria': (processo or {}).get('parte_contraria') or (contrarios[0] if contrarios else ''),
        'tribunal': r.get('tribunal') or '',
        'orgao': r.get('orgao') or '',
        'classe': r.get('classe') or '',
        'tipo_documento': r.get('tipo_documento') or r.get('tipo') or '',
        'data_disponibilizacao': comum.br(disp),
        'data_publicacao': prazos.br(publicacao),
        'link': r.get('link') or '',
        'categoria': cls['categoria'],
        'rotulo': cls['rotulo'],
        'motivo': cls['motivo'],
        'confianca': cls['confianca'],
        'origem_classificacao': 'regras',
        'sinais': ', '.join(cls['sinais']),
        'observacoes': ' | '.join(cls['observacoes']),
        'polo': {'A': 'ativo', 'P': 'passivo'}.get(cls['polo'], '') + (' (presumido)' if cls['polo_origem'] == 'presumido' else ''),
        'favoravel': {True: 'SIM', False: 'NÃO'}.get(cls['favoravel'], ''),
        'prazo_dias': cls['prazo_dias'] or '',
        'prazo_origem': cls['prazo_origem'],
        'prazo_corridos': 'SIM' if cls['prazo_corridos'] else '',
        'prazo_nosso': 'SIM' if cls['prazo_nosso'] else 'NÃO',
        'fatal': prazos.br(fatal),
        'fatal_iso': fatal.isoformat() if fatal else '',
        'interno': prazos.br(interno),
        'interno_iso': interno.isoformat() if interno else '',
        'interno_atrasado': 'SIM' if atrasado else '',
        'dias_uteis_restantes': '' if restantes is None else restantes,
        'evento_tipo': ev.get('tipo', ''),
        'evento_data': ev.get('data', ''),
        'evento_hora': ev.get('hora', ''),
        'evento_virtual': 'SIM' if ev.get('virtual') else '',
        'providencia': providencia,
        'peca': acao['peca'],
        'comando': comando,
        'responsavel': resp_nome,
        'responsavel_id': resp_id,
        'responsavel_cargo': resp_cargo,
        'gravidade': gravidade,
        'aviso_cliente': 'SIM' if (acao['aviso_cliente'] and cls['prazo_nosso'] is not False) else '',
        'advbox_processo_id': (processo or {}).get('id') or '',
        'advbox_fase': (processo or {}).get('stage') or '',
        'pasta': base,
        'frase_chave': cls['frase_chave'],
    }


def ordenar(itens):
    return sorted(itens, key=lambda i: (ORDEM_GRAVIDADE.get(i['gravidade'], 1),
                                        i['interno_iso'] or '9999', i['fatal_iso'] or '9999'))


# ============================================================
# 3. IA (opcional) PARA O QUE FICOU EM REVISAO MANUAL
# ============================================================

def refinar_com_ia(itens, resumos, maximo=3):
    """Pede a IA uma sugestao de classificacao para ate `maximo` itens em REVISAO_MANUAL."""
    if not ambiente.tem_credencial('ANTHROPIC_API_KEY'):
        print('   IA: sem ANTHROPIC_API_KEY, os itens seguem em REVISÃO MANUAL.')
        return 0
    import ia
    modelo = os.getenv('MODELO_CONTROLADORIA') or os.getenv('MODELO_EXTRACAO') or 'claude-sonnet-5'
    por_id = {r.get('id'): r for r in resumos}
    categorias = [k for k in ACOES]
    schema = {
        'type': 'object', 'additionalProperties': False,
        'required': ['categoria', 'prazo_dias', 'prazo_e_do_escritorio', 'resumo', 'justificativa'],
        'properties': {
            'categoria': {'type': 'string', 'enum': categorias},
            'prazo_dias': {'type': 'integer', 'description': 'dias do prazo para o escritorio; 0 se nao houver'},
            'prazo_e_do_escritorio': {'type': 'boolean'},
            'resumo': {'type': 'string', 'description': 'o que a publicacao diz, em 1 ou 2 frases'},
            'justificativa': {'type': 'string', 'description': 'trecho do texto que sustenta a classificacao'},
        },
    }
    sistema = (
        'Voce e a controladoria juridica de um escritorio que defende produtores rurais contra bancos '
        '(divida rural, Rondonia). Classifique a publicacao do Diario de Justica em UMA categoria da lista. '
        'Use SO o texto recebido; nao invente fatos, datas ou prazos. Se o texto nao permitir decidir, '
        'responda REVISAO_MANUAL. prazo_dias: so o prazo que o texto da ao escritorio (0 se nao houver ou se '
        'for da outra parte). Categorias: '
        + '; '.join(f'{k} = {v["rotulo"]}' for k, v in ACOES.items())
    )
    feitos = 0
    for it in itens:
        if feitos >= maximo:
            break
        if it['categoria'] != 'REVISAO_MANUAL':
            continue
        r = por_id.get(it['id_djen']) or {}
        conteudo = (f"Tribunal: {r.get('tribunal')} | Orgao: {r.get('orgao')} | Classe: {r.get('classe')} | "
                    f"Tipo: {r.get('tipo_documento')}\nTexto:\n{classificador.limpar(r.get('texto'))[:12000]}")
        try:
            resp = ia.json_por_schema(modelo, sistema, conteudo, schema, max_tokens=2000)
        except Exception as e:
            print(f'   IA: falhou em {it["processo"]} ({str(e)[:120]})')
            continue
        feitos += 1
        cat = resp.get('categoria') or 'REVISAO_MANUAL'
        nota = f"Sugestão da IA (conferir): {resp.get('resumo', '')} Base: \"{resp.get('justificativa', '')[:200]}\""
        it['observacoes'] = (it['observacoes'] + ' | ' if it['observacoes'] else '') + nota
        if cat != 'REVISAO_MANUAL':
            acao = ACOES[cat]
            it.update({'categoria': cat, 'rotulo': acao['rotulo'] + ' (IA)', 'origem_classificacao': 'ia',
                       'confianca': 'ia - conferir', 'providencia': acao['providencia'], 'peca': acao['peca']})
            dias = resp.get('prazo_dias') or 0
            if dias and resp.get('prazo_e_do_escritorio'):
                disp = comum.data(it['data_disponibilizacao'])
                fatal = prazos.prazo_fatal(disp, dias)
                interno, atrasado = prazos.prazo_interno(fatal, DIAS_ANTES_FATAL, comum.hoje())
                it.update({'prazo_dias': dias, 'prazo_origem': 'IA (conferir)', 'fatal': prazos.br(fatal),
                           'fatal_iso': fatal.isoformat(), 'interno': prazos.br(interno),
                           'interno_iso': interno.isoformat(), 'interno_atrasado': 'SIM' if atrasado else '',
                           'dias_uteis_restantes': prazos.dias_uteis_entre(comum.hoje(), fatal),
                           'gravidade': acao['gravidade']})
        print(f"   IA: {it['processo']} -> {cat}")
    return feitos


# ============================================================
# 4. TAREFAS NO ADVBOX (so com --criar-tarefas, item a item)
# ============================================================

def _registro_tarefas():
    return os.path.join(comum.pasta_saida('controladoria'), '_tarefas_criadas.json')


def _ler_registro():
    try:
        with open(_registro_tarefas(), encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _perguntar(texto):
    try:
        return input(texto).strip().lower()
    except EOFError:  # rodando agendado/sem terminal: nunca cria
        return 'n'


def texto_da_tarefa(i):
    linhas = [f"{TAG_TAREFA} DJEN#{i['id_djen']} | {i['rotulo']}"]
    if i['fatal']:
        linhas.append(f"Prazo FATAL (preliminar, conferir): {i['fatal']} | Interno D-{DIAS_ANTES_FATAL}: {i['interno']}")
    if i['evento_data']:
        linhas.append(f"{i['evento_tipo'].title()}: {i['evento_data']} {i['evento_hora']}".strip())
    linhas.append(f"Providência: {i['providencia']}")
    if i['peca']:
        linhas.append(f"Peça sugerida: {i['peca']}" + (f" ({i['comando']})" if i['comando'] else ''))
    if i['observacoes']:
        linhas.append(f"Atenção: {i['observacoes']}")
    linhas.append(f"Publicação: {i['data_disponibilizacao']} - {i['tribunal']} {i['orgao']}")
    if i['link']:
        linhas.append(f"Link: {i['link']}")
    return '\n'.join(linhas)


def candidatos_a_tarefa(itens):
    return [i for i in itens
            if i['advbox_processo_id'] and i['prazo_nosso'] == 'SIM' and i['categoria'] != 'DESPACHO'
            and (i['interno_iso'] or i['evento_data'])]


def criar_tarefas(itens, exemplo=False):
    cands = candidatos_a_tarefa(itens)
    sem_processo = [i for i in itens if not i['advbox_processo_id'] and i['prazo_nosso'] == 'SIM'
                    and (i['fatal'] or i['categoria'] == 'REVISAO_MANUAL')]
    print(f'\n=== TAREFAS NO ADVBOX: {len(cands)} candidata(s) ===')
    for n, i in enumerate(cands, 1):
        print(f"  {n:2}. [{i['gravidade']}] interno {i['interno'] or '-'} | fatal {i['fatal'] or '-'} | "
              f"{i['processo']} | {i['rotulo']} -> {i['responsavel']}")
    if sem_processo:
        print(f'  (+ {len(sem_processo)} com prazo mas SEM processo no ADVBOX: cadastrar antes; ver o relatório)')
    if not cands:
        return []
    if exemplo:
        print('  MODO EXEMPLO: nada foi criado no ADVBOX (simulação).')
        return []
    if not comum.tem_advbox():
        print('  Sem ADVBOX_API_TOKEN: nada criado (modo seguro).')
        return []

    import advbox_integration as advbox
    remetente = comum.remetente()
    if not remetente:
        print('  ERRO: config/equipe.py sem advbox_id do remetente (REMETENTE_TAREFAS). Nada criado.')
        return []
    registro = _ler_registro()
    criadas = []
    for i in cands:
        chave = str(i['id_djen'])
        if chave in registro:
            print(f"  {i['processo']}: já criada em {registro[chave]['em']} (pulado)")
            continue
        try:
            existentes = advbox.listar_tarefas_ritmado(lawsuit_id=str(i['advbox_processo_id']))
        except Exception as e:
            print(f"  {i['processo']}: não consegui conferir duplicidade ({str(e)[:80]}); pulado por segurança.")
            continue
        if any(f'DJEN#{chave}' in str(t.get('comments') or t.get('notes') or '') for t in existentes):
            print(f"  {i['processo']}: o ADVBOX já tem tarefa desta publicação (pulado)")
            continue
        print(f"\n  {i['processo']} | {i['cliente']}\n  {i['rotulo']} | interno {i['interno']} | fatal {i['fatal']}")
        print(f"  Para: {i['responsavel']}")
        if _perguntar('  Criar esta tarefa no ADVBOX? (s/N): ') != 's':
            print('  Pulado.')
            continue
        tipo = None
        for nome in ACOES[i['categoria']]['tipo_tarefa'] + [os.getenv('ADVBOX_TIPO_TAREFA_PADRAO') or '']:
            if nome:
                tipo = advbox.buscar_tipo_tarefa(nome)
                if tipo:
                    break
        destinatario = i['responsavel_id'] or comum.id_do_cargo(ACOES[i['categoria']]['cargo'])
        if not (tipo and destinatario):
            print(f"  Pulado: falta o tipo de tarefa no ADVBOX ({ACOES[i['categoria']]['tipo_tarefa']}) "
                  f"ou o ID do responsável em config/equipe.py.")
            continue
        urgente = (i['gravidade'] == 'ALTA' and i['dias_uteis_restantes'] != ''
                   and int(i['dias_uteis_restantes']) <= 5)
        try:
            r = advbox.criar_publicacao(i['advbox_processo_id'], tipo, [str(destinatario)], texto_da_tarefa(i),
                                        from_id=str(remetente), date_deadline=i['interno_iso'] or None,
                                        urgent=urgente)
        except Exception as e:
            print(f'  ERRO ao criar: {str(e)[:150]}')
            continue
        registro[chave] = {'em': datetime.now().isoformat(timespec='seconds'), 'processo': i['processo'],
                           'resposta': r if isinstance(r, dict) else str(r)}
        with open(_registro_tarefas(), 'w', encoding='utf-8') as f:
            json.dump(registro, f, ensure_ascii=False, indent=1)
        criadas.append(chave)
        print('  Tarefa criada.')
    print(f'\n  {len(criadas)} tarefa(s) criada(s).')
    return criadas


# ============================================================
# 5. EXECUCAO
# ============================================================

def executar(dias=7, criar=False, exemplo=False, usar_ia=False, ia_max=3):
    print('\n=== CONTROLADORIA: VARREDURA DO DJEN ===')
    resumos, oabs = coletar_djen(dias, exemplo)
    print(f'   {len(resumos)} publicação(ões) única(s)')
    if not resumos:
        print('   Nada publicado no período (se for inesperado, a API do DJEN pode ter dado falso-vazio: rode de novo).')
        return None

    procs = comum.processos(exemplo)
    aviso_advbox = ''
    if procs is None:
        comum.aviso_sem_advbox('o cruzamento com os processos do ADVBOX')
        aviso_advbox = 'SEM ADVBOX (sem credencial): cliente, responsável e processo não foram cruzados.'
        indice = {}
    else:
        import advbox_integration as advbox
        indice = advbox.indice_processos_por_numero(procs)
        print(f'   ADVBOX: {len(procs)} processo(s) no índice')
    mapa_casos = casos_por_processo(exemplo)

    itens = []
    for r in resumos:
        cls = classificador.classificar(r)
        num = comum.digitos(r.get('processo'))
        proc = indice.get(num)
        caso_ref = mapa_casos.get(str((proc or {}).get('id') or '')) or mapa_casos.get(num)
        itens.append(montar_item(r, cls, proc, caso_ref, exemplo))

    if usar_ia:
        refinar_com_ia(itens, resumos, ia_max)
    itens = ordenar(itens)

    import saidas_varredura
    fim = comum.hoje()
    cabecalho = [
        ('Período', f'{comum.br(fim - timedelta(days=max(1, int(dias)) - 1))} a {comum.br(fim)}'
                    + (' (EXEMPLO FICTÍCIO)' if exemplo else '')),
        ('OABs', ', '.join(f'{n}/{u}' for n, u in oabs)),
        ('ADVBOX', aviso_advbox or 'cruzado pelo número do processo'),
        ('Gerado em', datetime.now().strftime('%d/%m/%Y %H:%M')),
    ]
    arquivos = saidas_varredura.salvar_tudo(itens, cabecalho, exemplo,
                                            meta={'dias': dias, 'oabs': oabs, 'sem_advbox': bool(aviso_advbox)})

    print('\n   RESUMO')
    from collections import Counter
    for cat, n in Counter(i['categoria'] for i in itens).most_common():
        print(f'   {n:3}  {ACOES[cat]["rotulo"]}')
    print(f"   Prioridade ALTA: {sum(1 for i in itens if i['gravidade'] == 'ALTA')} | "
          f"sem folga p/ D-{DIAS_ANTES_FATAL}: {sum(1 for i in itens if i['interno_atrasado'])} | "
          f"sem processo no ADVBOX: {sum(1 for i in itens if not i['advbox_processo_id'])}")
    print(f"   Relatório: {arquivos['docx']}\n   Planilha:  {arquivos['csv']}\n"
          f"   Agenda:    {arquivos['ics']} ({arquivos['eventos_agenda']} evento(s))")

    if criar:
        criar_tarefas(itens, exemplo)
    else:
        n = len(candidatos_a_tarefa(itens))
        print(f'\n   {n} item(ns) podem virar tarefa no ADVBOX. Nada foi criado: rode com --criar-tarefas '
              '(confirmação item a item).')
    return itens, arquivos

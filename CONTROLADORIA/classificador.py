"""
Classificador de 1a passada das publicacoes do DJEN (regras e palavras-chave).

Rapido e 100% auditavel: cada item sai com o "motivo" (a regra que casou) e os
"sinais" secundarios encontrados. Nao decide sozinho em caso ambiguo: o que nao
casa com nenhuma regra segura vira REVISAO_MANUAL (e pode passar pela IA com
`varredura --ia`, sempre marcado como sugestao da IA).

Tambem descobre:
  - em que polo o escritorio esta (pelo "Advogados do(a) AUTOR: ..." do proprio texto;
    sem isso, presume pela classe processual e avisa);
  - se o prazo e do escritorio ou da parte contraria ("intime-se o exequente...");
  - quantos dias de prazo o texto da e se sao corridos;
  - data e hora de audiencia/pericia.
"""
import html
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from configuracao import ACOES, CLASSES_POLO_PASSIVO  # noqa: E402

# ------------------------------------------------------------------
# TEXTO
# ------------------------------------------------------------------


def limpar(texto):
    t = re.sub(r'<[^>]+>', ' ', texto or '')
    t = html.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def sentencas(texto_limpo):
    partes = re.split(r'(?<=[\.;!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ“"(])', texto_limpo)
    return [p.strip() for p in partes if p.strip()]


# ------------------------------------------------------------------
# POLO DO ESCRITORIO
# ------------------------------------------------------------------

ATIVO = {'autor', 'autora', 'autores', 'requerente', 'requerentes', 'exequente', 'exequentes',
         'embargante', 'embargantes', 'agravante', 'agravantes', 'apelante', 'apelantes',
         'impetrante', 'impetrantes', 'recorrente', 'recorrentes'}
PASSIVO = {'reu', 're', 'reus', 'requerido', 'requerida', 'requeridos', 'requeridas', 'executado',
           'executada', 'executados', 'embargado', 'embargada', 'embargados', 'agravado', 'agravada',
           'agravados', 'apelado', 'apelada', 'apelados', 'impetrado',
           'recorrido', 'recorrida'}
_PAPEL = re.compile(r'\b(' + '|'.join(sorted(ATIVO | PASSIVO, key=len, reverse=True)) + r')\b')


def _marcas_escritorio():
    """Nomes dos advogados (config/escritorio.py) e numeros de OAB monitorados."""
    marcas = []
    try:
        from config.escritorio import OUTORGADOS
        marcas += [norm(o['nome']) for o in OUTORGADOS]
    except Exception:
        pass
    try:
        from comunica_djen import oabs_monitoradas
        marcas += [n for n, _ in oabs_monitoradas()]
    except Exception:
        pass
    return [m for m in marcas if m]


MARCAS = None


def polo_do_escritorio(t_norm, classe_norm):
    """Retorna (polo 'A'/'P', origem 'texto'/'presumido')."""
    global MARCAS
    if MARCAS is None:
        MARCAS = _marcas_escritorio()
    posicoes = [t_norm.find(m) for m in MARCAS if m and t_norm.find(m) >= 0]
    if posicoes:
        pos = min(posicoes)
        antes = t_norm[max(0, pos - 500):pos]
        papeis = re.findall(r'advogad[oa]s?\s*(?:\(\w\)\s*)?(?:do|da|dos|das)\s*(?:\(\w+\)\s*)?(\w+)', antes)
        for papel in reversed(papeis):
            if papel in ATIVO:
                return 'A', 'texto'
            if papel in PASSIVO:
                return 'P', 'texto'
        ult_a, ult_p = antes.rfind('polo ativo'), antes.rfind('polo passivo')
        if ult_a > ult_p:
            return 'A', 'texto'
        if ult_p > ult_a:
            return 'P', 'texto'
    if any(norm(c) in classe_norm for c in CLASSES_POLO_PASSIVO):
        return 'P', 'presumido'
    return 'A', 'presumido'


_VERBO = re.compile(r'\b(intim\w*|fica[m]?|manifest\w*|determino|cite-se|apresent\w*|comprov\w*|'
                    r'recolh\w*|emend\w*|efetue|deposit\w*|inform\w*|indiqu\w*|junte|dê-se vista|de-se vista|vista)\b')


def destinatario(sent_norm):
    """Polo a quem a ordem se dirige: 'A', 'P', 'AMBOS' ou None."""
    if re.search(r'\b(as partes|ambas as partes|partes intimadas|intimem-se as partes|intimacao partes)\b', sent_norm):
        return 'AMBOS'
    m = _VERBO.search(sent_norm)
    if not m:
        return None
    depois = _PAPEL.search(sent_norm[m.end():m.end() + 90])
    papel = depois.group(1) if depois else None
    if not papel:
        antes = list(_PAPEL.finditer(sent_norm[max(0, m.start() - 60):m.start()]))
        papel = antes[-1].group(1) if antes else None
    if papel in ATIVO:
        return 'A'
    if papel in PASSIVO:
        return 'P'
    return None


# ------------------------------------------------------------------
# PRAZO E EVENTOS
# ------------------------------------------------------------------

_PRAZO = [
    re.compile(r'prazo\s+(?:legal\s+|comum\s+|improrrogavel\s+|sucessivo\s+)?de\s+(\d{1,3})\s*(?:\([^)]{0,25}\))?\s*dias?\s*(uteis|corridos)?'),
    re.compile(r'\bem\s+(\d{1,3})\s*\([^)]{0,25}\)\s*dias\s*(uteis|corridos)?'),
]


def extrair_prazo(sent_norm):
    """(dias, corridos?) ou (None, False)."""
    for rx in _PRAZO:
        m = rx.search(sent_norm)
        if m:
            dias = int(m.group(1))
            if 0 < dias <= 180:
                return dias, (m.group(2) == 'corridos')
    if re.search(r'1\.?019,?\s*(inciso\s*)?ii', sent_norm):
        return 15, False  # contrarrazoes ao agravo
    return None, False


_DATA = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')
_HORA = re.compile(r'\b(\d{1,2})\s*(?:h|:)\s*(\d{2})?\s*(?:min|h)?\b')
_DATA_EXTENSO = re.compile(r'\b(\d{1,2}) de (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|'
                           r'outubro|novembro|dezembro) de (\d{4})')
_MESES = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
          'outubro', 'novembro', 'dezembro']


def _evento(sent_norm):
    """Data (DD/MM/AAAA) e hora (HH:MM) mencionadas na frase, se houver."""
    data, hora = '', ''
    m = _DATA.search(sent_norm)
    if m:
        data = f'{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}'
        resto = sent_norm[m.end():m.end() + 30]
    else:
        m = _DATA_EXTENSO.search(sent_norm)
        if m:
            data = f'{int(m.group(1)):02d}/{_MESES.index(m.group(2)) + 1:02d}/{m.group(3)}'
            resto = sent_norm[m.end():m.end() + 30]
        else:
            resto = ''
    h = _HORA.search(resto)
    if h and int(h.group(1)) < 24:
        hora = f'{int(h.group(1)):02d}:{h.group(2) or "00"}'
    return data, hora


def _iso(data_br):
    d, m, a = data_br.split('/')
    return f'{a}-{m}-{d}'


def eventos(sents_norm, a_partir_de=''):
    """Audiencias e pericias com data (para a agenda e o aviso ao cliente).
    Datas anteriores a `a_partir_de` (AAAA-MM-DD, a disponibilizacao) sao historico e ficam fora."""
    achados = []
    for s in sents_norm:
        if re.search(r'deixo de designar|dispens\w* (a )?(realizacao da )?audiencia|cancel\w* (a )?audiencia', s):
            continue
        tipo = None
        if 'audiencia' in s and re.search(r'designo|redesigno|designad|redesignad|marcad|para o dia|sera realizad|fica mantid', s):
            tipo = 'AUDIENCIA'
        elif 'pericia' in s and re.search(r'designad|marcad|agendad|data e local|realizacao|sera realizad|para o dia', s):
            tipo = 'PERICIA'
        if tipo:
            data, hora = _evento(s)
            if data and a_partir_de and _iso(data) < a_partir_de[:10]:
                continue
            if data:
                virtual = bool(re.search(r'videoconferencia|virtual|meet\.google|zoom|teams', s))
                achados.append({'tipo': tipo, 'data': data, 'hora': hora, 'virtual': virtual})
    return achados


# ------------------------------------------------------------------
# REGRAS
# ------------------------------------------------------------------

R_RECURSO_CLASSE = ('agravo de instrumento', 'apelacao', 'recurso especial', 'recurso extraordinario',
                    'agravo interno', 'recurso inominado', 'agravo em recurso')
R_ED = re.compile(r'(rejeito|acolho|nao conheco|conheco|acolhid\w*|rejeitad\w*|provid\w*)[^.]{0,90}'
                  r'embargos (de declaracao|declaratorios)|embargos (de declaracao|declaratorios)[^.]{0,80}'
                  r'(rejeitad|acolhid|nao conhecid|conhecid|parcialmente acolhid)')
R_SENTENCA = re.compile(r'\bjulgo\s+(parcialmente\s+)?(procedente|improcedente)|julgo\s+extint|extingo\s+o\s+'
                        r'(processo|feito)|julgo\s+o\s+processo|homologo[^.]{0,60}acordo|'
                        r'cancel\w*(?:-se)?\s+(a\s+)?distribuicao|'
                        r'julgo\s+(parcialmente\s+)?procedentes|julgo\s+improcedentes|resolvo\s+o\s+merito')
R_TRANSITO = re.compile(r'certific\w*[^.]{0,80}transit\w* em julgado|transitou em julgado|certidao de transito|'
                        r'ocorreu o transito')
R_LIMINAR_SIM = re.compile(r'\b(defiro|concedo|antecipo)\b')
R_LIMINAR_NAO = re.compile(r'\b(indefiro|nego|denego|nao concedo)\b')
R_PENHORA = re.compile(r'\bpenhora\b|\bpenhorad[oa]s?\b|sisbajud|teimosinha|\bbloqueio\b|\barresto\b|'
                       r'constricao|renajud|citad[oa] para pagar|pague[^.]{0,40}\b(3|tres)\b|\bleilao\b|'
                       r'hasta publica|alienacao judicial')
# a constricao so conta quando a frase manda fazer algo (evita narrativa: "distincao entre ... e penhora")
R_ORDEM = re.compile(r'\b(defiro|determino|proceda-se|procedam-se|realize-se|expeca-se|efetue-se|efetivad\w*|'
                     r'efetuad\w*|penhorad\w*|bloquead\w*|converto|mantenho|intime-se|intimem-se|cite-se|'
                     r'autorizo|ordeno|nomeando-se|lavrado)\b')
R_REPLICA = re.compile(r'intimacao \w+ - replica|(apresentar|oferecer|oferecimento de|apresente)\s+replica|'
                       r'para\s+(manifestar-se\s+em\s+)?replica|impugna\w*\s+a\s+contestacao|'
                       r'manifest\w*[^.]{0,30}sobre a contestacao')
R_REPLICA_FUTURA = re.compile(r'^(apresentad[oa]|com a|vindo a|caso seja apresentada|juntada a|oferecida a)\s*'
                              r'(a\s+)?contestacao|apresentada contestacao|^\d+\s*-\s*apresentada')
R_CUSTAS = re.compile(r'emend\w*[^.]{0,30}(inicial|peticao)|recolh\w*[^.]{0,40}custas|comprov\w*[^.]{0,40}'
                      r'(recolhimento|pagamento)[^.]{0,40}custas|custas[^.]{0,80}sob pena|boletos? de custas|'
                      r'guia de custas|cancel\w*(?:-se)? (a )?distribuicao|comprovar[^.]{0,30}hipossuficiencia|'
                      r'indefiro[^.]{0,40}gratuidade|pagamento da 1. parcela das custas')
R_PERICIA = re.compile(r'intimacao \w+ - pericia|pericia[^.]{0,100}(designad|marcad|agendad|data e local|realizacao)|'
                       r'nomeio[^.]{0,40}perit|honorarios periciais|quesitos|laudo pericial|assistente tecnico')
R_MANIFESTA = re.compile(r'(intim\w*|fica\w*|manifest\w*|vista)[^.]{0,220}(manifest\w*|provas|informe|indiq\w*|'
                         r'junt\w*|esclare\w*|ciencia|requer\w*|prosseguimento|impugna\w*|apresent\w*|'
                         r'comprov\w*|regulariz\w*)')
R_CONTESTACAO = re.compile(r'juntada (da|de) contestacao|contestacao (juntada|apresentada) (no|ao|sob) id')


def _primeira(sents, rx, excluir=None):
    for s in sents:
        if rx.search(s) and not (excluir and excluir.search(s)):
            return s
    return None


def classificar(resumo):
    """
    resumo: item de comunica_djen.resumir().
    Retorna dict com categoria, motivo, sinais, polo, prazo, eventos e observacoes.
    """
    bruto = limpar(resumo.get('texto'))
    originais = sentencas(bruto)
    sents = [norm(s) for s in originais]
    t = norm(bruto)
    cauda = ' '.join(sents[-12:]) if sents else t
    tipo_doc = norm(resumo.get('tipo_documento') or resumo.get('tipo') or '')
    classe = norm(resumo.get('classe') or '')
    polo, polo_origem = polo_do_escritorio(t, classe)
    obs, sinais = [], []

    categoria, motivo, frase, favoravel = None, '', None, None

    # sinais secundarios (vao para o relatorio mesmo quando nao definem a categoria)
    for nome, rx in (('custas/emenda', R_CUSTAS), ('pericia', R_PERICIA),
                     ('replica', R_REPLICA), ('embargos de declaracao', R_ED), ('sentenca', R_SENTENCA)):
        if rx.search(t):
            sinais.append(nome)
    frase_constricao = next((s for s in sents if R_PENHORA.search(s) and R_ORDEM.search(s)), None)
    if frase_constricao:
        sinais.append('penhora/bloqueio')
    if re.search(r'defiro[^.]{0,40}gratuidade|gratuidade[^.]{0,30}deferid', t):
        sinais.append('gratuidade deferida')
    if re.search(r'indefiro[^.]{0,40}gratuidade|gratuidade[^.]{0,30}indeferid', t):
        sinais.append('gratuidade indeferida')
    if re.search(r'defiro[^.]{0,40}parcelamento[^.]{0,20}custas', t):
        sinais.append('custas parceladas')

    eh_recurso = tipo_doc.startswith('acordao') or any(k in classe for k in R_RECURSO_CLASSE)

    # 1) embargos de declaracao julgados
    frase = _primeira(sents, R_ED)
    if frase:
        categoria, motivo = 'EMBARGOS_DECLARACAO', 'embargos de declaração julgados'
    # 2) recursos (classe do tribunal ou acordao)
    if not categoria and eh_recurso:
        categoria, motivo = 'RECURSO', f'classe/tipo de recurso ({resumo.get("classe") or resumo.get("tipo_documento")})'
        frase = _primeira(sents, re.compile(r'contrarraz|1\.?019|intime-se o agravad|intime-se a parte agravad')) \
            or _primeira(sents, R_MANIFESTA)
        tut = _primeira(sents, re.compile(r'(tutela|efeito suspensivo|antecipacao)[^.]{0,60}recursal|efeito suspensivo'))
        if tut:
            if R_LIMINAR_NAO.search(tut):
                obs.append('Pedido de tutela recursal/efeito suspensivo INDEFERIDO pelo relator.')
            elif R_LIMINAR_SIM.search(tut):
                obs.append('Pedido de tutela recursal/efeito suspensivo DEFERIDO pelo relator.')
            if polo == 'A':
                obs.append('Escritório parece ser o recorrente: se a tutela recursal foi negada, avaliar agravo interno (15 dias úteis).')
            else:
                obs.append('Escritório parece ser o recorrido: prazo de contrarrazões (art. 1.019, II, CPC).')
        if re.search(r'(dou|deram|dar)\s+(parcial\s+)?provimento|recurso provido', cauda):
            obs.append('Acórdão/decisão DEU provimento ao recurso: conferir de quem era o recurso.')
        elif re.search(r'(nego|negaram|negar)\s+provimento|desprovid|nao provid', cauda):
            obs.append('Acórdão/decisão NEGOU provimento ao recurso: conferir de quem era o recurso.')
    # 3) sentenca
    if not categoria and (tipo_doc.startswith('sentenca') or R_SENTENCA.search(cauda)):
        frase = _primeira(sents, R_SENTENCA) or (sents[-1] if sents else '')
        alvo = frase + ' ' + cauda
        if re.search(r'parcialmente\s+procedente', alvo):
            resultado = 'PARCIAL'
        elif re.search(r'improcedente', alvo):
            resultado = 'IMPROCEDENTE'
        elif re.search(r'procedente', alvo):
            resultado = 'PROCEDENTE'
        elif re.search(r'cancel\w*\s+(a\s+)?distribuicao', alvo):
            resultado = 'EXTINCAO'
            obs.append('Cancelamento da distribuição (art. 290 CPC): custas iniciais não recolhidas.')
        elif re.search(r'homologo[^.]{0,60}acordo', alvo):
            resultado = 'ACORDO'
        elif re.search(r'extint\w*[^.]{0,60}pagamento|satisfacao da obrigacao|924,?\s*(inciso\s*)?ii\b', alvo):
            resultado = 'PAGAMENTO'
            obs.append('Extinção pelo pagamento da obrigação: conferir baixa de restrições e arquivamento.')
        elif re.search(r'extingo|extint|sem resolucao do merito|extincao', alvo):
            resultado = 'EXTINCAO'
        else:
            resultado = ''
        if resultado in ('PROCEDENTE', 'PARCIAL'):
            favoravel = (polo == 'A')
        elif resultado == 'IMPROCEDENTE':
            favoravel = (polo == 'P')
        elif resultado == 'EXTINCAO':
            favoravel = (polo == 'P')
            if re.search(r'prescri', alvo):
                obs.append('Extinção por PRESCRIÇÃO acolhida.')
        motivo = f'sentença ({resultado.lower() or "resultado não identificado"})'
        if resultado == 'PARCIAL':
            obs.append('Procedência PARCIAL: conferir o que foi negado (pode caber recurso).')
        if favoravel is None or polo_origem == 'presumido':
            categoria = 'SENTENCA'
            if polo_origem == 'presumido':
                obs.append('Polo do cliente presumido pela classe: conferir se a sentença é boa ou ruim.')
        else:
            categoria = 'SENTENCA_FAVORAVEL' if favoravel else 'SENTENCA_DESFAVORAVEL'
    # 4) transito em julgado
    if not categoria:
        frase = _primeira(sents, R_TRANSITO)
        if frase:
            categoria, motivo = 'TRANSITO_JULGADO', 'certidão/menção de trânsito em julgado'
    # 5) liminar / tutela de urgencia (so verbo em 1a pessoa na mesma frase)
    if not categoria:
        for s in sents:
            if not re.search(r'tutela|liminar', s):
                continue
            if R_LIMINAR_NAO.search(s):
                categoria, motivo, frase = 'LIMINAR_INDEFERIDA', 'tutela/liminar indeferida', s
                break
            if R_LIMINAR_SIM.search(s) and not re.search(r'requisitos para|para a concessao|exige-se', s):
                categoria, motivo, frase = 'LIMINAR_DEFERIDA', 'tutela/liminar deferida', s
                if 'parcialmente' in s:
                    obs.append('Tutela deferida PARCIALMENTE: conferir o que ficou de fora.')
                break
        if categoria and polo == 'P':
            obs.append('Cliente no polo PASSIVO: a liminar foi pedida CONTRA o cliente (inverter a leitura).')
            categoria = 'REVISAO_MANUAL'
            motivo += ' (cliente no polo passivo)'
    # 6) audiencia e pericia
    evs = eventos(sents, resumo.get('data') or '')
    if not categoria and any(e['tipo'] == 'AUDIENCIA' for e in evs):
        categoria, motivo = 'AUDIENCIA', 'audiência designada'
    if not categoria and (R_PERICIA.search(t) or any(e['tipo'] == 'PERICIA' for e in evs)):
        categoria, motivo = 'PERICIA', 'perícia (designação, honorários, quesitos ou laudo)'
        frase = _primeira(sents, R_PERICIA)
    # 7) execucao / penhora (so frase que manda fazer a constricao)
    if not categoria and frase_constricao:
        frase = frase_constricao
        if polo == 'P' and (polo_origem == 'texto' or any(norm(c) in classe for c in CLASSES_POLO_PASSIVO)):
            categoria, motivo = 'EXECUCAO_PENHORA', 'penhora/bloqueio/constrição contra o cliente'
        elif polo == 'A' and polo_origem == 'texto':
            categoria, motivo = 'MANIFESTACAO', 'execução movida pelo cliente (penhora/pesquisa de bens)'
            obs.append('Execução em que o cliente é o credor: providência de andamento, sem urgência de defesa.')
        else:
            categoria, motivo = 'REVISAO_MANUAL', 'menção a constrição sem saber de que lado o cliente está'
    # 8) replica
    if not categoria:
        frase = _primeira(sents, R_REPLICA, R_REPLICA_FUTURA)
        if frase:
            categoria, motivo = 'REPLICA', 'intimação para réplica'
        elif re.search(r'(apresentad[oa]|vindo)\s+(a\s+)?contestacao', t):
            sinais.append('réplica futura (depois da contestação)')
    # 9) custas / emenda
    if not categoria:
        frase = _primeira(sents, R_CUSTAS)
        if frase:
            categoria, motivo = 'CUSTAS_EMENDA', 'custas/emenda/juntada'
    # 10) contestacao juntada
    if not categoria and R_CONTESTACAO.search(t):
        categoria, motivo, frase = 'CONTESTACAO_JUNTADA', 'contestação juntada', _primeira(sents, R_CONTESTACAO)
    # 11) manifestacao generica
    if not categoria:
        candidatas = [s for s in sents if R_MANIFESTA.search(s)]
        com_prazo = [s for s in candidatas if extrair_prazo(s)[0]]
        pedido = [s for s in candidatas if re.search(r'querendo|manifest|esclarec|provas', s)]
        if com_prazo or pedido:
            frase = (com_prazo or pedido)[0]
            categoria, motivo = 'MANIFESTACAO', 'intimação para manifestação'
        elif candidatas and any('ciencia' in s for s in candidatas):
            frase = next(s for s in candidatas if 'ciencia' in s)
            categoria, motivo = 'DESPACHO', 'intimação só para ciência'
    # 12) despacho sem providencia
    if not categoria:
        if tipo_doc.startswith('despacho') or re.search(r'cite-se|arquivem-se|aguarde-se|cumpra-se', cauda):
            categoria, motivo = 'DESPACHO', 'despacho/decisão de andamento sem prazo identificado'
        else:
            categoria, motivo = 'REVISAO_MANUAL', 'nenhuma regra segura casou'
    if len(bruto) < 120:
        obs.append('Texto da publicação muito curto: abrir o link do DJEN.')

    # ---------------- prazo ----------------
    acao = ACOES[categoria]
    dias, corridos, prazo_origem = None, False, 'sem prazo'
    alvo_prazo = frase or ''
    if alvo_prazo:
        dias, corridos = extrair_prazo(alvo_prazo)
    procurar = categoria in ('MANIFESTACAO', 'CUSTAS_EMENDA', 'REPLICA', 'PERICIA', 'EXECUCAO_PENHORA',
                             'CONTESTACAO_JUNTADA', 'REVISAO_MANUAL')
    if not dias and procurar:  # procura em qualquer frase dirigida ao escritorio
        for s in sents:
            d, c = extrair_prazo(s)
            if not d or R_REPLICA_FUTURA.search(s):
                continue
            if polo == 'A' and re.search(r'cite-se|citacao|contestar|contestacao', s):
                continue  # prazo de defesa e do reu
            if destinatario(s) in (polo, 'AMBOS', None):
                dias, corridos, alvo_prazo = d, c, s
                break
    if dias:
        prazo_origem = 'texto'
    elif acao['prazo_dias']:
        dias, prazo_origem = acao['prazo_dias'], 'padrão CPC'

    dest = destinatario(alvo_prazo) if alvo_prazo else None
    prazo_nosso = True
    if categoria in ('MANIFESTACAO', 'CUSTAS_EMENDA', 'REPLICA', 'PERICIA', 'DESPACHO', 'CONTESTACAO_JUNTADA',
                     'EXECUCAO_PENHORA') and dest in ('A', 'P') and dest != polo:
        prazo_nosso = False
        obs.append('O prazo do texto é da PARTE CONTRÁRIA: só acompanhar.')
    if categoria == 'SENTENCA_FAVORAVEL':
        obs.append('Prazo de 5 dias = embargos de declaração, só se houver omissão/contradição.')

    mesmos = sorted((e for e in evs if e['tipo'] == categoria), key=lambda e: _iso(e['data']))
    ev_principal = mesmos[-1] if mesmos else (evs[-1] if evs else None)  # a data mais nova vale (redesignacao)
    if ev_principal and ev_principal['tipo'] == 'AUDIENCIA' and categoria != 'AUDIENCIA':
        obs.append(f"Há audiência marcada para {ev_principal['data']} {ev_principal['hora']}".strip() + '.')

    chave = alvo_prazo or frase or ''
    frase_original = originais[sents.index(chave)] if chave in sents else chave

    confianca = 'alta' if polo_origem == 'texto' else 'media'
    if categoria in ('REVISAO_MANUAL', 'DESPACHO'):
        confianca = 'baixa'

    return {
        'categoria': categoria,
        'rotulo': acao['rotulo'],
        'motivo': motivo,
        'sinais': sinais,
        'confianca': confianca,
        'polo': polo,
        'polo_origem': polo_origem,
        'favoravel': favoravel,
        'prazo_dias': dias if prazo_nosso else None,
        'prazo_dias_texto': dias,
        'prazo_corridos': corridos,
        'prazo_origem': prazo_origem if prazo_nosso else 'prazo da parte contrária',
        'prazo_nosso': prazo_nosso,
        'eventos': evs,
        'evento': ev_principal,
        'frase_chave': frase_original[:400],
        'observacoes': obs,
    }

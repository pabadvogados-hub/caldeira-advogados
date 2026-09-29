"""
Pecas comuns da Controladoria (fases 5-6) e da Gestao (pauta/auditoria/gargalos).

- de onde vem cada dado: ADVBOX (so leitura, ritmado) ou dados_exemplo (--exemplo);
- equipe: cargo de cada usuario do ADVBOX (config/equipe.py);
- casos da pasta do cliente (caso.json): fase, notificacao enviada, inicial protocolada;
- tarefa do ADVBOX num formato unico (quem, tipo, criada, prazo, concluida);
- CSV para revisao (ponto-e-virgula, abre direto no Excel).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import date, datetime, timedelta  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
CONTRATACAO_DIR = os.path.join(ambiente.RAIZ, 'CONTRATACAO')
if CONTRATACAO_DIR not in sys.path:
    sys.path.append(CONTRATACAO_DIR)

import dados_exemplo as ex  # noqa: E402
from configuracao import FASES_ENCERRADAS  # noqa: E402
from config.equipe import CARGOS, REMETENTE_TAREFAS  # noqa: E402

CARGO_LEGIVEL = {
    'SDR': 'SDR', 'CLOSER': 'Closer', 'GESTOR_JURIDICO': 'Gestor Jurídico',
    'COORDENADOR_JURIDICO': 'Coordenador Jurídico', 'ADV_EXTRAJUDICIAL': 'Adv. Extrajudicial',
    'ADV_JUDICIAL': 'Adv. Judicial', 'ESTAGIARIO': 'Estagiário', 'FINANCEIRO': 'Financeiro',
}


# ------------------------------------------------------------------
# DATAS
# ------------------------------------------------------------------

def hoje():
    """HOJE_SIMULADO=AAAA-MM-DD no ambiente serve so para teste."""
    simulado = os.getenv('HOJE_SIMULADO')
    return date.fromisoformat(simulado) if simulado else date.today()


def data(txt):
    """date a partir de 'AAAA-MM-DD[...]' ou 'DD/MM/AAAA'; None se vazio/invalido."""
    if isinstance(txt, datetime):
        return txt.date()
    if isinstance(txt, date):
        return txt
    txt = str(txt or '').strip()
    for fmt, n in (('%Y-%m-%d', 10), ('%d/%m/%Y', 10)):
        try:
            return datetime.strptime(txt[:n], fmt).date()
        except ValueError:
            continue
    return None


def br(d):
    d = data(d)
    return d.strftime('%d/%m/%Y') if d else ''


def semana(ref=None):
    """(segunda, sexta) da semana de `ref`."""
    ref = ref or hoje()
    seg = ref - timedelta(days=ref.weekday())
    return seg, seg + timedelta(days=4)


def digitos(s):
    return ''.join(c for c in str(s or '') if c.isdigit())


def nome_proprio(txt):
    """'JOSE DA SILVA' -> 'Jose da Silva'; 'BANCO X S.A.' -> 'Banco X S.A.'"""
    minusculas = {'de', 'da', 'do', 'das', 'dos', 'e'}
    saida = []
    for n, p in enumerate(str(txt or '').split()):
        if p.upper() in ('S.A.', 'S/A', 'SA', 'LTDA', 'LTDA.', 'ME', 'EPP', 'CEF', 'BB'):
            saida.append(p.upper())
        elif n and p.lower() in minusculas:
            saida.append(p.lower())
        else:
            saida.append(p.capitalize())
    return ' '.join(saida)


# ------------------------------------------------------------------
# EQUIPE
# ------------------------------------------------------------------

def cargos(exemplo=False):
    return ex.CARGOS_EXEMPLO if exemplo else CARGOS


def cargo_do_usuario(uid=None, nome=None, exemplo=False):
    uid, nome = str(uid or ''), (nome or '').upper()
    for chave, c in cargos(exemplo).items():
        if uid and str(c.get('advbox_id') or '') == uid:
            return chave
    for chave, c in cargos(exemplo).items():
        if nome and c.get('nome') and c['nome'].upper() in nome:
            return chave
    return None


def rotulo_pessoa(uid=None, nome=None, exemplo=False):
    cargo = cargo_do_usuario(uid, nome, exemplo)
    nome = nome or (cargos(exemplo).get(cargo, {}).get('nome') if cargo else '') or 'Sem responsável'
    return f'{nome} ({CARGO_LEGIVEL.get(cargo, cargo)})' if cargo else nome


def id_do_cargo(cargo, exemplo=False):
    return str((cargos(exemplo).get(cargo) or {}).get('advbox_id') or '')


def remetente(exemplo=False):
    return id_do_cargo(REMETENTE_TAREFAS, exemplo)


# ------------------------------------------------------------------
# ADVBOX (ou exemplo)
# ------------------------------------------------------------------

def tem_advbox():
    return ambiente.tem_credencial('ADVBOX_API_TOKEN')


_AVISOU = set()


def aviso_sem_advbox(o_que):
    if o_que in _AVISOU:
        return
    _AVISOU.add(o_que)
    print(f'   AVISO: sem ADVBOX_API_TOKEN no config/.env. Ficou de fora: {o_que} (modo seguro).')
    print('          Para ver o formato completo com dados fictícios, rode com --exemplo.')


def processos(exemplo=False):
    """Processos do ADVBOX (lista crua) ou None se nao ha credencial."""
    if exemplo:
        return ex.processos()
    if not tem_advbox():
        return None
    import advbox_integration as advbox
    print('   ADVBOX: lendo processos (paginado, respeitando 30 GET/min)...')
    return advbox.listar_processos_todos()


def processo_ativo(p):
    fase = (p.get('stage') or '').upper()
    if any(f in fase for f in FASES_ENCERRADAS):
        return False
    return not (p.get('status_closure') or p.get('date_closure'))


def cliente_do_processo(p):
    clientes = (p or {}).get('customers') or []
    return (clientes[0].get('name') if clientes else '') or ''


def id_cliente_do_processo(p):
    clientes = (p or {}).get('customers') or []
    return str((clientes[0].get('customer_id') or clientes[0].get('customers_id') or clientes[0].get('id'))
               if clientes else '')


_TELEFONES = {}


def telefone_do_processo(p, exemplo=False):
    """Celular do cliente: do proprio processo, senao da lista /customers do ADVBOX (lida uma vez)."""
    clientes = (p or {}).get('customers') or []
    if clientes and (clientes[0].get('cellphone') or clientes[0].get('phone')):
        return clientes[0].get('cellphone') or clientes[0].get('phone')
    if exemplo or not tem_advbox():
        return ''
    if not _TELEFONES:
        import advbox_integration as advbox
        print('   ADVBOX: lendo telefones dos clientes (/customers)...')
        for c in advbox.paginar_ritmado('/customers'):
            _TELEFONES[str(c.get('id'))] = c.get('cellphone') or c.get('phone') or ''
        _TELEFONES.setdefault('_lido', '1')
    return _TELEFONES.get(id_cliente_do_processo(p), '')


def normalizar_tarefa(t):
    lawsuit = t.get('lawsuit') or {}
    clientes = lawsuit.get('customers') or []
    pessoas = []
    for u in t.get('users') or []:
        pessoas.append({
            'id': str(u.get('id') or u.get('user_id') or ''),
            'nome': u.get('name') or '',
            'concluida_em': str(u.get('completed') or '')[:19],
            'urgente': bool(u.get('urgent') or u.get('important')),
        })
    return {
        'id': t.get('id'),
        'tipo': (t.get('task') or '').strip() or 'SEM TIPO',
        'criada_em': str(t.get('created_at') or t.get('date') or '')[:19],
        'inicio': str(t.get('date') or t.get('start') or '')[:10],
        'prazo': str(t.get('date_deadline') or '')[:10],
        'processo_id': t.get('lawsuits_id') or lawsuit.get('id'),
        'processo': lawsuit.get('process_number') or '',
        'cliente': (clientes[0].get('name') if clientes else '') or '',
        'texto': t.get('comments') or t.get('notes') or '',
        'pessoas': pessoas,
    }


def tarefas(exemplo=False, **filtros):
    """Tarefas normalizadas, ou None sem credencial. Filtros no padrao do /posts (pares de data)."""
    if exemplo:
        return [normalizar_tarefa(t) for t in ex.tarefas()]
    if not tem_advbox():
        return None
    import advbox_integration as advbox
    print(f'   ADVBOX: lendo tarefas {filtros or ""}...')
    return [normalizar_tarefa(t) for t in advbox.listar_tarefas_ritmado(**filtros)]


def movimentacoes(inicio, fim, exemplo=False):
    """[{processo_id, data, descricao}] no periodo, ou None sem credencial."""
    if exemplo:
        brutas = ex.movimentacoes()
    elif not tem_advbox():
        return None
    else:
        import advbox_integration as advbox
        print(f'   ADVBOX: lendo movimentações de {br(inicio)} a {br(fim)}...')
        brutas = advbox.listar_movimentacoes_periodo(str(inicio), str(fim))
    saida = []
    for m in brutas:
        d = data(m.get('date') or m.get('created_at'))
        if d and data(inicio) <= d <= data(fim):
            saida.append({'processo_id': m.get('lawsuit_id') or m.get('lawsuits_id') or m.get('id_lawsuit'),
                          'processo': m.get('process_number') or '',
                          'data': d, 'descricao': (m.get('description') or m.get('title') or '').strip()})
    return saida


# ------------------------------------------------------------------
# CASOS (caso.json das pastas de clientes)
# ------------------------------------------------------------------

def casos(exemplo=False):
    """[(pasta, caso)] dos clientes do escritorio (o que nao esta ENCERRADO)."""
    if exemplo:
        return ex.casos()
    from pasta_cliente import listar_casos
    return [(b, c) for b, c in listar_casos() if c.get('etapa') != 'ENCERRADO']


def nome_do_caso(caso):
    return ((caso.get('qualificacao') or {}).get('nome') or caso.get('id') or '').strip()


def notificacoes(caso):
    extra = caso.get('extrajudicial') or {}
    if isinstance(extra, list):
        return [n for n in extra if isinstance(n, dict)]
    return [n for n in (extra.get('notificacoes') or []) if isinstance(n, dict)]


def notificacao_enviada_em(caso):
    datas = [data(n.get('enviada_em')) for n in notificacoes(caso)]
    datas = [d for d in datas if d]
    return min(datas) if datas else None


def pecas_judiciais(caso):
    j = caso.get('judicial') or []
    if isinstance(j, dict):
        j = j.get('pecas') or [j]
    return [p for p in j if isinstance(p, dict)]


def inicial_protocolada_em(caso):
    """Data do protocolo da inicial, se algum modulo registrou; senao None."""
    for chave in ('inicial_protocolada_em', 'protocolo_inicial_em'):
        if data(caso.get(chave)):
            return data(caso.get(chave))
    for p in pecas_judiciais(caso):
        if 'inicial' in str(p.get('tipo') or '').lower():
            for chave in ('protocolada_em', 'protocolado_em', 'protocolo_em'):
                if data(p.get(chave)):
                    return data(p.get(chave))
    return None


def fase_do_caso(caso):
    etapa = (caso.get('etapa') or '').upper()
    if etapa == 'ENCERRADO':
        return 'ENCERRADO'
    if inicial_protocolada_em(caso) or 'ACOMPANHAMENTO' in etapa or 'PROTOCOLAD' in etapa:
        return 'JUDICIAL'
    if 'JUDICIAL' in etapa and 'EXTRAJUDICIAL' not in etapa:
        return 'JUDICIAL (preparando a inicial)'
    if notificacoes(caso) or 'EXTRAJUDICIAL' in etapa or 'NOTIFICA' in etapa:
        return 'EXTRAJUDICIAL'
    return 'CONTRATAÇÃO'


def prazo_do_caso(caso, marco):
    for p in caso.get('prazos') or []:
        if p.get('id') == marco:
            return data(p.get('data'))
    return None


def documentos_faltando(caso):
    return [s for s in caso.get('documentos_status') or []
            if s.get('obrigatorio') and s.get('situacao') not in ('NA PASTA', 'JA ENTREGOU')
            and not s.get('sensivel')]


def marcos_do_caso(caso, ref=None):
    """Situacao dos marcos 15/60 dias: [{'marco','limite','feito_em','dias_restantes','situacao'}]."""
    ref = ref or hoje()
    saida = []
    for marco, feito in (('notificacao', notificacao_enviada_em(caso)), ('inicial', inicial_protocolada_em(caso))):
        limite = prazo_do_caso(caso, marco)
        if not limite:
            continue
        if feito:
            situacao = 'CUMPRIDO NO PRAZO' if feito <= limite else 'CUMPRIDO COM ATRASO'
        elif ref > limite:
            situacao = 'ESTOUROU'
        elif (limite - ref).days <= 5:
            situacao = 'PERTO DO LIMITE'
        else:
            situacao = 'NO PRAZO'
        saida.append({'marco': marco, 'limite': limite, 'feito_em': feito,
                      'dias_restantes': (limite - ref).days, 'situacao': situacao})
    return saida


# ------------------------------------------------------------------
# SAIDA
# ------------------------------------------------------------------

def pasta_saida(*partes):
    return ambiente.pasta_saida(*partes)


def salvar_csv(caminho, linhas, campos=None):
    campos = campos or (list(linhas[0].keys()) if linhas else ['vazio'])
    with open(caminho, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=';', extrasaction='ignore')
        w.writeheader()
        w.writerows(linhas)
    return caminho


def ler_csv(caminho):
    with open(caminho, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f, delimiter=';'))


def console_utf8():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

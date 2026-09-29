"""
Coleta comum da GESTAO (pauta de segunda, auditoria de sexta, gargalos).

Tudo so leitura: tarefas do ADVBOX (/posts, ritmado), casos das pastas (caso.json),
varreduras salvas pela Controladoria (publicacoes do DJEN ja classificadas).
Sem ADVBOX_API_TOKEN, a parte do ADVBOX sai vazia com aviso (modo seguro).
"""
import os
import statistics
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import defaultdict  # noqa: E402
from datetime import timedelta  # noqa: E402

sys.path.insert(0, os.path.join(RAIZ, 'CONTROLADORIA'))
import comum  # noqa: E402  (CONTROLADORIA/comum.py)
import saidas_varredura  # noqa: E402

hoje = comum.hoje
br = comum.br
data = comum.data


def semana_de_trabalho(ref=None):
    """(segunda, sexta). No fim de semana, a semana que vem."""
    ref = ref or hoje()
    if ref.weekday() >= 5:
        ref = ref + timedelta(days=7 - ref.weekday())
    return comum.semana(ref)


def tarefas(exemplo=False, **filtros):
    """Tarefas normalizadas (lista) ou [] com aviso quando nao ha credencial."""
    t = comum.tarefas(exemplo, **filtros)
    if t is None:
        comum.aviso_sem_advbox('as tarefas do ADVBOX')
        return []
    return t


def por_pessoa(lista_tarefas, exemplo=False):
    """{rotulo da pessoa: [(tarefa, participacao da pessoa)]}"""
    saida = defaultdict(list)
    for t in lista_tarefas:
        for p in t['pessoas'] or [{'id': '', 'nome': 'Sem responsável', 'concluida_em': '', 'urgente': False}]:
            saida[comum.rotulo_pessoa(p['id'], p['nome'], exemplo)].append((t, p))
    return saida


def concluida_em(p):
    return data(p.get('concluida_em'))


def dias_para_concluir(t, p):
    ini, fim = data(t['criada_em']) or data(t['inicio']), concluida_em(p)
    return (fim - ini).days if ini and fim else None


def media(valores):
    v = [x for x in valores if x is not None]
    return round(statistics.mean(v), 1) if v else None


def mediana(valores):
    v = [x for x in valores if x is not None]
    return round(statistics.median(v), 1) if v else None


def casos(exemplo=False):
    return comum.casos(exemplo)


def publicacoes(desde=None, ate=None, exemplo=False):
    return saidas_varredura.historico(desde, ate, exemplo)


def cargos_ordem():
    return ['GESTOR_JURIDICO', 'COORDENADOR_JURIDICO', 'ADV_JUDICIAL', 'ADV_EXTRAJUDICIAL', 'ESTAGIARIO',
            'CLOSER', 'SDR', 'FINANCEIRO']


def ordem_pessoa(rotulo):
    for n, c in enumerate(cargos_ordem()):
        if f'({comum.CARGO_LEGIVEL.get(c)})' in rotulo:
            return (n, rotulo)
    return (99, rotulo)


def pasta_gestao(*partes):
    return comum.pasta_saida('gestao', *partes)


def dia_semana(d):
    return ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][d.weekday()] if d else ''

"""
Calculo PRELIMINAR de prazo processual a partir da publicacao no DJEN.

Regra usada (Lei 11.419/2006, art. 4, par. 3 e 4; CPC arts. 219, 220 e 224):
  - disponibilizacao no DJEN no dia D;
  - publicacao = 1o dia util seguinte a D;
  - o prazo comeca no 1o dia util seguinte a publicacao (exclui o dia do comeco);
  - conta so dias uteis (CPC art. 219), salvo quando o texto diz "dias corridos";
  - de 20/12 a 20/01 os prazos ficam suspensos (CPC art. 220).

Feriados: so os nacionais certos + FERIADOS_EXTRAS do .env (locais, DD/MM ou DD/MM/AAAA).
Carnaval e Corpus Christi NAO sao pulados de proposito: na duvida o calculo fica
mais CEDO, nunca mais tarde. Sempre "preliminar, conferir no processo".

Prazo interno = D-N dias uteis do fatal (PRAZO_INTERNO_DIAS_ANTES, padrao 3).
"""
import os
from datetime import date, datetime, timedelta


def _pascoa(ano):
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mes = (h + l_ - 7 * m + 114) // 31
    dia = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


_FIXOS = ('01/01', '21/04', '01/05', '07/09', '12/10', '02/11', '15/11', '20/11', '25/12')
_cache = {}


def feriados(ano):
    if ano in _cache:
        return _cache[ano]
    dias = {datetime.strptime(f'{d}/{ano}', '%d/%m/%Y').date() for d in _FIXOS}
    dias.add(_pascoa(ano) - timedelta(days=2))  # sexta-feira santa
    for item in (os.getenv('FERIADOS_EXTRAS') or '').split(','):
        item = item.strip()
        if not item:
            continue
        try:
            if item.count('/') == 1:
                dias.add(datetime.strptime(f'{item}/{ano}', '%d/%m/%Y').date())
            else:
                d = datetime.strptime(item, '%d/%m/%Y').date()
                if d.year == ano:
                    dias.add(d)
        except ValueError:
            continue
    _cache[ano] = dias
    return dias


def em_recesso(d):
    """20/12 a 20/01: prazos suspensos (CPC art. 220)."""
    return (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 20)


def dia_util(d, contar_recesso=False):
    if d.weekday() >= 5 or d in feriados(d.year):
        return False
    if not contar_recesso and em_recesso(d):
        return False
    return True


def proximo_dia_util(d):
    d += timedelta(days=1)
    while not dia_util(d):
        d += timedelta(days=1)
    return d


def somar_dias_uteis(d, n):
    for _ in range(n):
        d = proximo_dia_util(d)
    return d


def subtrair_dias_uteis(d, n):
    for _ in range(n):
        d -= timedelta(days=1)
        while not dia_util(d):
            d -= timedelta(days=1)
    return d


def dias_uteis_entre(inicio, fim):
    """Dias uteis de inicio (exclusive) ate fim (inclusive). Negativo se fim < inicio."""
    if fim == inicio:
        return 0
    sinal = 1 if fim > inicio else -1
    a, b = (inicio, fim) if sinal == 1 else (fim, inicio)
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if dia_util(d):
            n += 1
    return n * sinal


def _data(txt):
    if isinstance(txt, date):
        return txt
    txt = (txt or '').strip()[:10]
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def data_publicacao(disponibilizacao):
    d = _data(disponibilizacao)
    return proximo_dia_util(d) if d else None


def prazo_fatal(disponibilizacao, dias, corridos=False):
    """Data fatal preliminar. None se faltar dado."""
    pub = data_publicacao(disponibilizacao)
    if not pub or not dias:
        return None
    if not corridos:
        return somar_dias_uteis(pub, int(dias))
    fim = pub + timedelta(days=int(dias))
    while not dia_util(fim):
        fim += timedelta(days=1)
    return fim


def prazo_interno(fatal, dias_antes=3, hoje=None):
    """D-N (dias uteis) do fatal; nunca antes de hoje. Retorna (data, atrasado?)."""
    if not fatal:
        return None, False
    hoje = hoje or date.today()
    interno = subtrair_dias_uteis(fatal, dias_antes)
    if interno < hoje:
        return hoje, True
    return interno, False


def br(d):
    return d.strftime('%d/%m/%Y') if d else ''

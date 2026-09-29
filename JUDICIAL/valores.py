"""
Valores em reais: leitura do que veio da triagem ("R$ 1.200.000,00", "1,2 milhao", "310 mil",
"aprox. R$ 300 mil") e escrita por extenso para o valor da causa.
"""
import re
import unicodedata

UNIDADES = ['', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez', 'onze', 'doze',
            'treze', 'catorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove']
DEZENAS = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa']
CENTENAS = ['', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos', 'seiscentos', 'setecentos',
            'oitocentos', 'novecentos']
ESCALAS = [('', ''), ('mil', 'mil'), ('milhão', 'milhões'), ('bilhão', 'bilhões')]

APROXIMADO = re.compile(r'aprox|cerca|em torno|mais ou menos|~|uns |umas |estimad', re.I)


def _sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def _ate_999(n):
    if n == 0:
        return ''
    if n == 100:
        return 'cem'
    c, resto = divmod(n, 100)
    partes = [CENTENAS[c]] if c else []
    if resto:
        if resto < 20:
            partes.append(UNIDADES[resto])
        else:
            d, u = divmod(resto, 10)
            partes.append(DEZENAS[d] + (f' e {UNIDADES[u]}' if u else ''))
    return ' e '.join(partes)


def _inteiro_extenso(n):
    if n == 0:
        return 'zero'
    grupos = []
    while n:
        n, g = divmod(n, 1000)
        grupos.append(g)
    partes = []
    for i in range(len(grupos) - 1, -1, -1):
        g = grupos[i]
        if not g:
            continue
        if i == 1 and g == 1:
            txt = 'mil'
        else:
            txt = _ate_999(g)
            if i:
                txt += ' ' + (ESCALAS[i][0] if g == 1 else ESCALAS[i][1])
        partes.append((i, g, txt))
    saida = ''
    for k, (i, g, txt) in enumerate(partes):
        if k == 0:
            saida = txt
        else:
            # "e" antes do ultimo grupo quando ele e < 100 ou centena redonda
            ultimo = k == len(partes) - 1
            usa_e = ultimo and (g < 100 or g % 100 == 0)
            saida += (' e ' if usa_e else ', ') + txt
    return saida


def por_extenso(valor):
    """1234567.89 -> 'um milhão, duzentos e trinta e quatro mil, quinhentos e sessenta e sete reais e oitenta e nove centavos'"""
    centavos_total = int(round(valor * 100))
    reais, centavos = divmod(centavos_total, 100)
    partes = []
    if reais:
        txt = _inteiro_extenso(reais)
        redondo_milhao = reais >= 1_000_000 and reais % 1_000_000 == 0
        moeda = 'real' if reais == 1 else 'reais'
        partes.append(f"{txt}{' de' if redondo_milhao else ''} {moeda}")
    if centavos:
        partes.append(f"{_inteiro_extenso(centavos)} {'centavo' if centavos == 1 else 'centavos'}")
    return ' e '.join(partes) or 'zero reais'


def brl(valor):
    """1234567.8 -> 'R$ 1.234.567,80'"""
    s = f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {s}'


def ler_valor(texto):
    """
    Le o primeiro valor em reais de um texto livre. Retorna (valor_float, aproximado_bool) ou (None, False).
    Aceita 'R$ 1.200.000,00', '1.200.000', '1,2 milhão', 'R$ 310 mil', 'um milhão e duzentos' nao (fala).
    """
    if not texto:
        return None, False
    t = _sem_acento(str(texto).lower())
    aprox = bool(APROXIMADO.search(t))
    candidatos = []
    for m in re.finditer(r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*'
                         r'(mil\b|milhao|milhoes|mi\b|bilhao|bilhoes)?', t):
        try:
            v = float(m.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            continue
        mult = m.group(2) or ''
        if mult == 'mil':
            v *= 1_000
        elif mult in ('milhao', 'milhoes', 'mi'):
            v *= 1_000_000
        elif mult in ('bilhao', 'bilhoes'):
            v *= 1_000_000_000
        com_rs = 'r$' in t[max(0, m.start() - 4):m.start()]
        if v >= 100 or com_rs:  # "2 parcelas", "15 de outubro", "40/0254" nao sao valor de divida
            candidatos.append((not com_rs, m.start(), v))
    if not candidatos:
        return None, aprox
    return sorted(candidatos)[0][2], aprox

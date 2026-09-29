"""
Artes dos posts em PNG (Pillow), no padrao visual do Caldeira Advogados Associados.

- Carrossel e estatico: 1080x1350 (4:5). Story: 1080x1920 (9:16).
- Cores: grafite #20201F, laranja #C45911 (texto destacado em fundo escuro usa o tom claro #EA8A4E
  para ter contraste), papel #FBF8F4. Logo no canto, numeracao do slide, margens seguras.
- Texto quebrado automaticamente: a fonte diminui ate caber; se nem no tamanho minimo couber,
  o texto e cortado com "..." e o aviso volta para o relatorio (encurtar o texto).
- **palavra** no texto = destaque em laranja. Linha comecando com "- " = item de lista.
- Fontes do sistema com reserva (Windows C:\\Windows\\Fonts; Mac /System/Library/Fonts, /Library/Fonts e
  ~/Library/Fonts; Linux /usr/share/fonts): Georgia/Times New Roman no titulo, Arial/Helvetica no corpo. Para usar as
  fontes da marca, coloque os .ttf em config/fontes/ (titulo.ttf, corpo.ttf, corpo_negrito.ttf).
- NADA de imagem gerada por IA: so texto, formas e o logo do escritorio.
- Material bloqueado pela conformidade sai com faixa vermelha "NAO PUBLICAR ATE CORRIGIR".

Teste visual sem IA:
    python MARKETING/arte.py --demo [--tema claro|escuro] [--saida PASTA]
"""
import argparse
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(RAIZ, 'config', 'logo_caldeira.png')
PASTA_FONTES_MARCA = os.path.join(RAIZ, 'config', 'fontes')

TAM_FEED = (1080, 1350)
TAM_STORY = (1080, 1920)
MARGEM = 96

LARANJA = '#C45911'
LARANJA_CLARO = '#EA8A4E'     # destaque de texto sobre fundo escuro (contraste)
ESCURO = '#20201F'
PAPEL = '#FBF8F4'
VERMELHO = '#B3261E'

TEMAS = {
    'claro': {'fundo': PAPEL, 'texto': ESCURO, 'texto2': '#46423F', 'suave': '#857D75', 'linha': '#E2D8CC',
              'destaque': LARANJA, 'barra': LARANJA, 'logo': 'normal'},
    'escuro': {'fundo': ESCURO, 'texto': '#F5F1EB', 'texto2': '#D9D2C8', 'suave': '#A39B92', 'linha': '#3A3937',
               'destaque': LARANJA_CLARO, 'barra': LARANJA, 'logo': 'claro'},
    'laranja': {'fundo': LARANJA, 'texto': '#FFFFFF', 'texto2': '#FFF4EC', 'suave': '#FBE3D3', 'linha': '#D9773A',
                'destaque': '#FFFFFF', 'barra': '#FFFFFF', 'logo': 'branco'},
}

HANDLE = '@caldeira.advogados'
IDENTIFICACAO = 'Caldeira Advogados Associados · Dr. Augusto Alves Caldeira · OAB/RO 11.101'
AVISO_INFORMATIVO = 'Conteúdo informativo. Não substitui a análise do caso concreto.'

try:
    sys.path.insert(0, RAIZ)
    from config.escritorio import ESCRITORIO, TITULAR  # noqa: E402
    HANDLE = ESCRITORIO.get('instagram') or HANDLE
    IDENTIFICACAO = f"{ESCRITORIO['nome']} · Dr. {TITULAR['nome']} · {TITULAR['oab']}"
except Exception:  # noqa: BLE001 - arte funciona mesmo sem o config
    pass

# ============================================================
# FONTES
# ============================================================

_CANDIDATAS = {
    # titulo em serifa (conversa com o logo e com o timbrado das pecas).
    # Nomes do Windows (georgiab.ttf), do Mac ("Georgia Bold.ttf", em /System/Library/Fonts/Supplemental)
    # e do Linux (DejaVu/Liberation/Noto). A busca ignora maiusculas/minusculas.
    'titulo': ['titulo.ttf', 'georgiab.ttf', 'Georgia Bold.ttf', 'DejaVuSerif-Bold.ttf', 'LiberationSerif-Bold.ttf',
               'NotoSerif-Bold.ttf', 'timesbd.ttf', 'Times New Roman Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf',
               'DejaVuSans-Bold.ttf'],
    'corpo': ['corpo.ttf', 'segoeui.ttf', 'arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf',
              'NotoSans-Regular.ttf', 'calibri.ttf', 'Helvetica.ttc', 'HelveticaNeue.ttc'],
    'corpo_negrito': ['corpo_negrito.ttf', 'segoeuib.ttf', 'arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf',
                      'LiberationSans-Bold.ttf', 'NotoSans-Bold.ttf', 'calibrib.ttf'],
}
_PASTAS_FONTES = [
    PASTA_FONTES_MARCA,
    # Windows
    os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts'),
    # Mac (Georgia, Times New Roman e Arial ficam em Supplemental; Helvetica em /System/Library/Fonts)
    '/System/Library/Fonts', '/System/Library/Fonts/Supplemental', '/Library/Fonts',
    os.path.expanduser('~/Library/Fonts'),
    # Linux / VPS
    '/usr/share/fonts', '/usr/local/share/fonts',
    os.path.expanduser('~/.fonts'), os.path.expanduser('~/.local/share/fonts'),
]
_indice_fontes = None
_cache_fontes = {}


def _indexar_fontes():
    global _indice_fontes
    if _indice_fontes is None:
        _indice_fontes = {}
        for pasta in _PASTAS_FONTES:
            if not pasta or not os.path.isdir(pasta):
                continue
            for raiz, _dirs, arquivos in os.walk(pasta):
                for a in arquivos:
                    if a.lower().endswith(('.ttf', '.otf', '.ttc')):   # .ttc: Helvetica do Mac
                        _indice_fontes.setdefault(a.lower(), os.path.join(raiz, a))
    return _indice_fontes


def caminho_fonte(familia):
    indice = _indexar_fontes()
    for nome in _CANDIDATAS[familia]:
        if nome.lower() in indice:
            return indice[nome.lower()]
    return None


def fonte(familia, tamanho):
    chave = (familia, tamanho)
    if chave not in _cache_fontes:
        caminho = caminho_fonte(familia)
        if caminho:
            _cache_fontes[chave] = ImageFont.truetype(caminho, tamanho)
        else:
            _cache_fontes[chave] = ImageFont.load_default(size=tamanho)
    return _cache_fontes[chave]


def fontes_em_uso():
    return {f: (caminho_fonte(f) or 'fonte padrão do Pillow') for f in _CANDIDATAS}


# ============================================================
# LOGO (fundo branco do PNG vira transparente; versoes para fundo escuro e laranja)
# ============================================================

_cache_logo = {}


def _logo(variante, largura):
    chave = (variante, largura)
    if chave in _cache_logo:
        return _cache_logo[chave]
    if not os.path.exists(LOGO):
        _cache_logo[chave] = None
        return None
    im = Image.open(LOGO).convert('RGB')
    claro = (245, 241, 235)
    escuro = (32, 32, 31)
    saida = []
    pixels = im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata()
    for r, g, b in pixels:
        mx, mn = max(r, g, b), min(r, g, b)
        neutro = (mx - mn) < 40
        if neutro:
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            a = max(0.0, min(1.0, (255 - lum) / (255 - 40)))
            cor = {'normal': escuro, 'claro': claro, 'branco': (255, 255, 255)}[variante]
        else:
            a = max(0.0, min(1.0, (255 - mn) / 145))
            cor = (255, 255, 255) if variante == 'branco' else (r, g, b)
        saida.append((*cor, int(round(a * 255))))
    rgba = Image.new('RGBA', im.size)
    rgba.putdata(saida)
    altura = round(im.height * largura / im.width)
    rgba = rgba.resize((largura, altura), Image.LANCZOS)
    _cache_logo[chave] = rgba
    return rgba


def _colar_logo(img, variante, largura, x, y):
    logo = _logo(variante, largura)
    if logo is not None:
        img.alpha_composite(logo, (int(x), int(y)))
        return logo.size
    return (0, 0)


# ============================================================
# TEXTO COM QUEBRA AUTOMATICA E DESTAQUE
# ============================================================

def _paragrafos(texto):
    """[{marcador, palavras}] onde palavra = lista de (pedaco, destaque)."""
    saida = []
    for bruto in str(texto or '').replace('\r', '').split('\n'):
        linha = bruto.strip()
        if not linha:
            continue
        marcador = False
        if re.match(r'^([-•*]|\d+[.)])\s+', linha) and not linha.startswith('**'):
            marcador = True
            linha = re.sub(r'^([-•*]|\d+[.)])\s+', '', linha)
        palavras, atual, pedaco, destaque = [], [], '', False
        for tk in re.split(r'(\*\*)', linha):
            if tk == '**':
                if pedaco:
                    atual.append((pedaco, destaque))
                    pedaco = ''
                destaque = not destaque
                continue
            for ch in tk:
                if ch.isspace():
                    if pedaco:
                        atual.append((pedaco, destaque))
                        pedaco = ''
                    if atual:
                        palavras.append(atual)
                        atual = []
                else:
                    pedaco += ch
            if pedaco:
                atual.append((pedaco, destaque))
                pedaco = ''
        if atual:
            palavras.append(atual)
        if palavras:
            saida.append({'marcador': marcador, 'palavras': palavras})
    return saida


def _larg_palavra(palavra, f, fd):
    return sum((fd if d else f).getlength(t) for t, d in palavra)


def _partir_palavra(palavra, f, fd, largura):
    """Palavra maior que a linha (ex.: link): quebra por caractere."""
    pedacos, atual = [], []
    for t, d in palavra:
        for ch in t:
            teste = atual + [(ch, d)]
            if atual and _larg_palavra(teste, f, fd) > largura:
                pedacos.append(atual)
                atual = [(ch, d)]
            else:
                atual = teste
    if atual:
        pedacos.append(atual)
    return pedacos


def _quebrar(paragrafos, f, fd, largura, recuo_marcador):
    linhas = []
    espaco = f.getlength(' ')
    for p in paragrafos:
        disponivel = largura - (recuo_marcador if p['marcador'] else 0)
        atual, larg = [], 0.0
        primeira = True
        palavras = []
        for w in p['palavras']:
            if _larg_palavra(w, f, fd) > disponivel:
                palavras.extend(_partir_palavra(w, f, fd, disponivel))
            else:
                palavras.append(w)
        for w in palavras:
            lw = _larg_palavra(w, f, fd)
            extra = lw if not atual else espaco + lw
            if atual and larg + extra > disponivel:
                linhas.append({'palavras': atual, 'marcador': p['marcador'] and primeira,
                               'recuo': p['marcador'], 'fim': False})
                primeira = False
                atual, larg = [w], lw
            else:
                atual.append(w)
                larg += extra
        if atual:
            linhas.append({'palavras': atual, 'marcador': p['marcador'] and primeira, 'recuo': p['marcador'], 'fim': True})
    return linhas


def _altura(linhas, tamanho, entre, gap_par):
    if not linhas:
        return 0
    h = len(linhas) * tamanho * entre
    h += sum(1 for ln in linhas[:-1] if ln['fim']) * tamanho * gap_par
    return h


def ajustar_texto(texto, familia, familia_d, tmax, tmin, largura, altura, entre=1.3, gap_par=0.45, passo=2):
    """Escolhe o maior tamanho que cabe. Retorna dict com fontes, linhas, tamanho, altura e se coube."""
    pars = _paragrafos(texto)
    t = tmax
    while True:
        f, fd = fonte(familia, t), fonte(familia_d, t)
        recuo = round(t * 1.1)
        linhas = _quebrar(pars, f, fd, largura, recuo)
        h = _altura(linhas, t, entre, gap_par)
        if h <= altura or t <= tmin:
            break
        t = max(tmin, t - passo)
    coube = h <= altura
    if not coube:
        # corta as linhas que sobram e marca reticencias na ultima
        while linhas and _altura(linhas, t, entre, gap_par) > altura:
            linhas.pop()
        if linhas:
            ultima = linhas[-1]
            ultima['palavras'] = ultima['palavras'] + [[('…', False)]]
        h = _altura(linhas, t, entre, gap_par)
    return {'f': f, 'fd': fd, 'linhas': linhas, 't': t, 'h': h, 'coube': coube, 'entre': entre, 'gap': gap_par}


def desenhar_texto(draw, x, y, bloco, cor, cor_destaque, cor_marcador=None):
    f, fd, t, entre = bloco['f'], bloco['fd'], bloco['t'], bloco['entre']
    esp = f.getlength(' ')
    ascent = f.getmetrics()[0]
    recuo = round(t * 1.1)
    for ln in bloco['linhas']:
        base = y + ascent + (t * entre - t) / 2
        cx = x + (recuo if ln['recuo'] else 0)
        if ln['marcador']:
            r = max(5, round(t * 0.14))
            cy = base - t * 0.33
            draw.rectangle((x + 2, cy - r, x + 2 + 2 * r, cy + r), fill=cor_marcador or cor_destaque)
        for i, w in enumerate(ln['palavras']):
            if i:
                cx += esp
            for pedaco, d in w:
                fnt = fd if d else f
                draw.text((cx, base), pedaco, font=fnt, fill=cor_destaque if d else cor, anchor='ls')
                cx += fnt.getlength(pedaco)
        y += t * entre
        if ln['fim']:
            y += t * bloco['gap']
    return y


def _texto_espacado(draw, x, y, texto, fnt, cor, espac=3):
    for ch in texto:
        draw.text((x, y), ch, font=fnt, fill=cor)
        x += fnt.getlength(ch) + espac
    return x


def _seta(draw, x, y, tam, cor):
    """Seta simples desenhada (nao depende de glifo da fonte)."""
    draw.line((x, y, x + tam, y), fill=cor, width=4)
    draw.polygon([(x + tam + 2, y), (x + tam - 12, y - 10), (x + tam - 12, y + 10)], fill=cor)


def _faixa_bloqueio(img, draw):
    w = img.width
    draw.rectangle((0, 0, w, 64), fill=VERMELHO)
    fnt = fonte('corpo_negrito', 28)
    draw.text((w / 2, 32), 'NÃO PUBLICAR ATÉ CORRIGIR - ver alertas de conformidade', font=fnt,
              fill='#FFFFFF', anchor='mm')


def _rodape(img, draw, tema, ultimo, y_linha):
    c = TEMAS[tema]
    w = img.width
    draw.line((MARGEM, y_linha, w - MARGEM, y_linha), fill=c['linha'], width=2)
    fnt = fonte('corpo', 26)
    draw.text((MARGEM, y_linha + 44), HANDLE, font=fnt, fill=c['suave'], anchor='ls')
    if not ultimo:
        rot = 'arraste'
        lr = fnt.getlength(rot)
        x_seta = w - MARGEM - 46
        draw.text((x_seta - 14 - lr, y_linha + 44), rot, font=fnt, fill=c['suave'], anchor='ls')
        _seta(draw, x_seta, y_linha + 35, 44, c['barra'])


# ============================================================
# LAYOUTS
# ============================================================

def _novo(tamanho, tema):
    img = Image.new('RGBA', tamanho, TEMAS[tema]['fundo'])
    return img, ImageDraw.Draw(img)


def _capa(slide, n, total, rotulo, bloqueado, avisos, tamanho=TAM_FEED):
    tema = 'escuro'
    c = TEMAS[tema]
    img, draw = _novo(tamanho, tema)
    w, h = tamanho
    larg = w - 2 * MARGEM
    topo = 110 if not bloqueado else 150
    _colar_logo(img, c['logo'], 150, w - MARGEM - 150, topo - 20)
    if rotulo:
        _texto_espacado(draw, MARGEM, topo + 10, rotulo.upper(), fonte('corpo_negrito', 26), c['destaque'], 4)
    y_titulo = 400
    y_rodape = h - 130
    bt = ajustar_texto(slide.get('titulo', ''), 'titulo', 'titulo', 96, 54, larg - 36, 520, entre=1.12, gap_par=0.2)
    draw.rectangle((MARGEM, y_titulo + 8, MARGEM + 10, y_titulo + bt['h'] - 8), fill=LARANJA)
    y = desenhar_texto(draw, MARGEM + 36, y_titulo, bt, c['texto'], c['destaque'])
    if not bt['coube']:
        avisos.append(f'slide {n}: título não coube, foi cortado - encurte')
    if slide.get('texto'):
        disponivel = y_rodape - 60 - (y + 40)
        bx = ajustar_texto(slide['texto'], 'corpo', 'corpo_negrito', 42, 30, larg, max(60, disponivel), entre=1.35)
        desenhar_texto(draw, MARGEM, y + 40, bx, c['texto2'], c['destaque'])
        if not bx['coube']:
            avisos.append(f'slide {n}: texto não coube, foi cortado - encurte')
    _rodape(img, draw, tema, n == total, y_rodape)
    if bloqueado:
        _faixa_bloqueio(img, draw)
    return img


def _interno(slide, n, total, tema, bloqueado, avisos, tamanho=TAM_FEED, seguro_topo=0, seguro_base=0,
             numerar=True, rodape=True):
    c = TEMAS[tema]
    img, draw = _novo(tamanho, tema)
    w, h = tamanho
    larg = w - 2 * MARGEM
    topo = max(90, seguro_topo) + (50 if bloqueado and not seguro_topo else 0)
    _colar_logo(img, c['logo'], 140, w - MARGEM - 140, topo - 6)
    if numerar:
        fn = fonte('titulo', 70)
        draw.text((MARGEM, topo + 62), f'{n:02d}', font=fn, fill=c['barra'], anchor='ls')
        lx = MARGEM + fn.getlength(f'{n:02d}') + 10
        draw.text((lx, topo + 62), f'/ {total:02d}', font=fonte('corpo', 30), fill=c['suave'], anchor='ls')
    draw.rectangle((MARGEM, topo + 92, MARGEM + 110, topo + 100), fill=c['barra'])
    y = topo + 148
    y_rodape = h - max(130, seguro_base)
    limite = y_rodape - 50
    bt = ajustar_texto(slide.get('titulo', ''), 'titulo', 'titulo', 72, 42, larg, 340, entre=1.15, gap_par=0.2)
    y = desenhar_texto(draw, MARGEM, y, bt, c['texto'], c['destaque'])
    if not bt['coube']:
        avisos.append(f'slide {n}: título não coube, foi cortado - encurte')
    if slide.get('texto'):
        y += 34
        bx = ajustar_texto(slide['texto'], 'corpo', 'corpo_negrito', 52, 30, larg, max(60, limite - y), entre=1.38)
        y = desenhar_texto(draw, MARGEM, y, bx, c['texto2'], c['destaque'], c['barra'])
        if not bx['coube']:
            avisos.append(f'slide {n}: texto não coube, foi cortado - encurte')
    if slide.get('interacao'):
        _caixa_interacao(draw, slide['interacao'], MARGEM, min(y + 40, limite - 150), larg, c)
    if rodape:
        _rodape(img, draw, tema, n == total, y_rodape)
    if bloqueado:
        _faixa_bloqueio(img, draw)
    return img


def _caixa_interacao(draw, texto, x, y, larg, c, medir=False):
    """Marca onde entra a figurinha do Instagram (enquete, caixa de pergunta, teste).
    medir=True so devolve a altura."""
    bx = ajustar_texto(texto, 'corpo_negrito', 'corpo_negrito', 38, 26, larg - 60, 130, entre=1.3)
    alt = bx['h'] + 56
    if medir:
        return alt
    draw.rounded_rectangle((x, y, x + larg, y + alt), radius=24, outline=c['barra'], width=4)
    draw.text((x + 30, y - 14), ' figurinha do Instagram ', font=fonte('corpo', 22), fill=c['suave'],
              anchor='ls')
    desenhar_texto(draw, x + 30, y + 28, bx, c['texto'], c['destaque'])
    return alt


def _story(frame, n, total, tema, bloqueado, avisos, tamanho=TAM_STORY, seguro_topo=250, seguro_base=330):
    """Story 9:16: bloco centralizado na area segura (topo e base ficam livres para a interface do Instagram)."""
    c = TEMAS[tema]
    img, draw = _novo(tamanho, tema)
    w, h = tamanho
    larg = w - 2 * MARGEM
    _colar_logo(img, c['logo'], 150, w - MARGEM - 150, seguro_topo - 20)
    area_ini, area_fim = seguro_topo + 150, h - seguro_base
    area = area_fim - area_ini
    bt = ajustar_texto(frame.get('titulo', ''), 'titulo', 'titulo', 88, 50, larg, area * 0.45, entre=1.14, gap_par=0.2)
    bx = None
    if frame.get('texto'):
        bx = ajustar_texto(frame['texto'], 'corpo', 'corpo_negrito', 54, 34, larg, area * 0.35, entre=1.38)
    alt_int = _caixa_interacao(draw, frame['interacao'], 0, 0, larg, c, medir=True) if frame.get('interacao') else 0
    total_h = 38 + bt['h'] + (40 + bx['h'] if bx else 0) + (70 + alt_int if alt_int else 0)
    y = area_ini + max(0, (area - total_h) / 2)
    draw.rectangle((MARGEM, y, MARGEM + 110, y + 8), fill=c['barra'])
    y = desenhar_texto(draw, MARGEM, y + 38, bt, c['texto'], c['destaque'])
    if not bt['coube']:
        avisos.append(f'story {n}: título não coube, foi cortado - encurte')
    if bx:
        y = desenhar_texto(draw, MARGEM, y + 40, bx, c['texto2'], c['destaque'], c['barra'])
        if not bx['coube']:
            avisos.append(f'story {n}: texto não coube, foi cortado - encurte')
    if alt_int:
        _caixa_interacao(draw, frame['interacao'], MARGEM, y + 70, larg, c)
    fnt = fonte('corpo', 28)
    draw.text((w / 2, h - seguro_base + 70), HANDLE, font=fnt, fill=c['suave'], anchor='ms')
    if total > 1:
        draw.text((w / 2, h - seguro_base + 115), f'{n} de {total}', font=fonte('corpo', 24), fill=c['suave'],
                  anchor='ms')
    if bloqueado:
        _faixa_bloqueio(img, draw)
    return img


def _final(slide, n, total, bloqueado, avisos, tamanho=TAM_FEED):
    tema = 'laranja'
    c = TEMAS[tema]
    img, draw = _novo(tamanho, tema)
    w, h = tamanho
    larg = w - 2 * MARGEM
    topo = 110 if not bloqueado else 150
    _colar_logo(img, c['logo'], 170, MARGEM, topo - 10)
    y = 420
    bt = ajustar_texto(slide.get('titulo', ''), 'titulo', 'titulo', 80, 46, larg, 300, entre=1.15, gap_par=0.2)
    y = desenhar_texto(draw, MARGEM, y, bt, c['texto'], c['destaque'])
    if not bt['coube']:
        avisos.append(f'slide {n}: título não coube, foi cortado - encurte')
    y_ident = h - 190
    if slide.get('texto'):
        y += 40
        bx = ajustar_texto(slide['texto'], 'corpo', 'corpo_negrito', 44, 30, larg, max(60, y_ident - 60 - y), entre=1.38)
        desenhar_texto(draw, MARGEM, y, bx, c['texto'], '#FFFFFF', '#FFFFFF')
        if not bx['coube']:
            avisos.append(f'slide {n}: texto não coube, foi cortado - encurte')
    draw.line((MARGEM, y_ident, w - MARGEM, y_ident), fill='#FFFFFF', width=2)
    fnt = fonte('corpo', 25)
    draw.text((MARGEM, y_ident + 48), AVISO_INFORMATIVO, font=fnt, fill=c['texto2'], anchor='ls')
    draw.text((MARGEM, y_ident + 88), IDENTIFICACAO, font=fnt, fill=c['texto2'], anchor='ls')
    if bloqueado:
        _faixa_bloqueio(img, draw)
    return img


def _estatico(titulo, apoio, cta, tema, rotulo, bloqueado, avisos, tamanho=TAM_FEED):
    c = TEMAS[tema]
    img, draw = _novo(tamanho, tema)
    w, h = tamanho
    larg = w - 2 * MARGEM
    topo = 110 if not bloqueado else 150
    _colar_logo(img, c['logo'], 150, w - MARGEM - 150, topo - 20)
    if rotulo:
        _texto_espacado(draw, MARGEM, topo + 10, rotulo.upper(), fonte('corpo_negrito', 26), c['destaque'], 4)
    y = 330
    bt = ajustar_texto(titulo, 'titulo', 'titulo', 92, 52, larg, 470, entre=1.12, gap_par=0.2)
    y = desenhar_texto(draw, MARGEM, y, bt, c['texto'], c['destaque'])
    if not bt['coube']:
        avisos.append('estático: título não coube, foi cortado - encurte')
    draw.rectangle((MARGEM, y + 30, MARGEM + 110, y + 38), fill=c['barra'])
    y_ident = h - 170
    limite = y_ident - (110 if cta else 40)
    if apoio:
        bx = ajustar_texto(apoio, 'corpo', 'corpo_negrito', 44, 30, larg, max(60, limite - (y + 80)), entre=1.38)
        desenhar_texto(draw, MARGEM, y + 80, bx, c['texto2'], c['destaque'], c['barra'])
        if not bx['coube']:
            avisos.append('estático: texto de apoio não coube, foi cortado - encurte')
    if cta:
        bc = ajustar_texto(cta, 'corpo_negrito', 'corpo_negrito', 34, 26, larg, 90, entre=1.3)
        desenhar_texto(draw, MARGEM, y_ident - 100, bc, c['destaque'], c['destaque'])
    draw.line((MARGEM, y_ident, w - MARGEM, y_ident), fill=c['linha'], width=2)
    fnt = fonte('corpo', 24)
    draw.text((MARGEM, y_ident + 46), AVISO_INFORMATIVO, font=fnt, fill=c['suave'], anchor='ls')
    draw.text((MARGEM, y_ident + 84), IDENTIFICACAO, font=fnt, fill=c['suave'], anchor='ls')
    if bloqueado:
        _faixa_bloqueio(img, draw)
    return img


# ============================================================
# API
# ============================================================

def _salvar(img, pasta, nome):
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    img.convert('RGB').save(caminho, 'PNG', optimize=True)
    return caminho


def _prefixo(bloqueado):
    return 'NAO_PUBLICAR_' if bloqueado else ''


def renderizar_carrossel(slides, pasta, tema='claro', rotulo='', bloqueado=False):
    """slides: [{'titulo', 'texto'}]. 1o = capa (grafite), ultimo = fechamento (laranja), miolo no tema."""
    avisos, arquivos = [], []
    total = len(slides)
    for i, s in enumerate(slides, 1):
        if i == 1:
            img = _capa(s, i, total, rotulo, bloqueado, avisos)
        elif i == total and total > 2:
            img = _final(s, i, total, bloqueado, avisos)
        else:
            img = _interno(s, i, total, tema, bloqueado, avisos)
        arquivos.append(_salvar(img, pasta, f'{_prefixo(bloqueado)}slide_{i:02d}.png'))
    if arquivos:
        arquivos.append(prancha(arquivos, os.path.join(pasta, f'{_prefixo(bloqueado)}PRANCHA_revisao.png')))
    return arquivos, avisos


def renderizar_estatico(titulo, apoio, pasta, tema='escuro', cta='', rotulo='', bloqueado=False):
    avisos = []
    img = _estatico(titulo, apoio, cta, tema, rotulo, bloqueado, avisos)
    return [_salvar(img, pasta, f'{_prefixo(bloqueado)}estatico.png')], avisos


def renderizar_story(frames, pasta, tema='escuro', bloqueado=False):
    """frames: [{'titulo', 'texto', 'interacao'}] em 1080x1920, com area segura do Instagram."""
    avisos, arquivos = [], []
    total = len(frames)
    for i, fr in enumerate(frames, 1):
        img = _story(fr, i, total, tema, bloqueado, avisos)
        arquivos.append(_salvar(img, pasta, f'{_prefixo(bloqueado)}story_{i:02d}.png'))
    return arquivos, avisos


def prancha(arquivos, destino, colunas=3, largura_miniatura=360):
    """Folha de revisao com todas as artes lado a lado (para conferir de uma vez)."""
    imgs = [Image.open(a) for a in arquivos]
    esc = largura_miniatura / imgs[0].width
    mw, mh = largura_miniatura, round(imgs[0].height * esc)
    linhas = (len(imgs) + colunas - 1) // colunas
    gap = 24
    folha = Image.new('RGB', (colunas * mw + (colunas + 1) * gap, linhas * mh + (linhas + 1) * gap), '#D9D2C8')
    for k, im in enumerate(imgs):
        x = gap + (k % colunas) * (mw + gap)
        y = gap + (k // colunas) * (mh + gap)
        folha.paste(im.convert('RGB').resize((mw, mh), Image.LANCZOS), (x, y))
    folha.save(destino, 'PNG', optimize=True)
    return destino


TEMA_PADRAO = {'carrossel': 'claro', 'estatico': 'escuro', 'story': 'escuro'}


def renderizar_post(post, pasta, tema=None, bloqueado=False):
    """post: dict gerado pelo conteudo.py (formato, slides, rotulo, cta). Retorna (arquivos, avisos).
    tema None = padrao do formato (carrossel claro; estatico e story escuros)."""
    formato = post.get('formato')
    tema = tema or TEMA_PADRAO.get(formato, 'claro')
    rotulo = post.get('rotulo', '')
    slides = post.get('slides') or []
    if formato == 'carrossel':
        return renderizar_carrossel(slides, pasta, tema, rotulo, bloqueado)
    if formato == 'estatico':
        s = slides[0] if slides else {'titulo': post.get('titulo', ''), 'texto': ''}
        return renderizar_estatico(s.get('titulo', ''), s.get('texto', ''), pasta, tema, post.get('cta', ''),
                                   rotulo, bloqueado)
    if formato == 'story':
        return renderizar_story(slides, pasta, tema, bloqueado)
    return [], [f'formato {formato}: sem arte (reels é gravado em vídeo; use o roteiro)']


# ============================================================
# DEMONSTRACAO (sem IA)
# ============================================================

DEMO_CARROSSEL = [
    {'titulo': 'Prorrogar a dívida rural é **favor** do banco?',
     'texto': 'O que diz a Súmula 298 do STJ, em linguagem de quem produz.'},
    {'titulo': 'O que diz a Súmula 298',
     'texto': 'Para o STJ, o alongamento da dívida de crédito rural **não é faculdade do banco**: '
              'é direito do devedor, **nos termos da lei**.'},
    {'titulo': '"Nos termos da lei": o que quer dizer',
     'texto': 'O Manual de Crédito Rural (MCR 2.6.4) prevê a prorrogação quando o produtor comprova '
              '**dificuldade temporária** de pagar por causa de:\n- dificuldade de vender a produção\n'
              '- frustração de safra por fatores adversos\n- ocorrências que prejudicaram a atividade'},
    {'titulo': 'Na prática da lida',
     'texto': 'Estiagem que secou a lavoura, chuva demais na colheita, lagarta no pasto, preço que caiu na hora '
              'de vender. Cada situação precisa de **prova**.'},
    {'titulo': 'O que guardar desde já',
     'texto': '- Cédulas e aditivos\n- Notas fiscais e GTAs\n- Fotos com data da lavoura e do pasto\n'
              '- Laudos e registros da perda\n- Extratos e comprovantes de pagamento'},
    {'titulo': 'Peça por escrito',
     'texto': 'Faça o pedido de prorrogação **por escrito** ao banco ou à cooperativa e guarde o comprovante do '
              'envio. Esse registro mostra que você procurou o banco.'},
    {'titulo': 'Ficou com dúvida?',
     'texto': 'Converse com a equipe do escritório. Salve este conteúdo e compartilhe com quem trabalha no campo.'},
]


def main(argv=None):
    ap = argparse.ArgumentParser(description='Artes dos posts (PNG) - teste visual')
    ap.add_argument('--demo', action='store_true', help='renderiza carrossel, estático e story de demonstração')
    ap.add_argument('--tema', choices=['claro', 'escuro'], default='claro')
    ap.add_argument('--bloqueado', action='store_true', help='simula material bloqueado pela conformidade')
    ap.add_argument('--saida', help='pasta de saída (padrão: SAIDA/marketing/arte_demo)')
    args = ap.parse_args(argv)
    if not args.demo:
        ap.error('use --demo (as artes reais saem pelo conteudo.py post ... --arte)')
    pasta = args.saida
    if not pasta:
        sys.path.insert(0, os.path.join(RAIZ, 'NUCLEO'))
        import ambiente
        pasta = ambiente.pasta_saida('marketing', 'arte_demo')
    print('Fontes:', fontes_em_uso())
    arq, av = renderizar_carrossel(DEMO_CARROSSEL, os.path.join(pasta, 'carrossel'), args.tema, 'Crédito rural',
                                   args.bloqueado)
    arq2, av2 = renderizar_estatico('Pediu prorrogação e o banco **não respondeu**?',
                                    'Guarde o comprovante do pedido por escrito. Ele mostra que você procurou o banco '
                                    'antes de qualquer outra medida.', os.path.join(pasta, 'estatico'), 'escuro',
                                    'Ficou com dúvida? Converse com a equipe do escritório.', 'Dívida rural',
                                    args.bloqueado)
    arq3, av3 = renderizar_story([
        {'titulo': 'Você guarda as **notas fiscais** da safra?', 'texto': '', 'interacao': 'Enquete: Sim / Às vezes'},
        {'titulo': 'Nota, GTA e foto com data', 'texto': 'Esses papéis contam a história da sua safra.'},
        {'titulo': 'Lista completa no feed', 'texto': 'Salve o carrossel "O que guardar desde já".'},
    ], os.path.join(pasta, 'story'), 'escuro', args.bloqueado)
    for a in arq + arq2 + arq3:
        print(a)
    for a in av + av2 + av3:
        print('AVISO:', a)
    return 0


if __name__ == '__main__':
    sys.exit(main())

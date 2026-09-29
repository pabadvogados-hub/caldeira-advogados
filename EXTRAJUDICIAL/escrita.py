"""
Escrita no padrao visual das notificacoes do escritorio (tirado de msg37244 e msg37246):
titulo centralizado laranja 15; NOTIFICANTE/NOTIFICADO/ASSUNTO com rotulo e nome em laranja;
secoes "I. DOS FATOS:" a direita, sublinhadas, laranja 14; subtitulos "1) ..." laranja;
citacoes recuadas em 11; assinatura em duas colunas com nome e OAB em laranja.
Usa o timbrado do NUCLEO (docx_caldeira).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)

from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from docx_caldeira import DESTAQUE  # noqa: E402
from config.escritorio import VISUAL  # noqa: E402

VERMELHO = RGBColor(0xC0, 0x00, 0x00)
CINZA = RGBColor(0x59, 0x59, 0x59)
MARCA = re.compile(r'(\[(?:CONFERIR|PREENCHER)[^\]]*\])')
NEGRITO = re.compile(r'(\*\*[^*]+\*\*)')


def formatar(p, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=False, depois=6, espaco=None, antes=0):
    p.alignment = alinhamento
    f = p.paragraph_format
    f.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    f.line_spacing = espaco or VISUAL['espacamento']
    f.space_after = Pt(depois)
    f.space_before = Pt(antes)
    if recuo:
        f.first_line_indent = Cm(VISUAL['recuo_primeira_linha_cm'])
    return p


def run(p, texto, estilo='n', tamanho=None, italico=False, sublinhado=False):
    """estilo: n normal | b negrito | o laranja negrito. Marcas [CONFERIR]/[PREENCHER] saem em vermelho."""
    for parte in MARCA.split(str(texto)):
        if not parte:
            continue
        r = p.add_run(parte)
        r.italic = italico
        r.underline = sublinhado
        if tamanho:
            r.font.size = Pt(tamanho)
        if MARCA.fullmatch(parte):
            r.bold, r.font.color.rgb = True, VERMELHO
        elif estilo == 'o':
            r.bold, r.font.color.rgb = True, DESTAQUE
        elif estilo == 'b':
            r.bold = True
    return p


def pedacos(doc, partes, recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, depois=6, tamanho=None, antes=0):
    """Paragrafo com trechos de estilos diferentes: [('NOTIFICANTE: ', 'o'), ('texto', 'n'), ...]."""
    p = formatar(doc.add_paragraph(), alinhamento, recuo, depois, antes=antes)
    for texto, estilo in partes:
        run(p, texto, estilo, tamanho)
    return p


def texto_marcado(doc, texto, recuo=True, tamanho=None, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, depois=6):
    """Paragrafo que aceita **negrito** (vira laranja, como os destaques das pecas)."""
    p = formatar(doc.add_paragraph(), alinhamento, recuo, depois)
    for parte in NEGRITO.split(texto):
        if parte.startswith('**') and parte.endswith('**'):
            run(p, parte[2:-2], 'o', tamanho)
        elif parte:
            run(p, parte, 'n', tamanho)
    return p


def titulo_notificacao(doc, texto='NOTIFICAÇÃO EXTRAJUDICIAL'):
    p = formatar(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, depois=14)
    run(p, texto, 'o', 15)
    return p


def secao_romana(doc, texto):
    """'I. DOS FATOS:' a direita, sublinhado, laranja 14."""
    p = formatar(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.RIGHT, depois=10, antes=14)
    run(p, texto, 'o', 14, sublinhado=True)
    return p


def subtitulo(doc, texto):
    p = formatar(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, depois=6, antes=8)
    p.paragraph_format.keep_with_next = True
    run(p, texto, 'o')
    return p


def alinea(doc, texto):
    p = formatar(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, depois=4, antes=4)
    p.paragraph_format.keep_with_next = True
    run(p, texto, 'b')
    return p


def marcador(doc, texto, recuo_cm=1.25):
    """Item com marcador; 'Titulo: texto' deixa o titulo em negrito, como nas pecas."""
    p = formatar(doc.add_paragraph(), depois=3)
    p.paragraph_format.left_indent = Cm(recuo_cm)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    run(p, '•  ')   # espaco fixo: o justificado nao estica depois do marcador
    texto = texto.strip()
    m = re.match(r'^\*\*(.+?)\*\*\s*(.*)$', texto) or re.match(r'^([^:.]{3,60}:)\s+(.*)$', texto)
    if m:
        run(p, m.group(1).replace('**', ''), 'b')
        run(p, ' ' + m.group(2))
    else:
        for parte in NEGRITO.split(texto):
            if parte.startswith('**') and parte.endswith('**'):
                run(p, parte[2:-2], 'b')
            elif parte:
                run(p, parte)
    return p


def citacao(doc, texto):
    """Transcricao de norma/sumula: recuo de 4 cm, fonte 11, entre aspas."""
    p = formatar(doc.add_paragraph(), depois=8, espaco=1.0)
    p.paragraph_format.left_indent = Cm(4)
    run(p, texto, 'n', 11, italico=True)
    return p


def item_numerado(doc, numero, rotulo, texto):
    p = formatar(doc.add_paragraph(), depois=4)
    p.paragraph_format.left_indent = Cm(1.25)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    run(p, f'{numero}. ', 'o')
    run(p, f'{rotulo}: ', 'o')
    for parte in NEGRITO.split(texto):
        if parte.startswith('**') and parte.endswith('**'):
            run(p, parte[2:-2], 'o')
        elif parte:
            run(p, parte)
    return p


def _sem_bordas(tabela):
    tbl = tabela._tbl
    tblPr = tbl.tblPr
    bordas = OxmlElement('w:tblBorders')
    for lado in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{lado}')
        el.set(qn('w:val'), 'nil')
        bordas.append(el)
    tblPr.append(bordas)


def assinaturas(doc, advogados):
    """Bloco de assinatura em colunas (nome e OAB em laranja), como nas notificacoes."""
    doc.add_paragraph()
    t = doc.add_table(rows=1, cols=len(advogados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _sem_bordas(t)
    for i, adv in enumerate(advogados):
        cel = t.rows[0].cells[i]
        p = formatar(cel.paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER, depois=0, espaco=1.0)
        run(p, '_' * 30)
        p2 = formatar(cel.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, depois=0, espaco=1.0)
        run(p2, adv['nome'].upper(), 'o')
        p3 = formatar(cel.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, depois=0, espaco=1.0)
        run(p3, adv['oab'], 'o')
    return t


def nota_revisao(doc, texto):
    """Linha final da minuta (cinza, 9 pt). Nao vai no PDF de envio (ver notificacao.pdf_de_envio)."""
    p = formatar(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, depois=0, antes=10, espaco=1.0)
    r = p.add_run(texto)
    r.italic, r.font.size, r.font.color.rgb = True, Pt(9), CINZA
    return p


def markdown(doc, texto):
    """
    Converte o texto da IA:
      '## 1) TITULO'  -> subtitulo laranja     '### a) Alinea' -> alinea em negrito
      '- item'        -> marcador              '> citacao'     -> citacao recuada
      demais linhas   -> paragrafo com recuo (**negrito** vira destaque laranja)
    """
    for bruto in (texto or '').splitlines():
        linha = bruto.strip()
        if not linha or linha in ('---', '***'):
            continue
        if linha.startswith('### '):
            alinea(doc, linha[4:].strip().strip('*'))
        elif linha.startswith('## ') or linha.startswith('# '):
            subtitulo(doc, linha.lstrip('#').strip().strip('*').upper())
        elif linha.startswith(('- ', '* ', '• ')):
            marcador(doc, linha[2:].strip())
        elif linha.startswith('>'):
            citacao(doc, linha.lstrip('>').strip())
        else:
            texto_marcado(doc, linha)

"""
Ajuste das tabelas do timbrado para relatorios largos (Controladoria e Gestao).

Usa docx_caldeira.tabela() e depois:
  - fixa a largura de cada coluna (o Word ignora a largura so da celula com autoajuste ligado);
  - repete o cabecalho quando a tabela passa de pagina e nao deixa o cabecalho sozinho no pe da pagina;
  - nao quebra uma linha no meio.
"""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm

import docx_caldeira


def _marcar(linha, tag):
    trPr = linha._tr.get_or_add_trPr()
    el = OxmlElement(tag)
    el.set(qn('w:val'), 'true')
    trPr.append(el)


def tabela(doc, cabecalho, linhas, larguras_cm=None, tamanho=9):
    t = docx_caldeira.tabela(doc, cabecalho, linhas, larguras_cm, tamanho)
    if larguras_cm:
        t.autofit = False
        tblPr = t._tbl.tblPr
        layout = OxmlElement('w:tblLayout')
        layout.set(qn('w:type'), 'fixed')
        tblPr.append(layout)
        for i, w in enumerate(larguras_cm):
            if i < len(t.columns):
                t.columns[i].width = Cm(w)
    _marcar(t.rows[0], 'w:tblHeader')
    for cel in t.rows[0].cells:
        for p in cel.paragraphs:
            p.paragraph_format.keep_with_next = True
    for linha in t.rows:
        _marcar(linha, 'w:cantSplit')
    return t

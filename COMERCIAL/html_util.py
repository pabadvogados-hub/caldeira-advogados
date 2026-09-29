"""
Relatorios HTML simples e autocontidos (sem internet, sem biblioteca externa), nas cores do
escritorio: laranja #C45911 e grafite #20201F. Tabelas ordenaveis com um clique no titulo.
"""
import html
from datetime import datetime

LARANJA = '#C45911'
ESCURO = '#20201F'

_CSS = """
:root{--laranja:#C45911;--escuro:#20201F;--papel:#FBF8F4;--linha:#E7DED3;--suave:#6B645C;--ok:#2E7D32;--alerta:#B3261E}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--escuro);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
header{background:var(--escuro);color:#fff;padding:22px 16px;border-bottom:4px solid var(--laranja)}
header .caixa,main{max-width:1180px;margin:0 auto}
h1,h2{font-family:Georgia,"Times New Roman",serif;font-weight:700;letter-spacing:.2px}
h1{margin:0;font-size:26px}
header p{margin:4px 0 0;color:#D9D2C8;font-size:14px}
main{padding:18px 16px 48px}
h2{color:var(--laranja);font-size:20px;margin:28px 0 10px;border-bottom:1px solid var(--linha);padding-bottom:6px}
.cartoes{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(170px,100%),1fr));gap:10px}
.cartao{background:#fff;border:1px solid var(--linha);border-left:4px solid var(--laranja);border-radius:8px;padding:10px 12px;min-width:0}
.cartao b{display:block;font-size:clamp(17px,4.6vw,22px);font-family:Georgia,serif;overflow-wrap:anywhere}
.cartao span{color:var(--suave);font-size:13px}
.tabela{overflow-x:auto;background:#fff;border:1px solid var(--linha);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:14px}
th{background:var(--escuro);color:#fff;text-align:left;padding:8px 10px;cursor:pointer;white-space:nowrap;user-select:none}
th:hover{background:#3a3937}
th.asc:after{content:" \\25B2";color:var(--laranja)}
th.desc:after{content:" \\25BC";color:var(--laranja)}
td{padding:7px 10px;border-top:1px solid var(--linha);vertical-align:top}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:nth-child(even) td{background:#FCFAF7}
tr.destaque td{background:#FFF3EA}
ul.lista li{margin:4px 0}
.alerta{color:var(--alerta);font-weight:600}
.ok{color:var(--ok);font-weight:600}
.nota{color:var(--suave);font-size:13px}
footer{color:var(--suave);font-size:12px;max-width:1180px;margin:0 auto;padding:0 16px 30px}
"""

_JS = """
document.querySelectorAll('table.ordenavel').forEach(function(t){
  t.querySelectorAll('th').forEach(function(th,i){
    th.addEventListener('click',function(){
      var corpo=t.tBodies[0], linhas=Array.from(corpo.rows);
      var asc=!th.classList.contains('asc');
      t.querySelectorAll('th').forEach(function(x){x.classList.remove('asc','desc')});
      th.classList.add(asc?'asc':'desc');
      linhas.sort(function(a,b){
        var x=a.cells[i].getAttribute('data-v')||a.cells[i].innerText;
        var y=b.cells[i].getAttribute('data-v')||b.cells[i].innerText;
        var nx=parseFloat(x), ny=parseFloat(y);
        if(!isNaN(nx)&&!isNaN(ny)&&a.cells[i].hasAttribute('data-v')) return asc?nx-ny:ny-nx;
        return asc?x.localeCompare(y,'pt-BR'):y.localeCompare(x,'pt-BR');
      });
      linhas.forEach(function(l){corpo.appendChild(l)});
    });
  });
});
"""


def esc(v):
    return html.escape('' if v is None else str(v))


def reais(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '-'
    return 'R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def reais_curto(v):
    """R$ 6,77 bi / R$ 529,3 mi - para cartoes, onde o valor cheio nao cabe."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '-'
    if abs(v) >= 1e9:
        return f'R$ {numero(v / 1e9, 2)} bi'
    if abs(v) >= 1e6:
        return f'R$ {numero(v / 1e6, 1)} mi'
    return reais(v)


def numero(v, casas=0):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '-'
    return f'{v:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def cartoes(itens):
    """itens: [(valor_formatado, legenda)]"""
    return '<div class="cartoes">' + ''.join(
        f'<div class="cartao"><b>{esc(v)}</b><span>{esc(l)}</span></div>' for v, l in itens) + '</div>'


def tabela(cabecalho, linhas, destacar=None):
    """
    linhas: lista de listas. Cada celula pode ser texto ou (texto_formatado, valor_numerico)
    para ordenar pelo numero. destacar: conjunto de indices de linha a realcar.
    """
    destacar = destacar or set()
    th = ''.join(f'<th>{esc(c)}</th>' for c in cabecalho)
    corpo = []
    for i, linha in enumerate(linhas):
        tds = []
        for c in linha:
            if isinstance(c, tuple):
                tds.append(f'<td class="n" data-v="{esc(c[1])}">{esc(c[0])}</td>')
            else:
                tds.append(f'<td>{esc(c)}</td>')
        classe = ' class="destaque"' if i in destacar else ''
        corpo.append(f'<tr{classe}>' + ''.join(tds) + '</tr>')
    return (f'<div class="tabela"><table class="ordenavel"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(corpo)}</tbody></table></div>')


def lista(itens, classe=''):
    return f'<ul class="lista {classe}">' + ''.join(f'<li>{esc(i)}</li>' for i in itens) + '</ul>'


def pagina(titulo, subtitulo, blocos, rodape=''):
    """blocos: lista de (titulo_da_secao | None, html_da_secao)."""
    corpo = ''.join((f'<h2>{esc(t)}</h2>' if t else '') + h for t, h in blocos)
    gerado = datetime.now().strftime('%d/%m/%Y %H:%M')
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title><style>{_CSS}</style></head>
<body><header><div class="caixa"><h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p></div></header>
<main>{corpo}</main>
<footer>Caldeira Advogados Associados - gerado em {gerado}. {esc(rodape)}</footer>
<script>{_JS}</script></body></html>"""

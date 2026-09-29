"""
Saidas da varredura: relatorio DOCX no timbrado, CSV para a equipe, agenda .ics
(importa no Google Agenda/Outlook) e JSON de historico (base do avisos-cliente e dos
indicadores da auditoria de sexta). Tudo em SAIDA/controladoria/varreduras/.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from collections import Counter  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from docx.enum.section import WD_ORIENT  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum  # noqa: E402
from configuracao import ACOES, DIAS_ANTES_FATAL  # noqa: E402
from docx_caldeira import lista, novo_documento, paragrafo, secao, titulo  # noqa: E402
from docx_util import tabela  # noqa: E402

CAMPOS_CSV = ['gravidade', 'interno', 'fatal', 'dias_uteis_restantes', 'processo', 'cliente', 'rotulo',
              'providencia', 'peca', 'comando', 'responsavel', 'prazo_dias', 'prazo_origem', 'prazo_nosso',
              'evento_tipo', 'evento_data', 'evento_hora', 'tribunal', 'orgao', 'data_disponibilizacao',
              'data_publicacao', 'confianca', 'origem_classificacao', 'motivo', 'observacoes', 'polo',
              'favoravel', 'advbox_processo_id', 'advbox_fase', 'pasta', 'link', 'id_djen', 'categoria']


def pasta_varreduras():
    return comum.pasta_saida('controladoria', 'varreduras')


def _paisagem(doc):
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21)
    sec.left_margin, sec.right_margin = Cm(2), Cm(2)
    sec.top_margin, sec.bottom_margin = Cm(2.6), Cm(2.2)


def relatorio_docx(itens, caminho, cabecalho):
    doc = novo_documento()
    _paisagem(doc)
    titulo(doc, 'Controladoria · Varredura do DJEN')
    for rotulo, valor in cabecalho:
        paragrafo(doc, valor, rotulo=rotulo, espaco=1.0)

    secao(doc, '1. Resumo')
    por_cat = Counter(i['rotulo'] for i in itens)
    alta = [i for i in itens if i['gravidade'] == 'ALTA']
    manual = [i for i in itens if i['categoria'] == 'REVISAO_MANUAL']
    fora = [i for i in itens if not i['advbox_processo_id']]
    lista(doc, [
        f'{len(itens)} publicação(ões) analisada(s); {len(alta)} de prioridade ALTA.',
        f'{sum(1 for i in itens if i["fatal"])} com prazo fatal calculado (preliminar); '
        f'{sum(1 for i in itens if i["interno_atrasado"])} já sem folga para o D-{DIAS_ANTES_FATAL}.',
        f'{len(manual)} para REVISÃO MANUAL (ler a publicação inteira).',
        f'{len(fora)} sem processo correspondente no ADVBOX (cadastrar ou conferir o número).',
    ])
    tabela(doc, ['Tipo de publicação', 'Qtd.'], [[k, str(v)] for k, v in por_cat.most_common()], [12, 2.5])

    secao(doc, '2. Prazos (ordem de prioridade)')
    com_prazo = [i for i in itens if i['fatal'] or i['interno']]
    if com_prazo:
        tabela(doc, ['Grav.', 'Interno', 'Fatal', 'Processo', 'Cliente', 'Publicação', 'Providência', 'Responsável'],
               [[i['gravidade'], i['interno'] + (' (!)' if i['interno_atrasado'] else ''), i['fatal'],
                 i['processo'], i['cliente'][:40], i['rotulo'], i['peca'] or i['providencia'][:80],
                 i['responsavel']] for i in com_prazo],
               [1.4, 2.1, 2.1, 4.1, 4, 4, 5, 3], tamanho=8)
    else:
        paragrafo(doc, 'Nenhum prazo do escritório nas publicações do período.')

    eventos = [i for i in itens if i['evento_data']]
    if eventos:
        secao(doc, '3. Audiências e perícias (avisar o cliente e pôr na agenda)')
        tabela(doc, ['Quando', 'Tipo', 'Processo', 'Cliente', 'Onde'],
               [[f"{i['evento_data']} {i['evento_hora']}".strip(), i['evento_tipo'].title(), i['processo'],
                 i['cliente'][:40], 'Virtual' if i['evento_virtual'] else i['orgao']] for i in eventos],
               [3.5, 2.5, 4.5, 6, 8.5], tamanho=9)

    secao(doc, '4. Publicação por publicação')
    for n, i in enumerate(itens, 1):
        p = paragrafo(doc, f"{i['processo'] or 'sem número'} · {i['rotulo']}", rotulo=f'{n}. {i["gravidade"]}',
                      negrito=True, espaco=1.0)
        p.paragraph_format.space_before = Pt(8)
        linhas = [
            ('Cliente', f"{i['cliente']}" + (f" x {i['parte_contraria']}" if i['parte_contraria'] else '')),
            ('Órgão', f"{i['tribunal']} · {i['orgao']} · {i['classe']}"),
            ('Disponibilizada / publicada', f"{i['data_disponibilizacao']} / {i['data_publicacao']}"),
            ('Classificação', f"{i['motivo']} (confiança {i['confianca']}; polo {i['polo'] or '-'})"),
        ]
        if i['fatal']:
            linhas.append(('Prazo', f"{i['prazo_dias']} dia(s) ({i['prazo_origem']}) · fatal {i['fatal']} "
                                    f"(preliminar) · interno {i['interno']}"
                                    + (' · SEM FOLGA, fazer hoje' if i['interno_atrasado'] else '')))
        elif i['interno']:
            linhas.append(('Conferir até', i['interno']))
        linhas += [('Providência', i['providencia'])]
        if i['peca']:
            linhas.append(('Peça sugerida', i['peca'] + (f" · {i['comando']}" if i['comando'] else '')))
        linhas.append(('Responsável', i['responsavel']))
        if i['observacoes']:
            linhas.append(('Atenção', i['observacoes']))
        if i['frase_chave']:
            linhas.append(('Trecho', f"“{i['frase_chave'][:350]}”"))
        linhas.append(('Link', i['link']))
        for rot, val in linhas:
            paragrafo(doc, val, rotulo=rot, tamanho=10, espaco=1.0)

    p = paragrafo(doc, 'Prazos calculados de forma PRELIMINAR (publicação = 1º dia útil após a disponibilização; '
                       'dias úteis; recesso de 20/12 a 20/01; feriados locais só os do .env). Conferir no processo. '
                       'A IA não protocola nem decide: a providência é sugestão para o responsável e o Coordenador.',
                  negrito=True, tamanho=9)
    p.paragraph_format.space_before = Pt(14)
    doc.save(caminho)
    return caminho


def _ics_evento(uid, inicio, fim, resumo, descricao, dia_inteiro=True):
    def esc(t):
        return (t or '').replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    if dia_inteiro:
        dt = f'DTSTART;VALUE=DATE:{inicio:%Y%m%d}\r\nDTEND;VALUE=DATE:{(inicio + timedelta(days=1)):%Y%m%d}'
    else:
        dt = f'DTSTART:{inicio:%Y%m%dT%H%M%S}\r\nDTEND:{fim:%Y%m%dT%H%M%S}'
    return (f'BEGIN:VEVENT\r\nUID:{uid}@caldeira-controladoria\r\nDTSTAMP:{datetime.now():%Y%m%dT%H%M%S}\r\n'
            f'{dt}\r\nSUMMARY:{esc(resumo)}\r\nDESCRIPTION:{esc(descricao)}\r\nEND:VEVENT\r\n')


def agenda_ics(itens, caminho):
    """Prazo interno, prazo fatal e audiencias/pericias num arquivo .ics."""
    eventos = []
    for i in itens:
        desc = f"{i['cliente']} | {i['providencia']} | Responsável: {i['responsavel']} | {i['link']}"
        if i['interno_iso']:
            eventos.append(_ics_evento(f"{i['id_djen']}-interno", comum.data(i['interno_iso']), None,
                                       f"[INTERNO] {i['rotulo']} - {i['processo']}", desc))
        if i['fatal_iso'] and i['categoria'] != 'AUDIENCIA':
            eventos.append(_ics_evento(f"{i['id_djen']}-fatal", comum.data(i['fatal_iso']), None,
                                       f"[FATAL - conferir] {i['rotulo']} - {i['processo']}", desc))
        if i['evento_data']:
            d = comum.data(i['evento_data'])
            if i['evento_hora']:
                h, m = (int(x) for x in i['evento_hora'].split(':'))
                ini = datetime(d.year, d.month, d.day, h, m)
                eventos.append(_ics_evento(f"{i['id_djen']}-evento", ini, ini + timedelta(hours=1),
                                           f"{i['evento_tipo'].title()} - {i['cliente']} ({i['processo']})", desc,
                                           dia_inteiro=False))
            else:
                eventos.append(_ics_evento(f"{i['id_djen']}-evento", d, None,
                                           f"{i['evento_tipo'].title()} - {i['cliente']} ({i['processo']})", desc))
    with open(caminho, 'w', encoding='utf-8', newline='') as f:
        f.write('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Caldeira Advogados//Controladoria//PT\r\n'
                + ''.join(eventos) + 'END:VCALENDAR\r\n')
    return caminho, len(eventos)


def salvar_tudo(itens, cabecalho, exemplo=False, meta=None):
    carimbo = datetime.now().strftime('%Y-%m-%d_%H%M') + ('_EXEMPLO' if exemplo else '')
    pasta = pasta_varreduras()
    docx = relatorio_docx(itens, os.path.join(pasta, f'{carimbo} - Varredura DJEN.docx'), cabecalho)
    csv_ = comum.salvar_csv(os.path.join(pasta, f'{carimbo} - Varredura DJEN.csv'), itens, CAMPOS_CSV)
    ics, n_ev = agenda_ics(itens, os.path.join(pasta, f'{carimbo} - Agenda.ics'))
    js = os.path.join(pasta, f'{carimbo}.json')
    with open(js, 'w', encoding='utf-8') as f:
        json.dump({'gerado_em': datetime.now().isoformat(timespec='seconds'), 'exemplo': exemplo,
                   'meta': meta or {}, 'itens': itens}, f, ensure_ascii=False, indent=1)
    return {'docx': docx, 'csv': csv_, 'ics': ics, 'eventos_agenda': n_ev, 'json': js}


def historico(desde=None, ate=None, exemplo=False):
    """Itens de todas as varreduras salvas (sem repetir a mesma publicacao) no intervalo."""
    pasta = pasta_varreduras()
    vistos, saida = set(), []
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith('.json') or ('_EXEMPLO' in nome) != exemplo:
            continue
        try:
            with open(os.path.join(pasta, nome), encoding='utf-8') as f:
                dados = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for i in dados.get('itens') or []:
            d = comum.data(i.get('data_disponibilizacao'))
            if (desde and d and d < desde) or (ate and d and d > ate) or i.get('id_djen') in vistos:
                continue
            vistos.add(i.get('id_djen'))
            saida.append(i)
    return saida


def ultima_varredura(exemplo=False):
    pasta = pasta_varreduras()
    nomes = sorted(n for n in os.listdir(pasta) if n.endswith('.json') and ('_EXEMPLO' in n) == exemplo)
    if not nomes:
        return None, []
    with open(os.path.join(pasta, nomes[-1]), encoding='utf-8') as f:
        return os.path.join(pasta, nomes[-1]), json.load(f).get('itens') or []


def rotulos_categorias():
    return {k: v['rotulo'] for k, v in ACOES.items()}

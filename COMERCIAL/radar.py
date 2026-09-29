"""
RADAR DE CREDITO RURAL POR MUNICIPIO (dados publicos do Banco Central + IBGE).

Termometro para decidir ONDE mostrar os anuncios: municipios com mais produtores tomando
credito rural (quantidade de contratos), mais volume financiado e mais soja/bovinos.

Saidas em SAIDA/radar/ (ou --saida): CSV (abre no Excel), HTML com tabela ordenavel e JSON.

Limites (dizer sempre a quem decide):
- SICOR mostra contratos NOVOS emitidos no ano, nao saldo devedor nem inadimplencia por municipio.
- E dado agregado e anonimo: nao ha nome, CPF ou contrato de ninguem (sigilo bancario).
  O radar serve para segmentar anuncio institucional por regiao, nunca para abordar pessoas.
"""
import csv
import json
import os
from bisect import bisect_right
from collections import defaultdict
from datetime import date

import sicor
from config_comercial import RADAR, UFS_ATENDIMENTO
from html_util import cartoes, esc, lista, numero, pagina, reais, reais_curto, tabela

# Norte do MT: mesorregiao do IBGE. Municipio criado depois de 2017 (ex.: Boa Esperanca do Norte) nao tem
# mesorregiao e vem com a regiao intermediaria "Sinop", que tambem e norte do estado.
NORTE_MT = {'Norte Mato-grossense', 'Sinop'}


def _float(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _progresso(rotulo):
    def aviso(n):
        print(f'\r   {rotulo}: {n} linhas', end='', flush=True)
    return aviso


def coletar_uf(uf, ano, cache=None):
    """Consolida um estado: ({codigo_ibge: registro do municipio}, [avisos de meses que falharam])."""
    uf = uf.upper()
    faltas = []
    print(f'\n[{uf} {ano}] municipios (IBGE)...', flush=True)
    try:
        nomes = sicor.municipios_ibge(uf)
    except Exception as e:  # nome oficial e so enfeite: segue com o nome do SICOR
        print(f'   aviso: IBGE indisponivel ({e}); usando nomes do SICOR')
        nomes = {}

    mun = defaultdict(lambda: {
        'uf': uf, 'codigo_ibge': '', 'municipio': '', 'mesorregiao': '',
        'qtd_custeio': 0, 'vl_custeio': 0.0, 'qtd_invest': 0, 'vl_invest': 0.0,
        'vl_agricola': 0.0, 'vl_pecuaria': 0.0, 'area_custeio_ha': 0.0,
        'vl_soja': 0.0, 'area_soja_ha': 0.0, 'vl_bovinos': 0.0,
    })

    linhas, falharam = sicor.totais_municipio(uf, ano, aviso=_progresso('custeio + investimento'), cache=cache)
    print()
    if falharam:
        faltas.append(f"{uf} contratos (custeio + investimento): meses {', '.join(map(str, falharam))} nao baixados")
    for r in linhas:
        cod = str(r.get('codMunicIbge') or '').strip()
        if not cod:
            continue
        m = mun[cod]
        m['codigo_ibge'] = cod
        m['municipio'] = m['municipio'] or (r.get('Municipio') or '').strip()
        qc, vc = int(r.get('QtdCusteio') or 0), _float(r.get('VlCusteio'))
        qi, vi = int(r.get('QtdInvestimento') or 0), _float(r.get('VlInvestimento'))
        m['qtd_custeio'] += qc
        m['vl_custeio'] += vc
        m['qtd_invest'] += qi
        m['vl_invest'] += vi
        m['area_custeio_ha'] += _float(r.get('AreaCusteio'))
        if r.get('Atividade') == '1':
            m['vl_agricola'] += vc + vi
        elif r.get('Atividade') == '2':
            m['vl_pecuaria'] += vc + vi

    for produto, campo_vl, campo_area in (('SOJA', 'vl_soja', 'area_soja_ha'), ('BOVINOS', 'vl_bovinos', None)):
        linhas, falharam = sicor.custeio_por_produto(uf, ano, produto, aviso=_progresso(f'custeio {produto.lower()}'),
                                                     cache=cache)
        print()
        if falharam:
            faltas.append(f"{uf} custeio {produto.lower()}: meses {', '.join(map(str, falharam))} nao baixados")
        for r in linhas:
            cod = str(r.get('codIbge') or '').strip()
            if not cod:
                continue
            m = mun[cod]
            m['codigo_ibge'] = cod
            m['municipio'] = m['municipio'] or (r.get('Municipio') or '').strip()
            m[campo_vl] += _float(r.get('VlCusteio'))
            if campo_area:
                m[campo_area] += _float(r.get('AreaCusteio'))

    for cod, m in mun.items():
        if cod in nomes:
            m['municipio'] = nomes[cod]['nome']
            m['mesorregiao'] = nomes[cod]['mesorregiao']
        m['qtd_total'] = m['qtd_custeio'] + m['qtd_invest']
        m['vl_total'] = m['vl_custeio'] + m['vl_invest']
        m['vl_medio_contrato'] = m['vl_total'] / m['qtd_total'] if m['qtd_total'] else 0.0
        m['vl_foco'] = m['vl_soja'] + m['vl_bovinos']
    return dict(mun), faltas


def _percentis(valores):
    ordenados = sorted(valores)
    n = len(ordenados)
    return lambda v: 100.0 * bisect_right(ordenados, v) / n if n else 0.0


def pontuar(registros):
    """Indice de prioridade 0-100: percentil de contratos, de valor e de soja+bovinos (pesos em config)."""
    if not registros:
        return registros
    p_qtd = _percentis([r['qtd_total'] for r in registros])
    p_vl = _percentis([r['vl_total'] for r in registros])
    p_foco = _percentis([r['vl_foco'] for r in registros])
    for r in registros:
        r['indice'] = round(RADAR['peso_contratos'] * p_qtd(r['qtd_total'])
                            + RADAR['peso_valor'] * p_vl(r['vl_total'])
                            + RADAR['peso_foco'] * p_foco(r['vl_foco']), 1)
    registros.sort(key=lambda r: (r['indice'], r['vl_total']), reverse=True)
    for i, r in enumerate(registros, 1):
        r['posicao'] = i
    return registros


def sugerir(registros, mt_todo=False, quantos=None):
    """Municipios prioritarios para o trafego. MT: so o Norte Mato-grossense, salvo mt_todo."""
    quantos = quantos or RADAR['top_sugestao']
    elegiveis = [r for r in registros if r['qtd_total'] > 0 and
                 (r['uf'] != 'MT' or mt_todo or r['mesorregiao'] in NORTE_MT)]
    saida = []
    for r in elegiveis[:quantos]:
        partes = [f"{numero(r['qtd_total'])} contratos", f"{reais(r['vl_total'])} financiados"]
        if r['vl_soja']:
            partes.append(f"soja {reais(r['vl_soja'])}")
        if r['vl_bovinos']:
            partes.append(f"bovinos {reais(r['vl_bovinos'])}")
        partes.append(f"média {reais(r['vl_medio_contrato'])} por contrato")
        saida.append({'municipio': r['municipio'], 'uf': r['uf'], 'indice': r['indice'],
                      'motivo': '; '.join(partes)})
    return saida


COLUNAS = [
    ('posicao', 'Posição'), ('uf', 'UF'), ('municipio', 'Município'), ('mesorregiao', 'Mesorregião'),
    ('indice', 'Índice'), ('qtd_total', 'Contratos'), ('vl_total', 'Valor total (R$)'),
    ('qtd_custeio', 'Contratos custeio'), ('vl_custeio', 'Custeio (R$)'),
    ('qtd_invest', 'Contratos investimento'), ('vl_invest', 'Investimento (R$)'),
    ('vl_medio_contrato', 'Média por contrato (R$)'), ('vl_agricola', 'Agrícola (R$)'),
    ('vl_pecuaria', 'Pecuária (R$)'), ('vl_soja', 'Custeio soja (R$)'), ('area_soja_ha', 'Área soja (ha)'),
    ('vl_bovinos', 'Custeio bovinos (R$)'), ('codigo_ibge', 'Código IBGE'),
]


def salvar_csv(registros, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow([t for _, t in COLUNAS])
        for r in registros:
            linha = []
            for c, _ in COLUNAS:
                v = r.get(c, '')
                if isinstance(v, float):
                    v = f'{v:.2f}'.replace('.', ',')
                linha.append(v)
            w.writerow(linha)


def salvar_html(registros, sugestoes, ufs, ano, caminho, faltas=None):
    total_qtd = sum(r['qtd_total'] for r in registros)
    total_vl = sum(r['vl_total'] for r in registros)
    total_soja = sum(r['vl_soja'] for r in registros)
    total_bov = sum(r['vl_bovinos'] for r in registros)
    top_sug = {(s['municipio'], s['uf']) for s in sugestoes}
    parcial = ' (ano em curso: dados parciais)' if int(ano) >= date.today().year else ''

    linhas, destaque = [], set()
    for i, r in enumerate(registros):
        if (r['municipio'], r['uf']) in top_sug:
            destaque.add(i)
        linhas.append([
            (str(r['posicao']), r['posicao']), r['uf'], r['municipio'], r['mesorregiao'],
            (numero(r['indice'], 1), r['indice']), (numero(r['qtd_total']), r['qtd_total']),
            (reais(r['vl_total']), round(r['vl_total'], 2)), (numero(r['qtd_custeio']), r['qtd_custeio']),
            (reais(r['vl_custeio']), round(r['vl_custeio'], 2)), (numero(r['qtd_invest']), r['qtd_invest']),
            (reais(r['vl_invest']), round(r['vl_invest'], 2)),
            (reais(r['vl_medio_contrato']), round(r['vl_medio_contrato'], 2)),
            (reais(r['vl_soja']), round(r['vl_soja'], 2)), (numero(r['area_soja_ha']), round(r['area_soja_ha'], 1)),
            (reais(r['vl_bovinos']), round(r['vl_bovinos'], 2)),
        ])
    cab = ['Pos.', 'UF', 'Município', 'Mesorregião', 'Índice', 'Contratos', 'Valor total', 'Contr. custeio',
           'Custeio', 'Contr. invest.', 'Investimento', 'Média/contrato', 'Custeio soja', 'Área soja (ha)',
           'Custeio bovinos']

    sug_html = '<ol class="lista">' + ''.join(
        f"<li><b>{esc(s['municipio'])}/{esc(s['uf'])}</b> - índice {numero(s['indice'], 1)} - {esc(s['motivo'])}</li>"
        for s in sugestoes) + '</ol>'
    como_ler = lista([
        'Índice (0 a 100) = 40% quantidade de contratos + 35% valor financiado + 25% custeio de soja e bovinos, '
        'cada um comparado com os demais municípios da lista (pesos em COMERCIAL/config_comercial.py).',
        'Muitos contratos = muitos produtores com crédito rural = mais público para o anúncio.',
        'Média por contrato alta = dívidas maiores (produtor de porte médio/grande).',
        'Mato Grosso: a sugestão considera só o Norte Mato-grossense (a tabela mostra o estado todo).',
        'Use a lista para segmentar os anúncios por cidade (raio) no Gerenciador de Anúncios e compare o custo '
        'por lead de cada região no relatório do Meta Ads antes de mudar orçamento.',
    ])
    limites = lista([
        'Fonte: SICOR/Banco Central (Matriz de Dados do Crédito Rural) + IBGE. Dado público e agregado.',
        'O SICOR mostra contratos novos do ano, não o saldo devedor nem a inadimplência por município.',
        'Não há nome, CPF ou contrato de ninguém: o radar orienta anúncio institucional por região, '
        'nunca abordagem individual (Provimento 205/2021 da OAB).',
    ])
    blocos = []
    if faltas:
        blocos.append(('DADOS INCOMPLETOS - rodar de novo', lista(
            faltas + ['O servidor do Banco Central não respondeu nesses meses. Rode o mesmo comando de novo: '
                      'os meses já baixados ficam guardados e só os que faltam são buscados.'], 'alerta')))
    blocos += [
        (None, cartoes([(numero(total_qtd), 'contratos de crédito rural'), (reais_curto(total_vl), 'financiados'),
                        (reais_curto(total_soja), 'custeio de soja'), (reais_curto(total_bov), 'custeio de bovinos'),
                        (numero(len(registros)), 'municípios')])),
        ('Onde investir no tráfego (sugestão)', sug_html),
        ('Como ler', como_ler),
        ('Todos os municípios (clique no título da coluna para ordenar)', tabela(cab, linhas, destaque)),
        ('Limites do dado', limites),
    ]
    titulo = 'Radar do Crédito Rural'
    sub = f"{', '.join(ufs)} - contratos emitidos em {ano}{parcial}"
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(pagina(titulo, sub, blocos, 'Fonte: Banco Central (SICOR) e IBGE.'))


def gerar(ufs=None, ano=None, saida=None, mt_todo=False):
    import ambiente
    ufs = [u.strip().upper() for u in (ufs or UFS_ATENDIMENTO) if u.strip()]
    ano = int(ano or date.today().year - 1)
    pasta = saida or ambiente.pasta_saida('radar')
    os.makedirs(pasta, exist_ok=True)

    cache = os.path.join(pasta, 'cache')
    registros, faltas = [], []
    for uf in ufs:
        dados_uf, faltas_uf = coletar_uf(uf, ano, cache)
        registros += list(dados_uf.values())
        faltas += faltas_uf
    registros = pontuar([r for r in registros if r['qtd_total'] or r['vl_foco']])
    sugestoes = sugerir(registros, mt_todo)

    base = os.path.join(pasta, f"radar_{'-'.join(ufs)}_{ano}" + ('_INCOMPLETO' if faltas else ''))
    salvar_csv(registros, base + '.csv')
    salvar_html(registros, sugestoes, ufs, ano, base + '.html', faltas)
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'ufs': ufs, 'ano': ano, 'incompleto': faltas, 'sugestoes': sugestoes, 'municipios': registros},
                  f, ensure_ascii=False, indent=1)

    print(f'\n=== RADAR {", ".join(ufs)} {ano} ===')
    if faltas:
        print('ATENCAO - DADOS INCOMPLETOS (o servidor do Banco Central falhou; rode de novo para completar):')
        for x in faltas:
            print(f'  - {x}')
    print(f'{len(registros)} municipios | {numero(sum(r["qtd_total"] for r in registros))} contratos | '
          f'{reais(sum(r["vl_total"] for r in registros))}')
    print('\nTop 10 do indice:')
    for r in registros[:10]:
        print(f"  {r['posicao']:>2}. {r['municipio']}/{r['uf']:<3} indice {r['indice']:>5}  "
              f"{numero(r['qtd_total']):>6} contratos  {reais(r['vl_total']):>20}  soja {reais(r['vl_soja'])}")
    print('\nSugestao para o trafego:')
    for s in sugestoes[:10]:
        print(f"  - {s['municipio']}/{s['uf']}: {s['motivo']}")
    print(f'\nArquivos:\n  {base}.csv\n  {base}.html\n  {base}.json')
    return base

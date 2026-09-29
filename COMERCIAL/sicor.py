"""
Dados PUBLICOS de credito rural (sem credencial):

- SICOR / Banco Central (Olinda OData): contratos de credito rural por municipio.
  Base: https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/
- IBGE (servicodados): nome oficial dos municipios e mesorregiao (ex.: Norte Mato-grossense).

Pegadinhas da API do SICOR (conferidas em campo):
- `cdEstado` NAO e o codigo IBGE da UF: e um codigo interno do BCB (RO = 22, MT = 14).
- O filtro precisa ir com espaco codificado como %20 (quote com safe="'"); nao usar params={} do requests.
- Nao aceita $count. $skip junto com $filter volta SEMPRE 500 (paginacao quebrada, 09/2026):
  a busca e feita mes a mes (MesEmissao), com $top alto e erro se bater no limite.
- A API devolve 500 "Erro desconhecido" de vez em quando: repetir a chamada resolve.
- As linhas de CusteioMunicipioProduto/InvestMunicipioProduto sao AGREGADAS (nao sao contratos);
  a QUANTIDADE de contratos so existe em CusteioInvestimentoComercialIndustrialSemFiltros.
- nomeProduto vem entre aspas: '"SOJA"', '"BOVINOS"'.
- SICOR registra so as EMISSOES (contratos novos no ano), nao o saldo devedor nem a inadimplencia.
"""
import json
import os
import time
from urllib.parse import quote

import requests

BASE = 'https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata'
IBGE = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios'

# cdEstado do SICOR -> UF (codigo interno do BCB, validado por amostragem)
SICOR_UF = {
    '1': 'AC', '2': 'AL', '3': 'AM', '5': 'BA', '6': 'CE', '8': 'ES', '10': 'GO', '11': 'MA',
    '12': 'MG', '13': 'MS', '14': 'MT', '15': 'PA', '16': 'PB', '17': 'PE', '18': 'PI', '19': 'PR',
    '20': 'RJ', '21': 'RN', '22': 'RO', '23': 'RR', '24': 'RS', '25': 'SC', '26': 'SE', '27': 'SP',
    '28': 'TO',
}
UF_SICOR = {v: k for k, v in SICOR_UF.items()}
ATIVIDADE = {'1': 'AGRICOLA', '2': 'PECUARIA'}


class ErroSicor(RuntimeError):
    pass


def _texto(resposta):
    try:
        return resposta.content.decode('utf-8')
    except UnicodeDecodeError:
        return resposta.content.decode('latin-1')


ESPERAS = (5, 15, 30, 60)   # segundos entre tentativas (o servidor do BCB oscila muito)


def _get(url, timeout=150):
    ultimo = None
    for i in range(len(ESPERAS) + 1):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return json.loads(_texto(r))
            ultimo = f'HTTP {r.status_code}'
        except (requests.RequestException, ValueError) as e:
            ultimo = type(e).__name__
        if i < len(ESPERAS):
            time.sleep(ESPERAS[i])
    raise ErroSicor(f'SICOR nao respondeu depois de {len(ESPERAS) + 1} tentativas ({ultimo})')


def filtro(uf=None, ano=None, **iguais):
    partes = []
    if uf:
        cd = UF_SICOR.get(uf.upper())
        if not cd:
            raise ValueError(f'UF fora do mapeamento do SICOR: {uf}')
        partes.append(f"cdEstado eq '{cd}'")
    if ano:
        partes.append(f"AnoEmissao eq '{ano}'")
    for campo, valor in iguais.items():
        partes.append(f"{campo} eq '{valor}'")
    return ' and '.join(partes)


LIMITE = 50000   # linhas por consulta; se vier exatamente isso, o mes foi cortado


def buscar(entidade, filtro_odata='', campos=None, limite=LIMITE):
    """
    Uma consulta ao SICOR, sem paginacao. ATENCAO: nesta API o $skip junto com $filter
    devolve sempre 500 (conferido em 09/2026), por isso a paginacao e feita por MES
    (ver buscar_ano), e nunca por $skip.
    """
    qs = ['$format=json', f'$top={limite}']
    if filtro_odata:
        qs.append('$filter=' + quote(filtro_odata, safe="'"))
    if campos:
        qs.append('$select=' + ','.join(campos))
    linhas = _get(f'{BASE}/{entidade}?' + '&'.join(qs)).get('value', [])
    if len(linhas) >= limite:
        raise ErroSicor(f'{entidade}: a consulta bateu no limite de {limite} linhas ({filtro_odata}); '
                        'dividir mais o filtro')
    return linhas


def _mes_fechado(ano, mes):
    from datetime import date
    hoje = date.today()
    return (int(ano), mes) < (hoje.year, hoje.month)


def buscar_ano(entidade, uf, ano, campos=None, aviso=None, cache=None, **iguais):
    """
    Todas as linhas de um ano, consultando MES A MES (01 a 12), um de cada vez (em paralelo o
    servidor do BCB recusa mais). Meses ja fechados ficam em cache (pasta `cache`) para a proxima
    rodada nao baixar de novo. Devolve (linhas, meses_que_falharam).
    """
    linhas, falharam = [], []
    for mes in range(1, 13):
        arq = None
        if cache:
            extra = '_'.join(str(v).strip('"') for v in iguais.values())
            arq = os.path.join(cache, f"{entidade}_{uf}_{ano}_{mes:02d}{'_' + extra if extra else ''}.json")
            if os.path.exists(arq):
                with open(arq, encoding='utf-8') as f:
                    linhas += json.load(f)
                if aviso:
                    aviso(len(linhas))
                continue
        try:
            lote = buscar(entidade, filtro(uf, ano, MesEmissao=f'{mes:02d}', **iguais), campos)
        except ErroSicor:
            falharam.append(mes)
            continue
        linhas += lote
        if arq and _mes_fechado(ano, mes):
            os.makedirs(cache, exist_ok=True)
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(lote, f, ensure_ascii=False)
        if aviso:
            aviso(len(linhas))
    return linhas, falharam


def totais_municipio(uf, ano, aviso=None, cache=None):
    """Quantidade e valor de custeio/investimento por municipio (com atividade agricola/pecuaria)."""
    campos = ['codMunicIbge', 'cdMunicipio', 'Municipio', 'Atividade', 'QtdCusteio', 'VlCusteio',
              'QtdInvestimento', 'VlInvestimento', 'AreaCusteio', 'AreaInvestimento']
    return buscar_ano('CusteioInvestimentoComercialIndustrialSemFiltros', uf, ano, campos, aviso, cache)


def custeio_por_produto(uf, ano, produto, aviso=None, cache=None):
    """Valor e area de custeio de um produto (ex.: SOJA, BOVINOS) por municipio."""
    campos = ['codIbge', 'Municipio', 'VlCusteio', 'AreaCusteio']
    return buscar_ano('CusteioMunicipioProduto', uf, ano, campos, aviso, cache, nomeProduto=f'"{produto}"')


def municipios_ibge(uf):
    """{codigo_ibge: {'nome', 'mesorregiao'}} dos municipios da UF (API publica do IBGE)."""
    r = requests.get(IBGE.format(uf=uf.upper()), timeout=60)
    r.raise_for_status()
    saida = {}
    for m in r.json():
        meso = ''
        micro = m.get('microrregiao') or {}
        if micro.get('mesorregiao'):
            meso = micro['mesorregiao'].get('nome', '')
        elif m.get('regiao-imediata'):
            inter = m['regiao-imediata'].get('regiao-intermediaria') or {}
            meso = inter.get('nome', '')
        saida[str(m['id'])] = {'nome': m['nome'], 'mesorregiao': meso}
    return saida

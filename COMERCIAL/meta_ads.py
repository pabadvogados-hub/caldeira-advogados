"""
RELATORIO DO META ADS para quem monitora as campanhas (sem agencia).

Le a conta de anuncio (so leitura) e entrega, em linguagem simples:
- gasto, alcance, cliques, leads (conversas no WhatsApp + formularios) e custo por lead (CPL);
- por campanha, por anuncio (ranking) e por regiao (estado de quem viu o anuncio);
- alertas: CPL subiu contra o periodo anterior, anuncio gastando sem lead, publico cansado, criativo fraco;
- recomendacoes do que avaliar.

NADA e alterado na conta: pausar, ativar ou mudar orcamento e decisao humana no Gerenciador de Anuncios.
Credenciais: META_ACCESS_TOKEN e META_AD_ACCOUNT_ID em config/.env. Sem elas: --exemplo.
"""
import json
import os
from datetime import date, timedelta

import ambiente
from config_comercial import META
from html_util import cartoes, lista, numero, pagina, reais, tabela

EXEMPLO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exemplos', 'META_ADS_EXEMPLO.json')


def periodos(dias, hoje=None):
    hoje = hoje or date.today()
    ate = hoje - timedelta(days=1)
    desde = ate - timedelta(days=dias - 1)
    ate_ant = desde - timedelta(days=1)
    desde_ant = ate_ant - timedelta(days=dias - 1)
    return (desde.isoformat(), ate.isoformat()), (desde_ant.isoformat(), ate_ant.isoformat())


def coletar(dias):
    import meta_ads_integration as meta
    if not meta.configurado():
        raise SystemExit('Meta Ads nao configurado: preencha META_ACCESS_TOKEN e META_AD_ACCOUNT_ID em config/.env '
                         '(ou rode com --exemplo).')
    (d1, a1), (d0, a0) = periodos(dias)
    print(f'   periodo {d1} a {a1} (comparando com {d0} a {a0})')
    try:
        return {
            'periodo': [d1, a1], 'periodo_anterior': [d0, a0],
            'conta': meta.insights(level='account', desde=d1, ate=a1),
            'conta_anterior': meta.insights(level='account', desde=d0, ate=a0),
            'campanhas': meta.insights(level='campaign', desde=d1, ate=a1),
            'campanhas_anterior': meta.insights(level='campaign', desde=d0, ate=a0),
            'anuncios': meta.insights(level='ad', desde=d1, ate=a1),
            'regioes': meta.insights(level='account', desde=d1, ate=a1, breakdowns='region',
                                     campos='spend,impressions,reach,clicks,inline_link_clicks,actions'),
        }
    except meta.ErroMeta as e:
        raise SystemExit(f'ERRO na Meta API: {e}')


def metricas(linha):
    from meta_ads_integration import conversas, formularios
    gasto = float(linha.get('spend') or 0)
    acoes = linha.get('actions')
    conv, form = conversas(acoes), formularios(acoes)
    leads = conv + form
    impressoes = int(float(linha.get('impressions') or 0))
    cliques = int(float(linha.get('inline_link_clicks') or linha.get('clicks') or 0))
    return {
        'gasto': gasto, 'impressoes': impressoes, 'alcance': int(float(linha.get('reach') or 0)),
        'cliques': cliques, 'ctr': (100.0 * cliques / impressoes) if impressoes else 0.0,
        'frequencia': float(linha.get('frequency') or 0), 'conversas': conv, 'formularios': form,
        'leads': leads, 'cpl': (gasto / leads) if leads else None,
    }


def _var(atual, anterior):
    if atual is None or not anterior:
        return None
    return 100.0 * (atual - anterior) / anterior


def analisar(dados):
    conta = metricas((dados.get('conta') or [{}])[0])
    conta_ant = metricas((dados.get('conta_anterior') or [{}])[0])
    ant_por_camp = {c.get('campaign_id'): metricas(c) for c in dados.get('campanhas_anterior') or []}
    cpl_ref = META['cpl_alvo'] or conta['cpl']

    campanhas = []
    for c in dados.get('campanhas') or []:
        m = metricas(c)
        m.update({'id': c.get('campaign_id'), 'nome': c.get('campaign_name', '')})
        m['cpl_anterior'] = (ant_por_camp.get(m['id']) or {}).get('cpl')
        m['var_cpl'] = _var(m['cpl'], m['cpl_anterior'])
        campanhas.append(m)
    campanhas.sort(key=lambda x: x['gasto'], reverse=True)

    anuncios = []
    for a in dados.get('anuncios') or []:
        m = metricas(a)
        m.update({'id': a.get('ad_id'), 'nome': a.get('ad_name', ''), 'campanha': a.get('campaign_name', ''),
                  'conjunto': a.get('adset_name', '')})
        anuncios.append(m)
    com_lead = sorted([a for a in anuncios if a['leads']], key=lambda x: x['cpl'])
    sem_lead = sorted([a for a in anuncios if not a['leads']], key=lambda x: x['gasto'], reverse=True)
    ranking = com_lead + sem_lead

    regioes = []
    for r in dados.get('regioes') or []:
        m = metricas(r)
        m['regiao'] = r.get('region') or '-'
        regioes.append(m)
    regioes.sort(key=lambda x: x['gasto'], reverse=True)

    alertas, recomendacoes = [], []
    limite = META['alerta_cpl_subiu_pct']
    v = _var(conta['cpl'], conta_ant['cpl'])
    if v is not None and v > limite:
        alertas.append(f"Custo por lead da conta subiu {numero(v)}%: {reais(conta_ant['cpl'])} -> {reais(conta['cpl'])}.")
    if conta['gasto'] and not conta['leads']:
        alertas.append(f"A conta gastou {reais(conta['gasto'])} e não gerou nenhum lead no período.")
    for c in campanhas:
        if c['var_cpl'] is not None and c['var_cpl'] > limite:
            alertas.append(f"Campanha \"{c['nome']}\": custo por lead subiu {numero(c['var_cpl'])}% "
                           f"({reais(c['cpl_anterior'])} -> {reais(c['cpl'])}).")
        if META['cpl_alvo'] and c['cpl'] and c['cpl'] > META['cpl_alvo']:
            alertas.append(f"Campanha \"{c['nome']}\": custo por lead {reais(c['cpl'])} acima da meta "
                           f"{reais(META['cpl_alvo'])}.")
    minimo = max(META['gasto_minimo_sem_lead'], 2 * (cpl_ref or 0)) if cpl_ref else META['gasto_minimo_sem_lead']
    for a in sem_lead:
        if a['gasto'] >= minimo:
            alertas.append(f"Anúncio \"{a['nome']}\" gastou {reais(a['gasto'])} sem nenhum lead.")
            recomendacoes.append(f"Avaliar pausar o anúncio \"{a['nome']}\" (gastou {reais(a['gasto'])} sem lead) "
                                 'e passar a verba para o anúncio que mais traz conversa.')
    for a in anuncios:
        if a['frequencia'] > META['frequencia_alta']:
            alertas.append(f"Anúncio \"{a['nome']}\": frequência {numero(a['frequencia'], 1)} (as mesmas pessoas "
                           'estão vendo muitas vezes).')
            recomendacoes.append(f"Trocar o vídeo/imagem do anúncio \"{a['nome']}\" ou ampliar o público: público cansado.")
        if a['impressoes'] >= 1000 and a['ctr'] < META['ctr_baixo_pct']:
            recomendacoes.append(f"Anúncio \"{a['nome']}\" tem poucos cliques ({numero(a['ctr'], 2)}% dos que viram): "
                                 'testar outro título, outra imagem ou os primeiros 3 segundos do vídeo.')
    if com_lead:
        melhor = com_lead[0]
        recomendacoes.insert(0, f"Melhor anúncio: \"{melhor['nome']}\" - {melhor['leads']} lead(s) a {reais(melhor['cpl'])} "
                                'cada. Se quiser crescer, aumente o orçamento do conjunto dele aos poucos '
                                '(no máximo 20% a cada 2 ou 3 dias) e acompanhe o custo por lead.')
    reg_lead = [r for r in regioes if r['leads']]
    if reg_lead:
        rb = min(reg_lead, key=lambda r: r['cpl'])
        recomendacoes.append(f"Região com lead mais barato: {rb['regiao']} ({reais(rb['cpl'])} por lead).")
    for r in regioes:
        if r['gasto'] >= minimo and not r['leads']:
            alertas.append(f"Região {r['regiao']}: gastou {reais(r['gasto'])} sem lead.")
            recomendacoes.append(f"Avaliar excluir a região {r['regiao']} do público ou reduzir a verba nela.")
    focos = {f.lower() for f in META['regioes_foco']}
    fora = [r for r in regioes if r['regiao'].lower() not in focos and r['gasto'] > 0]
    if fora:
        gasto_fora = sum(r['gasto'] for r in fora)
        if conta['gasto'] and gasto_fora / conta['gasto'] > 0.2:
            alertas.append(f"{numero(100 * gasto_fora / conta['gasto'])}% da verba foi para fora de "
                           f"{', '.join(META['regioes_foco'])}.")
    if not alertas:
        recomendacoes.append('Nenhum alerta no período: manter as campanhas como estão e olhar de novo amanhã.')
    recomendacoes.append('Antes de subir anúncio novo: sem promessa de resultado, sem preço de honorário, sem '
                         '"garantia" e sem sensacionalismo (Provimento 205/2021 da OAB).')
    return {'conta': conta, 'conta_anterior': conta_ant, 'var_cpl_conta': v, 'campanhas': campanhas,
            'ranking': ranking, 'regioes': regioes, 'alertas': alertas, 'recomendacoes': recomendacoes}


def texto(dados, a, dias):
    c, c0 = a['conta'], a['conta_anterior']
    d1, a1 = dados['periodo']
    L = [f'RELATÓRIO META ADS - {"ontem" if dias == 1 else f"últimos {dias} dias"} ({d1} a {a1})', '',
         f"Gasto: {reais(c['gasto'])} | Leads: {c['leads']} (conversas {c['conversas']}, formulários {c['formularios']})",
         f"Custo por lead: {reais(c['cpl']) if c['cpl'] else '-'} (período anterior: {reais(c0['cpl']) if c0['cpl'] else '-'})",
         f"Alcance: {numero(c['alcance'])} pessoas | Cliques: {numero(c['cliques'])} | "
         f"Taxa de clique: {numero(c['ctr'], 2)}%", '']
    L.append('ALERTAS' if a['alertas'] else 'ALERTAS: nenhum')
    L += [f'  ! {x}' for x in a['alertas']]
    L += ['', 'O QUE AVALIAR (nada foi mudado na conta; a decisão é sua)']
    L += [f'  - {x}' for x in a['recomendacoes']]
    L += ['', 'CAMPANHAS']
    for x in a['campanhas']:
        L.append(f"  {x['nome']}: {reais(x['gasto'])} | {x['leads']} leads | CPL {reais(x['cpl']) if x['cpl'] else '-'}"
                 + (f" ({'+' if x['var_cpl'] > 0 else ''}{numero(x['var_cpl'])}%)" if x['var_cpl'] is not None else ''))
    L += ['', 'RANKING DE ANÚNCIOS (menor custo por lead primeiro)']
    for i, x in enumerate(a['ranking'], 1):
        L.append(f"  {i}. {x['nome']} [{x['campanha']}]: {reais(x['gasto'])} | {x['leads']} leads | "
                 f"CPL {reais(x['cpl']) if x['cpl'] else 'sem lead'}")
    if a['regioes']:
        L += ['', 'REGIÕES']
        for r in a['regioes']:
            L.append(f"  {r['regiao']}: {reais(r['gasto'])} | {r['leads']} leads | CPL {reais(r['cpl']) if r['cpl'] else '-'}")
    return '\n'.join(L) + '\n'


def html(dados, a, dias):
    c = a['conta']
    d1, a1 = dados['periodo']
    var = a['var_cpl_conta']
    blocos = [
        (None, cartoes([
            (reais(c['gasto']), 'gasto no período'), (str(c['leads']), 'leads (conversas + formulários)'),
            (reais(c['cpl']) if c['cpl'] else '-', 'custo por lead'
             + (f" ({'+' if var > 0 else ''}{numero(var)}% vs. anterior)" if var is not None else '')),
            (numero(c['alcance']), 'pessoas alcançadas'), (numero(c['ctr'], 2) + '%', 'taxa de clique')])),
        ('Alertas', lista(a['alertas'] or ['Nenhum alerta no período.'], 'alerta' if a['alertas'] else 'ok')),
        ('O que avaliar (nada foi alterado na conta)', lista(a['recomendacoes'])),
        ('Campanhas', tabela(['Campanha', 'Gasto', 'Leads', 'CPL', 'CPL anterior', 'Variação', 'Cliques', 'Alcance'], [
            [x['nome'], (reais(x['gasto']), x['gasto']), (str(x['leads']), x['leads']),
             (reais(x['cpl']) if x['cpl'] else '-', x['cpl'] or 0),
             (reais(x['cpl_anterior']) if x['cpl_anterior'] else '-', x['cpl_anterior'] or 0),
             (f"{numero(x['var_cpl'])}%" if x['var_cpl'] is not None else '-', x['var_cpl'] or 0),
             (numero(x['cliques']), x['cliques']), (numero(x['alcance']), x['alcance'])] for x in a['campanhas']])),
        ('Ranking de anúncios', tabela(['#', 'Anúncio', 'Campanha', 'Gasto', 'Leads', 'CPL', 'CTR', 'Frequência'], [
            [(str(i), i), x['nome'], x['campanha'], (reais(x['gasto']), x['gasto']), (str(x['leads']), x['leads']),
             (reais(x['cpl']) if x['cpl'] else 'sem lead', x['cpl'] or 999999),
             (numero(x['ctr'], 2) + '%', round(x['ctr'], 2)), (numero(x['frequencia'], 1), x['frequencia'])]
            for i, x in enumerate(a['ranking'], 1)])),
        ('Regiões (estado de quem viu o anúncio)', tabela(['Região', 'Gasto', 'Leads', 'CPL', 'Cliques'], [
            [r['regiao'], (reais(r['gasto']), r['gasto']), (str(r['leads']), r['leads']),
             (reais(r['cpl']) if r['cpl'] else '-', r['cpl'] or 999999), (numero(r['cliques']), r['cliques'])]
            for r in a['regioes']])),
    ]
    sub = f"{'Ontem' if dias == 1 else f'Últimos {dias} dias'} ({d1} a {a1})" + (' - DADOS DE EXEMPLO' if dados.get('_exemplo') else '')
    return pagina('Relatório Meta Ads', sub, blocos, 'Somente leitura: nenhuma campanha foi alterada.')


def relatorio(dias=7, exemplo=False, saida=None):
    print(f'\n=== META ADS ({dias} dia(s)) ===')
    if exemplo:
        with open(EXEMPLO, encoding='utf-8') as f:
            dados = json.load(f)
        dados['_exemplo'] = True
        (d1, a1), (d0, a0) = periodos(dias)
        dados['periodo'], dados['periodo_anterior'] = [d1, a1], [d0, a0]
        print('   usando dados FICTICIOS (exemplos/META_ADS_EXEMPLO.json)')
    else:
        dados = coletar(dias)
    analise = analisar(dados)
    pasta = saida or ambiente.pasta_saida('meta_ads')
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, f"{date.today().isoformat()}_meta_{dias}d" + ('_EXEMPLO' if exemplo else ''))
    txt = texto(dados, analise, dias)
    with open(base + '.txt', 'w', encoding='utf-8') as f:
        f.write(txt)
    with open(base + '.html', 'w', encoding='utf-8') as f:
        f.write(html(dados, analise, dias))
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'dados': dados, 'analise': analise}, f, ensure_ascii=False, indent=1, default=str)
    print(txt)
    print(f'Arquivos: {base}.txt | .html | .json')
    return base

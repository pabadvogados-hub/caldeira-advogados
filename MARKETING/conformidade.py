"""
Verificador de conformidade da PUBLICIDADE da advocacia - Caldeira Advogados Associados.

Base: Codigo de Etica e Disciplina da OAB (CED, arts. 39 a 47), Estatuto da Advocacia (art. 34, IV)
e Provimento 205/2021 do Conselho Federal da OAB.

Funciona por REGRAS (sem IA, sem custo): procura termos proibidos ou arriscados e devolve alertas
    {trecho, contexto, regra, gravidade (BLOQUEIA | ATENCAO), sugestao, posicao, onde}

- Todo conteudo gerado pelo modulo de marketing passa por aqui.
- Com qualquer BLOQUEIA o material sai marcado "NÃO PUBLICAR ATÉ CORRIGIR".
- Sem alerta NAO quer dizer aprovado: a revisao do advogado antes de publicar continua obrigatoria.
- Regra em duvida foi tratada como proibida; artigo sem certeza leva [CONFERIR] no texto da regra.

Uso direto:
    python MARKETING/conformidade.py arquivo.txt
    python MARKETING/conformidade.py --texto "Consulta gratis, resultado garantido!"
"""
import argparse
import re
import sys
import unicodedata

BLOQUEIA = 'BLOQUEIA'
ATENCAO = 'ATENCAO'

SITUACAO_BLOQUEADO = 'NÃO PUBLICAR ATÉ CORRIGIR'
SITUACAO_ATENCAO = 'REVISAR OS ALERTAS ANTES DE PUBLICAR'
SITUACAO_LIVRE = 'SEM ALERTAS AUTOMÁTICOS (a revisão do advogado continua obrigatória)'

# Referencias usadas nas regras (texto que aparece no alerta)
_R_PROMESSA = ('Promessa/garantia de resultado ou afirmação que pode induzir a erro '
               '(CED, art. 39; Prov. 205/2021, art. 3º, II, e art. 6º [CONFERIR])')
_R_MERCANTIL = ('Mercantilização: valor, gratuidade, desconto ou forma de pagamento como chamariz '
                '(Prov. 205/2021, art. 3º, I; CED, art. 39)')
_R_AUTOENGRANDECER = ('Autoengrandecimento ou expressão persuasiva '
                      '(Prov. 205/2021, art. 3º, IV)')
_R_COMPARACAO = 'Comparação com colegas ou concorrentes (Prov. 205/2021, art. 3º, IV)'
_R_ESPECIALIDADE = ('Anúncio de especialidade exige título certificado ou notória especialização '
                    '(Prov. 205/2021, art. 3º, III [CONFERIR])')
_R_URGENCIA = ('Urgência apelativa / pressão para contratar = captação e mercantilização '
               '(CED, arts. 7º e 39; Prov. 205/2021, art. 3º, IV)')
_R_SENSACIONALISMO = ('Sensacionalismo ou medo exagerado; linguagem incompatível com a sobriedade '
                      '(CED, arts. 39 e 42, III [CONFERIR])')
_R_CAPTACAO = ('Possível captação indevida de clientela '
               '(CED, art. 7º; Estatuto da Advocacia, art. 34, IV)')
_R_BRINDE = ('Brinde, sorteio ou vantagem para atrair cliente '
             '(Prov. 205/2021, art. 3º, V [CONFERIR]; CED, art. 7º)')
_R_CASO = ('Resultado de cliente, caso concreto ou volume de clientes/causas '
           '(Prov. 205/2021, art. 6º [CONFERIR]; CED, art. 42, IV)')
_R_DADO = 'Número/estatística: só com fonte oficial citada; nunca inventar dado'
_R_SIGILO = 'Dado que identifica pessoa ou processo (sigilo profissional; CED, art. 42, IV)'
_R_ESTRUTURA = ('Estrutura física do escritório ou ostentação '
                '(Prov. 205/2021, art. 6º [CONFERIR])')
_R_CONSULTA = ('Responder consulta jurídica com habitualidade em meio de comunicação '
               '(CED, art. 42, I [CONFERIR])')
_R_LITIGIO = ('Incentivo a litígio; o advogado deve estimular a solução consensual '
              '(CED, art. 2º, parágrafo único [CONFERIR])')
_R_PENDENTE = 'Marcação pendente no texto'

# Cada regra: id, padrao (no texto normalizado: minusculo e sem acento), gravidade, regra, sugestao,
# exceto (regex no entorno que desfaz o alerta), agrava (regex no entorno que sobe para BLOQUEIA).
REGRAS = [
    # ---------------- pendencias ----------------
    dict(id='pendente', p=r'\[(conferir|preencher)[^\]]*\]', g=BLOQUEIA, regra=_R_PENDENTE,
         s='Resolver o [CONFERIR]/[PREENCHER] (conferir a informação ou retirar o trecho) antes de publicar.'),

    # ---------------- promessa / garantia de resultado ----------------
    dict(id='garantia', g=BLOQUEIA, regra=_R_PROMESSA,
         p=r'\bgarant(imos|o|ido|ida|idos|idas|ia de (resultado|sucesso|exito|vitoria|ganho|aprovacao'
           r'|prorrogacao|alongamento|liminar|decisao))\b',
         s='Retire a garantia. Use "a lei prevê", "pode ser pedido", "cada caso depende de análise".'),
    dict(id='garanta', g=BLOQUEIA, regra=_R_PROMESSA, p=r'\bgaranta(m)?\b',
         s='Imperativo que sugere resultado. Troque por "Conheça seus direitos" ou "Entenda como funciona".'),
    dict(id='garante', g=ATENCAO, regra=_R_PROMESSA, p=r'\bgarante(m)?\b',
         s='Se for a lei, prefira "a lei prevê". O escritório nunca garante resultado.'),
    dict(id='cem_por_cento', g=BLOQUEIA, regra=_R_PROMESSA, p=r'\b100 ?%|\bcem por cento\b',
         s='Retire "100%". Nenhum resultado jurídico é certo.'),
    dict(id='certeza', g=BLOQUEIA, regra=_R_PROMESSA,
         p=r'\b(resultado|sucesso|vitoria|exito|aprovacao) (certo|certa|garantid[oa]|assegurad[oa])\b'
           r'|\bcausa ganha\b|\bcerteza (de|do|da) (resultado|exito|vitoria|sucesso|ganho|aprovacao)\b'
           r'|\bsem risco\b|\brisco zero\b|\bnao tem como perder\b',
         s='Retire a certeza de resultado. Cada caso depende dos documentos e da análise do juiz.'),
    dict(id='com_certeza', g=ATENCAO, regra=_R_PROMESSA, p=r'\bcom certeza\b',
         s='Evite "com certeza" perto de resultado; prefira "em regra" ou "pode".'),
    dict(id='ganhar_resultado', g=BLOQUEIA, regra=_R_PROMESSA,
         p=r'\b(vai|vamos|voce vai|o senhor vai) ganhar\b|\bganhamos\b|\bvencemos\b'
           r'|\bganh(e|ar) (a|sua|essa) (causa|acao|prorrogacao|disputa)\b',
         s='Não fale em ganhar causa. Explique o direito e os requisitos.'),
    dict(id='ganhe', g=ATENCAO, regra=_R_AUTOENGRANDECER, p=r'\bganhe\b',
         s='"Ganhe" é linguagem de venda; reescreva de forma informativa.'),
    dict(id='resolva', g=BLOQUEIA, regra=_R_PROMESSA,
         p=r'\bresolv(a|emos|e) (ja|agora|hoje|rapido|de vez|seu|sua|o seu|a sua|suas|seus)\b'
           r'|\b(acabe|acabamos|livre-se|livre se|se livre|zere|zeramos|elimine|eliminamos|quite)'
           r' (com )?(a |as |sua |suas |seu |seus |os |o )?(divida|dividas|juros|debito|debitos|problema|problemas)\b'
           r'|\bfim d(a|as) (sua |suas )?dividas?\b',
         s='Promessa de resolver o problema. Troque por "Entenda o que a lei prevê" / "Conheça os caminhos".'),
    dict(id='limpe_nome', g=BLOQUEIA, regra=_R_PROMESSA, p=r'\b(limpe|limpamos|limpa|tiramos) (o |seu |o seu |teu )?nome\b',
         s='Promessa de "limpar o nome". Explique que a Justiça pode ser chamada a decidir sobre a negativação.'),
    dict(id='limpar_nome', g=ATENCAO, regra=_R_PROMESSA, p=r'\blimpar (o |seu |o seu )?nome\b',
         s='Cuidado para não soar como promessa; fale em "pedir que o nome não seja negativado".'),
    dict(id='prazo_resultado', g=BLOQUEIA, regra=_R_PROMESSA,
         p=r'\b(liminar|resultado|prorrogacao|decisao|sentenca|solucao|aprovacao) (em|ate|em ate) \d+ ?(dias|horas|semanas|meses)\b',
         s='Não prometa prazo de resultado. O tempo depende do banco e do Judiciário.'),
    dict(id='prazo_generico', g=ATENCAO, regra=_R_PROMESSA, p=r'\b(em|ate|em ate) \d+ ?(dias|horas|semanas)\b',
         s='Se for prazo legal (ex.: prazo para defesa), cite a norma; se for prazo de resultado, retire.'),
    dict(id='facil', g=ATENCAO, regra=_R_AUTOENGRANDECER,
         p=r'\b(rapido e facil|facil e rapido|sem burocracia|descomplicad[oa]|simples e rapido|sem dor de cabeca)\b',
         s='Expressão de venda; descreva o procedimento de forma neutra.'),
    dict(id='tem_direito', g=ATENCAO, regra=_R_PROMESSA,
         p=r'\b(voce|o senhor|a senhora|o produtor|todo produtor) tem (o )?direito\b|\bo banco e obrigado\b|\bo banco tem que\b',
         s='Afirmação absoluta: prefira "pode ter direito, se cumprir os requisitos" / "a norma prevê".'),
    dict(id='direito_absoluto', g=ATENCAO, regra=_R_PROMESSA,
         p=r'\be (um )?direito (seu|do produtor|previsto em lei|garantido|de todo produtor|certo)\b',
         exceto=r'(requisito|nos termos|se comprovar|desde que|depende)',
         s='Condicione no mesmo trecho: "direito previsto em lei, desde que cumpridos os requisitos".'),

    # ---------------- mercantilizacao ----------------
    dict(id='gratis', g=BLOQUEIA, regra=_R_MERCANTIL,
         p=r'\b(gratis|gratuit[oa]s?|de graca|sem custo|custo zero|free|sem nenhum custo|nao paga nada|sem pagar nada)\b',
         exceto=r'(justica|judiciaria|beneficio da|assistencia)\s*$',
         s='Gratuidade como chamariz é vedada. Retire; use "Converse com a equipe do escritório".'),
    dict(id='sem_compromisso', g=ATENCAO, regra=_R_MERCANTIL, p=r'\bsem compromisso\b',
         s='Linguagem de venda; retire.'),
    dict(id='desconto', g=BLOQUEIA, regra=_R_MERCANTIL,
         p=r'\b(desconto|descontos|promocao|promocoes|promocional|black friday|condicao especial|condicoes especiais'
           r'|preco especial|cupom|parcelamos|parcelamento facilitado|facilitamos o pagamento|sem entrada|entrada zero'
           r'|so paga (se|quando|no final)|so cobramos (se|quando|no final)|pague (so|somente|apenas) (se|quando|no final)'
           r'|honorarios (so|somente|apenas) no (final|exito))\b',
         exceto=r'(indevid|em conta|na conta|em folha|debito|na aposentadoria|no beneficio|do banco)',
         s='Condição comercial não entra na publicidade. Retire.'),
    dict(id='oferta', g=ATENCAO, regra=_R_MERCANTIL, p=r'\b(oferta|ofertas|imperdivel)\b',
         exceto=r'(credito|do banco|de renegociacao|de acordo)',
         s='Se for oferta do escritório, retire; se for oferta do banco, deixe claro.'),
    dict(id='honorarios', g=ATENCAO, regra=_R_MERCANTIL, p=r'\bhonorarios?\b',
         agrava=r'(r\$|\d|parcel|barat|acessive|valor|preco|gratis|desconto|entrada|so no final)',
         s='Não fale de valor, forma de pagamento ou condição de honorários na publicidade.'),
    dict(id='reais', g=ATENCAO, regra=_R_MERCANTIL, p=r'r\$ ?\d',
         agrava=r'(honorar|consulta|atendimento|nosso servico|pacote|nossos precos|mensalidade|investimento de)',
         s='Valor em reais só como exemplo educativo (nunca preço de serviço). Se for dado de mercado, cite a fonte.'),
    dict(id='preco_servico', g=BLOQUEIA, regra=_R_MERCANTIL,
         p=r'\b(preco|valor|custo) (da|de|do) (consulta|atendimento|analise|servico|honorario)'
           r'|\b(barato|baratinho|acessivel|acessiveis|preco justo|melhor preco|menor preco|cabe no (seu )?bolso)\b',
         s='Preço/valor de serviço não entra na publicidade. Retire.'),

    # ---------------- autoengrandecimento / comparacao ----------------
    dict(id='melhor', g=BLOQUEIA, regra=_R_AUTOENGRANDECER,
         p=r'\b(o|a|os|as|somos o|somos a|somos os) melhor(es)? (advogad\w*|escritorio\w*|equipe|banca|opcao|escolha'
           r'|especialista\w*|atendimento|servico|defesa|resultado)'
           r'|\bmelhor(es)? (advogad\w*|escritorio\w*)\b'
           r'|\bmelhor(es)? (do|da|de) (brasil|estado|rondonia|mato grosso|regiao|norte|cidade|agro|mercado|pais)\b',
         s='Autoelogio. Retire "o melhor"; mostre conhecimento explicando o tema.'),
    dict(id='lider', g=BLOQUEIA, regra=_R_AUTOENGRANDECER,
         p=r'(\bnumero 1\b|\bno\.? ?1\b|#1\b|\btop 1\b|\blider(es)? (em|no|na|de|do|da)\b|\breferencia (em|no|na|nacional|regional)\b'
           r'|\bmais (premiad|reconhecid|experient|procurad|confiav)\w*|\bo mais completo\b|\bincomparave\w*|\bimbativel\b'
           r'|\binigualave\w*|\brenomad\w*|\bconceituad\w*|\bpremiad\w*|\bos mais (qualificad|preparad)\w*)',
         s='Autoengrandecimento. Retire.'),
    dict(id='excelencia', g=ATENCAO, regra=_R_AUTOENGRANDECER, p=r'\b(excelencia|excelente atendimento|alta performance)\b',
         s='Evite adjetivos sobre o próprio escritório.'),
    dict(id='unico_escritorio', g=BLOQUEIA, regra=_R_AUTOENGRANDECER,
         p=r'\b(unico|unica|unicos|unicas) (escritorio|advogad\w*|equipe|especialista\w*|banca|que (resolve|consegue|garante|entende))',
         s='Afirmação de exclusividade. Retire.'),
    dict(id='unico', g=ATENCAO, regra=_R_AUTOENGRANDECER, p=r'\b(unic[oa]s?|exclusiv[oa]s?)\b',
         s='Confirme que "único/exclusivo" não se refere ao escritório.'),
    dict(id='especialista', g=ATENCAO, regra=_R_ESPECIALIDADE, p=r'\bespecialist\w*|\bespecializad\w*',
         s='Só use se houver título certificado [CONFERIR]; prefira "atuação em crédito rural / agronegócio".'),
    dict(id='comparacao', g=BLOQUEIA, regra=_R_COMPARACAO,
         p=r'\b(outros|demais) (advogad\w*|escritorio\w*|colegas)\b|\bconcorrent\w*|\bdiferente (dos|de) outros\b'
           r'|\bao contrario d[eo]s? outros\b|\bnao somos como\b|\bmelhor (do )?que (os|outros|qualquer)\b|\bmais barato que\b',
         s='Não compare com colegas. Fale só do tema e do direito.'),
    dict(id='exclamacoes', g=ATENCAO, regra=_R_AUTOENGRANDECER, p=r'!{2,}',
         s='Excesso de exclamação soa apelativo; use uma ou nenhuma.'),

    # ---------------- urgencia / captacao ----------------
    dict(id='urgencia', g=BLOQUEIA, regra=_R_URGENCIA,
         p=r'\b(ultimas vagas|vagas limitadas|so hoje|somente hoje|apenas hoje|ultima chance|ultima oportunidade|corra'
           r'|antes que seja tarde|o tempo esta acabando|tempo acabando|agende ja|chame ja|ligue ja|clique ja'
           r'|nao perca (essa|esta|a) (chance|oportunidade))\b',
         s='Pressão para contratar. Retire; informe prazos legais de forma neutra, se for o caso.'),
    dict(id='urgencia_leve', g=ATENCAO, regra=_R_URGENCIA,
         p=r'\b(urgente|urgentemente|agora mesmo|imediatamente|nao espere|nao perca|aproveite|so ate|somente ate)\b',
         s='Veja se é informação de prazo (ok, com a norma) ou apelo de venda (retirar).'),
    dict(id='cta_agora', g=ATENCAO, regra=_R_URGENCIA,
         p=r'\b(chame|chama|fale|mande|envie|clique|ligue|agende)\b[^.!?\n]{0,30}\b(agora|ja)\b',
         s='Chamada apelativa. Prefira "Ficou com dúvida? Converse com a equipe do escritório".'),
    dict(id='captacao_ativa', g=ATENCAO, regra=_R_CAPTACAO,
         p=r'\b(ligamos para voce|vamos ate (voce|sua)|visitamos (sua|voce)|mande (seu|o seu|sua) (contrato|cpf|documento|cedula)'
           r'|envie (seu|o seu|sua) (contrato|cpf|documento|cedula)|analisamos (seu|o seu|sua)|analise (do seu|da sua) (contrato|cedula|divida))\b',
         s='Oferecer análise do caso do seguidor pode soar como captação. Use convite discreto ao contato.'),
    dict(id='brinde', g=BLOQUEIA, regra=_R_BRINDE,
         p=r'\b(sorteio|sorteamos|brindes?|indique e ganhe|indicacao premiada|premio para quem|cashback|bonus)\b',
         s='Retire brinde/sorteio/prêmio.'),
    dict(id='consulta_publica', g=ATENCAO, regra=_R_CONSULTA,
         p=r'\b(tire (sua|suas) duvidas? (aqui|nos comentarios|no direct)|respondemos (todas|sua|suas)|responderemos'
           r'|pergunte (ao|para o) advogado|consultoria online)\b',
         s='Responda em termos gerais e convide para atendimento; não dê parecer em comentário.'),
    dict(id='litigio', g=ATENCAO, regra=_R_LITIGIO,
         p=r'\b(processe|processar o banco|process[ea] (o|seu|os) banco|entre na justica|va a justica|acione o banco|bote o banco na justica)\b',
         s='Informe o direito e os caminhos (pedido ao banco, negociação, ação quando cabível), sem incitar processo.'),

    # ---------------- sensacionalismo ----------------
    dict(id='medo', g=BLOQUEIA, regra=_R_SENSACIONALISMO,
         p=r'\b(vai perder tudo|perder tudo|o banco vai (tomar|levar)|tomar(ao)? (sua|a sua|tua) (fazenda|terra|propriedade|casa)'
           r'|desesper\w*|ruina|falencia certa|destruir (sua|a sua) vida|pesadelo|tragedia)\b',
         s='Medo exagerado. Descreva o risco com sobriedade ("a execução pode levar à penhora de bens").'),
    dict(id='medo_leve', g=ATENCAO, regra=_R_SENSACIONALISMO,
         p=r'\bperder (a|sua) (fazenda|terra|propriedade|casa)\b|\bnao durma\b|\bcuidado!',
         s='Tom alarmista; reescreva com sobriedade.'),
    dict(id='ofensa_banco', g=BLOQUEIA, regra=_R_SENSACIONALISMO,
         p=r'\b(ladra\w*|ladrao|ladroes|roub\w*|bandid\w*|safad\w*|agiot\w*|mafia|sanguessug\w*|vampir\w*|picaret\w*)\b',
         s='Linguagem ofensiva contra instituição. Retire; fale em "cobrança indevida" ou "exigência sem previsão na norma".'),
    dict(id='golpe', g=ATENCAO, regra=_R_SENSACIONALISMO, p=r'\bgolp\w*',
         s='Se for alerta contra golpes, ok; se acusa banco/pessoa, retire.'),

    # ---------------- casos concretos / dados ----------------
    dict(id='resultado_cliente', g=BLOQUEIA, regra=_R_CASO,
         p=r'\b(conseguimos|obtivemos|revertemos|recuperamos|economizamos|salvamos|livramos)\b'
           r'|\b(nosso|nossa|nossos|nossas|um|uma|o|a) client\w* (conseguiu|ganhou|obteve|teve|recebeu|livrou|garantiu|foi|saiu)\b'
           r'|\b(caso|casos) de sucesso\b|\bdepoimentos?\b|\bclientes? satisfeit\w*|\bresultados? (obtid|alcancad|conquistad)\w*',
         s='Resultado de cliente/caso concreto não entra na publicidade. Retire.'),
    dict(id='volume_clientes', g=BLOQUEIA, regra=_R_CASO,
         p=r'\b(mais de|centenas de|milhares de|dezenas de) (\d[\d\.]* )?(clientes|produtores|casos|processos|acoes|familias|contratos)\b'
           r'|\b\d[\d\.]* (clientes|produtores atendidos|casos|processos|acoes ganhas|liminares|sentencas)\b'
           r'|\b(milhoes|milhao|mil reais) (recuperad|economizad|renegociad|prorrogad|salv)\w*',
         s='Volume de clientes/casos/valores é autopromoção (e nunca pode ser inventado). Retire.'),
    dict(id='numero_processo', g=BLOQUEIA, regra=_R_SIGILO, p=r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b',
         s='Retire o número do processo.'),
    dict(id='cpf', g=BLOQUEIA, regra=_R_SIGILO, p=r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', s='Retire o CPF.'),
    dict(id='percentual', g=ATENCAO, regra=_R_DADO, p=r'\b(?!100\b)\d{1,3}([.,]\d+)? ?(%|por cento)',
         s='Cite a fonte oficial do número (Banco Central, CONAB, IBGE...) ou retire.'),
    dict(id='estatistica', g=ATENCAO, regra=_R_DADO,
         p=r'\b\d+ (em|de) cada \d+\b|\ba maioria dos produtores\b|\b(estudos|pesquisas|dados) (mostram|comprovam|revelam)\b',
         s='Estatística sem fonte: cite a fonte oficial ou retire.'),

    # ---------------- estrutura / ostentacao ----------------
    dict(id='estrutura', g=ATENCAO, regra=_R_ESTRUTURA,
         p=r'\b(estrutura (moderna|completa|de ponta|ampla)|escritorio (moderno|amplo|de luxo)|ostent\w*|carro de luxo|nossa sede)\b',
         s='Não destaque estrutura física nem bens. Foque no conteúdo informativo.'),
]

for _r in REGRAS:
    _r['_re'] = re.compile(_r['p'])
    _r['_exceto'] = re.compile(_r['exceto']) if _r.get('exceto') else None
    _r['_agrava'] = re.compile(_r['agrava']) if _r.get('agrava') else None

_JANELA = 45


def _normalizar(texto):
    """Minusculo e sem acento, mantendo 1 caractere por caractere (as posicoes batem com o original)."""
    saida = []
    for c in str(texto):
        d = unicodedata.normalize('NFKD', c)
        saida.append((d[0] if d else c).lower()[:1] or c)
    return ''.join(saida)


def verificar(texto, onde=''):
    """Lista de alertas do texto, na ordem em que aparecem."""
    texto = texto or ''
    norm = _normalizar(texto)
    alertas = []
    for r in REGRAS:
        for m in r['_re'].finditer(norm):
            ini, fim = m.start(), m.end()
            antes = norm[max(0, ini - _JANELA):ini]
            entorno = norm[max(0, ini - _JANELA):min(len(norm), fim + _JANELA)]
            if r['_exceto'] and (r['_exceto'].search(antes) or r['_exceto'].search(norm[fim:fim + _JANELA])):
                continue
            gravidade = r['g']
            if r['_agrava'] and r['_agrava'].search(entorno):
                gravidade = BLOQUEIA
            c_ini, c_fim = max(0, ini - 35), min(len(texto), fim + 35)
            contexto = ('...' if c_ini else '') + texto[c_ini:c_fim].replace('\n', ' ') + ('...' if c_fim < len(texto) else '')
            alertas.append({
                'trecho': texto[ini:fim], 'contexto': contexto, 'regra': r['regra'], 'gravidade': gravidade,
                'sugestao': r['s'], 'posicao': ini, 'onde': onde, 'id': r['id'],
            })
    # a mesma palavra pode cair em duas regras (ex.: "garantido" e "resultado garantido"): fica a mais grave
    alertas.sort(key=lambda a: (a['posicao'], 0 if a['gravidade'] == BLOQUEIA else 1))
    finais = []
    for a in alertas:
        repetido = False
        for b in finais:
            sobrepoe = a['posicao'] < b['posicao'] + len(b['trecho']) and b['posicao'] < a['posicao'] + len(a['trecho'])
            if sobrepoe and (b['gravidade'] == BLOQUEIA or a['gravidade'] == b['gravidade']):
                repetido = True
                break
        if not repetido:
            finais.append(a)
    return finais


def verificar_partes(partes):
    """partes: lista de (onde, texto) ou dict {onde: texto}. Junta os alertas indicando onde estao."""
    itens = partes.items() if isinstance(partes, dict) else partes
    alertas = []
    for onde, texto in itens:
        alertas.extend(verificar(texto, onde))
    return alertas


def bloqueia(alertas):
    return any(a['gravidade'] == BLOQUEIA for a in alertas)


def situacao(alertas):
    if bloqueia(alertas):
        return SITUACAO_BLOQUEADO
    if alertas:
        return SITUACAO_ATENCAO
    return SITUACAO_LIVRE


def contagem(alertas):
    b = sum(1 for a in alertas if a['gravidade'] == BLOQUEIA)
    return b, len(alertas) - b


def relatorio_texto(alertas, titulo='Conferência de conformidade (Provimento 205/2021)'):
    b, at = contagem(alertas)
    linhas = [titulo, '=' * len(titulo), f'SITUAÇÃO: {situacao(alertas)}',
              f'Alertas: {b} BLOQUEIA | {at} ATENÇÃO', '']
    for i, a in enumerate(alertas, 1):
        onde = f' [{a["onde"]}]' if a.get('onde') else ''
        linhas += [f'{i}. {a["gravidade"]}{onde}: "{a["trecho"]}"',
                   f'   Contexto: {a["contexto"]}',
                   f'   Regra: {a["regra"]}',
                   f'   Sugestão: {a["sugestao"]}', '']
    linhas += ['Lembrete: o verificador é por palavras e não substitui a leitura do advogado responsável.',
               'Sem alerta não quer dizer aprovado. Nada é publicado automaticamente.']
    return '\n'.join(linhas)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Confere um texto de publicidade contra o Provimento 205/2021 da OAB')
    ap.add_argument('arquivo', nargs='?')
    ap.add_argument('--texto')
    args = ap.parse_args(argv)
    if args.texto:
        texto = args.texto
    elif args.arquivo:
        with open(args.arquivo, encoding='utf-8-sig', errors='replace') as f:
            texto = f.read()
    else:
        ap.error('informe o arquivo ou --texto')
    alertas = verificar(texto)
    print(relatorio_texto(alertas))
    return 2 if bloqueia(alertas) else 0


if __name__ == '__main__':
    sys.exit(main())

"""
Checklist pre-protocolo da FASE JUDICIAL (o que o Adv. Judicial confere antes da inicial).

Le o caso.json e os arquivos da pasta do cliente e classifica cada item em:
    BLOQUEIA  sem isso a inicial nao sai (procuracao, cedulas, laudos, notificacao ao banco)
    ATENCAO   falta ou ponto fraco que os bancos atacam (DNA secao 7) - resolver ou justificar
    OK        conferido

Saidas em 20 JUDICIAL/: "Checklist Pre-Protocolo - data.docx" e "PEDIDO AO ESTAGIARIO - data.txt"
(texto pronto com o que falta e onde salvar). Nada e enviado a ninguem.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import date, datetime  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caso_judicial as cj  # noqa: E402
from CONTRATACAO import pasta_cliente  # noqa: E402
from config.equipe import CARGOS  # noqa: E402
from config.escritorio import CHECKLIST_DOCUMENTOS, PRAZOS  # noqa: E402
from docx_caldeira import docx_para_pdf, lista, novo_documento, paragrafo, secao, tabela, titulo  # noqa: E402

BLOQUEIA, ATENCAO, OK = 'BLOQUEIA', 'ATENÇÃO', 'OK'
DIAS_SEM_RESPOSTA = 10   # depois disso, silencio do banco = recusa tacita (DNA 2.3; escritorio ajuiza em 2-4 semanas)
DIAS_ALERTA_PRAZO = 10   # alerta quando faltar isso para o prazo interno da inicial
PASTA_ITEM = {d['id']: d.get('pasta') for d in CHECKLIST_DOCUMENTOS}
TIPOS_RISCO = (('ccb', 'CCB'), ('cedula de credito bancario', 'CCB'), ('cpr', 'CPR/CPRF'), ('cheque especial', 'cheque especial'),
               ('capital de giro', 'capital de giro'), ('credito pessoal', 'crédito pessoal'))


def _item(nivel, item, detalhe, responsavel='', pedir=None, pasta=None):
    return {'nivel': nivel, 'item': item, 'detalhe': detalhe, 'responsavel': responsavel,
            'pedir': pedir, 'pasta': pasta}


def _data(txt):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(txt or '').strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def _br(txt):
    d = _data(txt)
    return d.strftime('%d/%m/%Y') if d else (txt or '-')


def _destino(item_id):
    p = PASTA_ITEM.get(item_id)
    if not p:
        return None
    return p if p == cj.CONTRATACAO else f'{pasta_cliente.DOCS}/{p}'


# ============================================================
# VERIFICACOES
# ============================================================

def _documentos_basicos(base, caso, docs, itens):
    por_item = pasta_cliente.arquivos_por_item(base)
    q = caso.get('qualificacao') or {}

    # procuracao assinada (ZapSign baixa como "... - Procuracao (ASSINADO).pdf")
    assinada = por_item.get('procuracao') or any(
        'procura' in (l.get('documento') or '').lower() and l.get('status') == 'assinado'
        for l in caso.get('zapsign') or [])
    itens.append(_item(OK if assinada else BLOQUEIA, 'Procuração assinada',
                       'na pasta' if assinada else 'não encontrei a procuração ASSINADA em 00 CONTRATACAO',
                       'Estagiário', None if assinada else 'Procuração assinada pelo cliente (baixar do ZapSign)',
                       cj.CONTRATACAO))

    falta_q = [c for c in ('nome', 'cpf', 'estado_civil', 'profissao', 'logradouro', 'cidade', 'uf')
               if not q.get(c) or '[CONFERIR' in str(q.get(c))]
    itens.append(_item(BLOQUEIA if ('nome' in falta_q or 'cpf' in falta_q) else (ATENCAO if falta_q else OK),
                       'Qualificação do autor (caso.json)',
                       'completa' if not falta_q else 'faltando/conferir: ' + ', '.join(falta_q),
                       'Estagiário', 'Dados de qualificação do cliente: ' + ', '.join(falta_q) if falta_q else None))

    for item_id, nome, nivel_falta, obs in (
            ('pessoais', 'Documentos pessoais (RG/CNH/CPF)', ATENCAO, ''),
            ('endereco', 'Comprovante de endereço', ATENCAO, ''),
            ('extratos', 'Extratos bancários', ATENCAO, 'mostram saldo, débitos automáticos e evolução da dívida'),
            ('pagamentos', 'Comprovantes de pagamento das parcelas', ATENCAO, 'mostram boa-fé e histórico de adimplência'),
            ('matricula', 'Matrícula do imóvel rural', ATENCAO, 'prova da propriedade/área; hipoteca'),
            ('fiscal', 'Notas fiscais de venda da produção', ATENCAO,
             'provam a destinação rural e a queda de receita (bancos atacam a falta, DNA §7)')):
        achados = por_item.get(item_id)
        itens.append(_item(OK if achados else nivel_falta, nome,
                           ', '.join(achados[:3]) if achados else f'não está na pasta. {obs}'.strip(),
                           'Estagiário', None if achados else nome, _destino(item_id)))

    # gratuidade: a decisao de pedir e do Coordenador; o documento precisa estar pronto
    declaracao = [d for d in docs if 'declara' in d.nome.lower() and 'assinad' in d.nome.lower()] or \
        [l for l in caso.get('zapsign') or [] if 'declara' in (l.get('documento') or '').lower()
         and l.get('status') == 'assinado']
    decisao = [d for d in docs if d.pasta == cj.JUDICIAL and 'gratuidade' in d.nome.lower()]
    if decisao or declaracao:
        itens.append(_item(OK, 'Gratuidade da justiça',
                           'decisão de gratuidade na pasta' if decisao else 'declaração de hipossuficiência assinada',
                           'Coordenador Jurídico'))
    else:
        itens.append(_item(ATENCAO, 'Gratuidade da justiça',
                           'sem declaração de hipossuficiência assinada. O Coordenador decide se pede gratuidade '
                           '(subsidiário: custas ao final ou parcelamento em 08 parcelas)',
                           'Coordenador Jurídico', 'Declaração de hipossuficiência assinada (se o Coordenador '
                                                   'decidir pedir gratuidade)', cj.CONTRATACAO))
    ir = por_item.get('ir')
    itens.append(_item(OK if ir else ATENCAO, 'Imposto de Renda (3 últimos anos)',
                       ', '.join(ir[:3]) if ir else 'bancos impugnam a gratuidade com IR, IDARON e receita bruta '
                                                    '(DNA §4.6); tese: patrimônio imobilizado não é liquidez',
                       'Estagiário', None if ir else 'Declarações de Imposto de Renda dos 3 últimos anos',
                       _destino('ir')))
    ar = (caso.get('triagem') or {}).get('atividade_rural') or {}
    pecuaria = re.search(r'pecu|gado|bovin|boi|rebanho|leite', cj.norm(f"{ar.get('tipo')} {ar.get('culturas_rebanho')}"))
    if pecuaria:
        gta = por_item.get('pecuaria')
        itens.append(_item(OK if gta else ATENCAO, 'GTA e extrato do IDARON (pecuária)',
                           ', '.join(gta[:3]) if gta else 'bancos pedem ofício ao IDARON; provam rebanho e vendas',
                           'Estagiário', None if gta else 'GTAs e extrato de movimentação do IDARON (3 anos)',
                           _destino('pecuaria')))


def _cedulas(caso, docs, bancos_alvo, itens):
    if not cj.operacoes(caso):
        itens.append(_item(BLOQUEIA, 'Operações bancárias do caso',
                           'o caso.json não tem operações (triagem vazia). Levantar bancos, cédulas, valores e vencimentos',
                           'Gestor Jurídico'))
        return
    for banco in bancos_alvo:
        ops = cj.operacoes_do_banco(caso, banco)
        ced = cj.cedulas_do_banco(docs, banco)
        if not ced:
            itens.append(_item(BLOQUEIA, f'Cédulas — {banco}',
                               f'nenhuma cédula/contrato de {banco} na pasta ({len(ops)} operação(ões) relatada(s)). '
                               'Se o cliente não tem: notificação curta "PEDIDO DE CONTRATOS RURAIS" (DNA §5.1) '
                               'e pedido de exibição (arts. 396 a 400 CPC) na inicial',
                               'Estagiário', f'Cópia integral de TODAS as cédulas, aditivos e renegociações do {banco}',
                               _destino('contratos')))
        elif len(ced) < len(ops):
            itens.append(_item(ATENCAO, f'Cédulas — {banco}',
                               f'{len(ced)} arquivo(s) para {len(ops)} operação(ões): conferir se há cédula de cada '
                               'operação e todos os aditivos', 'Estagiário',
                               f'Cédulas/aditivos que faltam do {banco} (conferir com as operações do caso)',
                               _destino('contratos')))
        else:
            itens.append(_item(OK, f'Cédulas — {banco}', ', '.join(d.nome for d in ced[:4]), 'Estagiário'))

        # pontos de risco das operacoes (DNA 7.5)
        riscos = []
        for o in ops:
            txt = cj.norm(' '.join(str(o.get(k) or '') for k in ('instrumento', 'finalidade', 'observacao', 'situacao')))
            for chave, rotulo in TIPOS_RISCO:
                if f' {chave} ' in f' {txt} ' and rotulo not in riscos:
                    riscos.append(rotulo)
            if 'fno' in txt.split() and 'FNO' not in riscos:
                riscos.append('FNO')
            if re.search(r'ja (foi )?prorrogad|prorrogada anteriormente|foi prorrogad|renegociad|repactuad', txt) \
                    and 'já prorrogada' not in riscos:
                riscos.append('já prorrogada')
            if re.search(r'em execucao|execucao (judicial )?(ajuizada|em andamento|proposta)|executad', txt) \
                    and 'execução' not in riscos:
                riscos.append('execução')
        if riscos:
            dicas = {'CCB': 'provar destinação rural (notas, GTA, projeto) — tese da natureza materialmente rural',
                     'CPR/CPRF': '"não existe CPRF desvinculada da atividade rural" (DNA §2.4)',
                     'cheque especial': 'banco dirá que não é crédito rural; provar destinação',
                     'capital de giro': 'provar destinação rural', 'crédito pessoal': 'provar destinação rural',
                     'FNO': 'Basa invoca MCR 2.6.5 "b" II; tese Lei 9.138/95 art. 5º, II (DNA §7.3)',
                     'já prorrogada': 'MCR não limita o número de prorrogações; novo evento adverso (DNA §7.1)',
                     'execução': 'já há execução: embargos à execução + prejudicialidade externa (comando embargos)'}
            itens.append(_item(ATENCAO, f'Pontos de risco — {banco}',
                               '; '.join(f'{r}: {dicas.get(r, "")}' for r in riscos), 'Adv. Judicial'))
        aval = [o.get('garantias_avalistas') for o in ops if o.get('garantias_avalistas')]
        if aval:
            itens.append(_item(ATENCAO, f'Avalistas e garantias — {banco}',
                               '; '.join(dict.fromkeys(aval)) + '. A tutela pede extensão aos avalistas: '
                               'conferir nome completo e CPF de cada um', 'Estagiário',
                               f'Nome completo e CPF dos avalistas/fiadores das operações do {banco}'))


def _laudos(docs, itens):
    safra = [d for d in docs if cj.eh_laudo_safra(d)]
    fin = [d for d in docs if cj.eh_laudo_financeiro(d)]
    destino = f'{pasta_cliente.DOCS}/{PASTA_ITEM.get("frustracao")}'
    if not safra:
        itens.append(_item(BLOQUEIA, 'Laudo de frustração de safra (agronômico)',
                           'não encontrado na pasta', 'Gestor Jurídico', None, destino))
    else:
        nomes = ', '.join(d.nome for d in safra[:3])
        art = any(cj.tem_art(d) for d in safra)
        vist = any(cj.tem_vistoria(d) for d in safra)
        itens.append(_item(OK, 'Laudo de frustração de safra (agronômico)', nomes, 'Gestor Jurídico'))
        itens.append(_item(OK if art else ATENCAO, 'ART do laudo agronômico',
                           'ART encontrada' if art else 'não achei ART no laudo. Bancos atacam laudo sem ART e '
                                                        'sem visto no CREA-RO (DNA §4.4 e §7.3)',
                           'Gestor Jurídico', None if art else 'ART do laudo agronômico', destino))
        itens.append(_item(OK if vist else ATENCAO, 'Vistoria in loco no laudo',
                           'laudo menciona vistoria' if vist else 'laudo não menciona vistoria na propriedade. '
                                                                  'Bancos atacam laudo "de gabinete" (DNA §7.2)',
                           'Gestor Jurídico'))
    if not fin:
        itens.append(_item(BLOQUEIA, 'Laudo financeiro / capacidade de pagamento',
                           'não encontrado. Dele saem a carência e o nº de parcelas pedidos (Tabela 03)',
                           'Gestor Jurídico', None, destino))
    else:
        itens.append(_item(OK, 'Laudo financeiro / capacidade de pagamento',
                           ', '.join(d.nome for d in fin[:3]), 'Gestor Jurídico'))


def _extrajudicial(caso, docs, bancos_alvo, itens):
    registros = cj.extrajudicial(caso)
    arquivos = [d for d in docs if d.pasta == cj.EXTRAJUDICIAL]
    hoje = date.today()
    for banco in bancos_alvo:
        regs = [r for r in registros if cj.mesmo_banco(r.get('banco') or '', banco)]
        arqs = [d for d in arquivos if cj.banco_no_texto(banco, d.nome, curto=True)
                or cj.banco_no_texto(banco, d.texto[:3000])]
        # formato do modulo EXTRAJUDICIAL: tipo 'alongamento' (pedido de prorrogacao) ou 'contratos' (pedido de copias)
        enviada = next((r for r in reversed(regs) if r.get('enviada_em') and r.get('tipo') != 'contratos'), None)
        so_contratos = next((r for r in regs if r.get('enviada_em') and r.get('tipo') == 'contratos'), None)
        acordo = next((r for r in regs if (r.get('decisao') or {}).get('resultado') == 'acordo'), None)
        if acordo:
            itens.append(_item(ATENCAO, f'Acordo registrado — {banco}',
                               f"a fase extrajudicial registrou ACORDO em {_br(acordo['decisao'].get('data'))}. "
                               'Confirmar com o Coordenador se a ação ainda é cabível', 'Coordenador Jurídico'))
        if not enviada and so_contratos:
            itens.append(_item(ATENCAO, f'Notificação extrajudicial — {banco}',
                               f"só a notificação de PEDIDO DE CONTRATOS foi enviada ({_br(so_contratos['enviada_em'])}); "
                               'o pedido de alongamento ao banco ainda não. O pedido administrativo não é requisito '
                               '(DNA §2.3), mas o manual prevê a notificação antes da inicial', 'Adv. Extrajudicial'))
            continue
        if not enviada:
            if arqs:
                itens.append(_item(ATENCAO, f'Notificação extrajudicial — {banco}',
                                   'há arquivo em 10 EXTRAJUDICIAL (' + ', '.join(d.nome for d in arqs[:2]) +
                                   '), mas o envio não está registrado no caso (data e resposta)', 'Adv. Extrajudicial'))
            else:
                itens.append(_item(BLOQUEIA, f'Notificação extrajudicial — {banco}',
                                   'sem notificação enviada. O manual exige a notificação e a resposta/ausência '
                                   'do banco antes da inicial (DNA §2.3 e §4.5)', 'Adv. Extrajudicial'))
            continue
        d_env = _data(enviada.get('enviada_em'))
        dias = (hoje - d_env).days if d_env else None
        itens.append(_item(OK if arqs else ATENCAO, f'Notificação extrajudicial — {banco}',
                           f"enviada em {_br(enviada.get('enviada_em'))}" +
                           ('' if arqs else '. Juntar na pasta o comprovante do envio (e-mail/protocolo)'),
                           'Adv. Extrajudicial', None if arqs else f'Comprovante do envio da notificação ao {banco}',
                           cj.EXTRAJUDICIAL))
        resposta = next((r.get('resposta') for r in reversed(regs) if r.get('resposta')), None)
        if isinstance(resposta, dict):  # formato do modulo EXTRAJUDICIAL
            if resposta.get('tipo') == 'sem_resposta':
                resposta = None
            else:
                resposta = (f"recebida em {_br(resposta.get('data'))}: " + (resposta.get('trecho') or
                            f"ver {os.path.basename(resposta.get('arquivo') or '') or 'arquivo em 10 EXTRAJUDICIAL'}"))
        if resposta:
            negativa = re.search(r'negad|indefer|recus|nao atend|não atend|percentual|nao preench|não preench',
                                 str(resposta), re.I)
            itens.append(_item(ATENCAO if negativa else OK, f'Resposta do banco — {banco}',
                               f'{str(resposta)[:220].rstrip(". ")}' + ('. A inicial precisa rebater o fundamento da recusa'
                                                           if negativa else ''), 'Adv. Judicial'))
        elif dias is not None and dias >= DIAS_SEM_RESPOSTA:
            itens.append(_item(OK, f'Resposta do banco — {banco}',
                               f'sem resposta há {dias} dias: inércia = recusa tácita / pretensão resistida (DNA §2.3)',
                               'Adv. Judicial'))
        else:
            itens.append(_item(ATENCAO, f'Resposta do banco — {banco}',
                               f'aguardando resposta ({dias if dias is not None else "?"} dia(s) do envio). Padrão do '
                               'escritório: ratificar a notificação e ajuizar 2 a 4 semanas depois', 'Adv. Extrajudicial'))
        ops = cj.operacoes_do_banco(caso, banco)
        listadas = enviada.get('operacoes')
        if isinstance(listadas, list) and ops and len(listadas) >= len(ops):
            itens.append(_item(OK, f'Pedido administrativo por operação — {banco}',
                               f'{len(listadas)} operação(ões) na notificação', 'Adv. Extrajudicial'))
        else:
            itens.append(_item(ATENCAO, f'Pedido administrativo por operação — {banco}',
                               'conferir se a notificação listou CADA operação (nº da cédula). O BB exige pedido e '
                               'laudo por operação; a sentença de Cacoal afastou a exigência, mas evita discussão '
                               '(DNA §7.1)', 'Adv. Extrajudicial'))


def _prazo(caso, itens):
    limite = next((_data(p.get('data')) for p in caso.get('prazos') or [] if p.get('id') == 'inicial'), None)
    if not limite:
        itens.append(_item(ATENCAO, f"Prazo interno da inicial ({PRAZOS['inicial_dias_apos_contrato']} dias do contrato)",
                           'prazo não registrado no caso.json', 'Coordenador Jurídico'))
        return
    faltam = (limite - date.today()).days
    if faltam < 0:
        nivel, txt = ATENCAO, f'VENCIDO há {-faltam} dia(s) (limite {limite:%d/%m/%Y}). Prioridade máxima'
    elif faltam <= DIAS_ALERTA_PRAZO:
        nivel, txt = ATENCAO, f'faltam {faltam} dia(s) (limite {limite:%d/%m/%Y})'
    else:
        nivel, txt = OK, f'faltam {faltam} dias (limite {limite:%d/%m/%Y})'
    itens.append(_item(nivel, f"Prazo interno da inicial ({PRAZOS['inicial_dias_apos_contrato']} dias do contrato)",
                       txt, 'Coordenador Jurídico'))


# ============================================================
# SAIDAS
# ============================================================

def texto_pedido_estagiario(caso, itens, prazo_txt):
    estag = (CARGOS.get('ESTAGIARIO') or {}).get('nome') or 'Estagiário(a)'
    pedir = [i for i in itens if i['pedir'] and i['nivel'] != OK]
    if not pedir:
        return None
    linhas = [f'Olá, {estag}.', '',
              f'Para protocolar a petição inicial de {cj.nome_cliente(caso)} ({prazo_txt}), faltam os itens abaixo. '
              'Peça ao cliente (ou providencie) e salve cada um na pasta indicada:', '']
    for n, i in enumerate(pedir, 1):
        onde = f" -> salvar em: {i['pasta']}" if i.get('pasta') else ''
        linhas.append(f"{n}. {i['pedir']} [{i['nivel']}]{onde}")
    outros = [i for i in itens if i['nivel'] != OK and not i['pedir'] and i['responsavel'] not in ('Estagiário',)]
    if outros:
        linhas += ['', 'Para sua ciência (já com o responsável):']
        linhas += [f"- {i['item']}: {i['responsavel']}" for i in outros]
    linhas += ['', 'Quando tudo estiver na pasta, avise o Adv. Judicial para rodar o checklist de novo.',
               'Senha GOV.BR do cliente: nunca por mensagem escrita.']
    return '\n'.join(linhas) + '\n'


def gerar(pasta, banco=None):
    base, caso = cj.abrir(pasta)
    docs = cj.inventario(base)
    todos = cj.bancos(caso)
    alvo = [cj.escolher_banco(caso, banco)] if banco else [b for b in todos if not cj.eh_nao_bancario(b)]
    itens = []
    for b in todos:
        if cj.eh_nao_bancario(b) and not banco:
            itens.append(_item(ATENCAO, f'Credor não bancário — {b}',
                               'não é banco/cooperativa de crédito: fica fora da ação mandamental. Confirmar com o '
                               'Gestor se entra em outra estratégia', 'Gestor Jurídico'))
    _documentos_basicos(base, caso, docs, itens)
    _cedulas(caso, docs, alvo, itens)
    _laudos(docs, itens)
    _extrajudicial(caso, docs, alvo, itens)
    _prazo(caso, itens)
    if any(cj.eh_caixa(b) for b in alvo):
        itens.append(_item(ATENCAO, 'Foro', 'réu é a Caixa Econômica Federal: Justiça Federal (SSJ Ji-Paraná). '
                                            'Verificar ação anterior contra a CEF para conexão/prevenção (DNA §1.2)',
                           'Coordenador Jurídico'))

    ordem = {BLOQUEIA: 0, ATENCAO: 1, OK: 2}
    itens.sort(key=lambda i: ordem[i['nivel']])
    cont = {n: sum(1 for i in itens if i['nivel'] == n) for n in (BLOQUEIA, ATENCAO, OK)}
    prazo = next((p.get('data') for p in caso.get('prazos') or [] if p.get('id') == 'inicial'), None)
    prazo_txt = f'prazo interno até {prazo}' if prazo else 'prazo interno a confirmar'

    # terminal
    print(f'\n=== CHECKLIST PRE-PROTOCOLO: {cj.nome_cliente(caso)} ===')
    print(f"Bancos: {', '.join(alvo) or '-'} | {prazo_txt}")
    for nivel in (BLOQUEIA, ATENCAO, OK):
        grupo = [i for i in itens if i['nivel'] == nivel]
        if grupo:
            print(f'\n{nivel} ({len(grupo)})')
            for i in grupo:
                print(f"  - {i['item']}: {i['detalhe']}")

    # arquivos
    hoje = date.today().strftime('%d-%m-%Y')
    nome = cj.nome_arquivo(caso)
    saida = cj.pasta_judicial(base)
    rel = os.path.join(saida, f'{nome} - Checklist Pre-Protocolo - {hoje}.docx')
    doc = novo_documento()
    titulo(doc, 'Checklist pré-protocolo')
    paragrafo(doc, 'Fase judicial · documento interno do Adv. Judicial', tamanho=10).alignment = 1
    paragrafo(doc, cj.nome_cliente(caso) or '[CONFERIR]', rotulo='Cliente')
    paragrafo(doc, ', '.join(alvo) or '[CONFERIR]', rotulo='Banco(s)')
    paragrafo(doc, prazo_txt, rotulo='Prazo')
    paragrafo(doc, f"{cont[BLOQUEIA]} bloqueio(s), {cont[ATENCAO]} ponto(s) de atenção, {cont[OK]} ok",
              rotulo='Resumo')
    secao(doc, 'Itens')
    tabela(doc, ['Nível', 'Item', 'Situação', 'Responsável'],
           [[i['nivel'], i['item'], i['detalhe'], i['responsavel']] for i in itens], [2.2, 4.3, 7.2, 2.3], tamanho=8)
    if cont[BLOQUEIA]:
        secao(doc, 'Enquanto houver BLOQUEIA')
        lista(doc, ['A minuta da inicial pode ser gerada para adiantar a redação, mas não protocolar.',
                    'Itens de laudo são do Gestor Jurídico; notificação é do Adv. Extrajudicial.'])
    paragrafo(doc, 'Checklist gerado automaticamente a partir da pasta do cliente e do caso.json. '
                   'Conferência final do Adv. Judicial e do Coordenador Jurídico.', negrito=True, tamanho=9)
    doc.save(rel)
    docx_para_pdf(rel)

    pedido = texto_pedido_estagiario(caso, itens, prazo_txt)
    caminho_pedido = None
    if pedido:
        caminho_pedido = os.path.join(saida, f'PEDIDO AO ESTAGIARIO - {hoje}.txt')
        with open(caminho_pedido, 'w', encoding='utf-8') as f:
            f.write(pedido)

    def alt(c):
        c['judicial_checklist'] = {
            'gerado_em': datetime.now().isoformat(timespec='seconds'), 'bancos': alvo,
            'bloqueia': cont[BLOQUEIA], 'atencao': cont[ATENCAO], 'ok': cont[OK], 'arquivo': rel,
            'pedido_estagiario': caminho_pedido,
            'pendencias': [f"{i['nivel']}: {i['item']}" for i in itens if i['nivel'] != OK],
        }
        if not c.get('judicial'):  # nao volta a etapa de quem ja tem peca gerada
            c['etapa'] = 'JUDICIAL - CHECKLIST COM PENDENCIAS' if cont[BLOQUEIA] else 'JUDICIAL - PRONTO PARA A INICIAL'
    cj.registrar(base, alt)

    print(f'\nChecklist: {rel}')
    if caminho_pedido:
        print(f'Pedido ao Estagiário (texto pronto): {caminho_pedido}')
    return {'itens': itens, 'contagem': cont, 'arquivo': rel, 'pedido': caminho_pedido}

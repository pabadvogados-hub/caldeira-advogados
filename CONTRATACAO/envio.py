"""
Tudo que sai do escritorio na fase de contratacao. So roda com --enviar.

- assinatura(): contrato, procuracao e declaracao -> PDF -> ZapSign (TRAVADO se sobrar
  [PREENCHER]/[CONFERIR] em qualquer documento)
- whatsapp(): mensagem ao produtor pelo Atende Direito
- advbox(): cadastra cliente + processo (fase inicial configuravel)
- honorarios(): cobranca da entrada / parcelas no Asaas (so com valores numericos no cadastro)
- tarefas(): tarefas por cargo no ADVBOX (so com --criar-tarefas e IDs em config/equipe.py)
"""
import base64
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'INTEGRACOES'))
sys.path.insert(0, RAIZ)

from docx_caldeira import docx_para_pdf  # noqa: E402
from documentos import pendencias_no_arquivo  # noqa: E402
from pasta_cliente import CONTRATACAO, PASTA_AREA  # noqa: E402
from config.escritorio import TITULAR  # noqa: E402
from config.equipe import CARGOS, REMETENTE_TAREFAS, TAREFAS_CONTRATACAO  # noqa: E402


def _tem(var):
    v = os.getenv(var, '')
    return bool(v) and not v.startswith('SEU') and 'AQUI' not in v.upper()


def travas(documentos):
    """Lista o que impede o envio para assinatura."""
    problemas = []
    for d in documentos:
        pend = pendencias_no_arquivo(d['arquivo'])
        if pend:
            problemas.append(f"{d['documento']}: {', '.join(pend[:6])}")
    return problemas


def assinatura(caso, documentos):
    if not _tem('ZAPSIGN_API_TOKEN'):
        print('   ZapSign: sem ZAPSIGN_API_TOKEN no .env, pulando.')
        return []
    problemas = travas(documentos)
    if problemas:
        print('   ZapSign TRAVADO. Corrija nos documentos (.docx) e rode "enviar" de novo:')
        for p in problemas:
            print(f'     - {p}')
        return []

    from zapsign_integration import criar_documento, criar_signatario
    q = caso['qualificacao']
    nome = q['nome'].upper()
    links = []
    for d in documentos:
        pdf = docx_para_pdf(d['arquivo'])
        if not pdf:
            print(f"   ERRO: nao consegui gerar o PDF de {d['documento']} (instalar Word ou LibreOffice).")
            continue
        with open(pdf, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        signers = [criar_signatario(nome, q.get('email') or None, q.get('telefone') or None)]
        if 'Contrato' in d['documento']:
            signers.append(criar_signatario(TITULAR['nome'].upper(), TITULAR.get('email') or None,
                                            send_whatsapp=False))
        try:
            out = criar_documento(f"{nome} - {d['documento']}", b64, signers,
                                  folder_path=f'/{PASTA_AREA}/{nome}/', external_id=caso.get('id', ''))
        except Exception as e:
            print(f"   ERRO ZapSign em {d['documento']}: {e}")
            continue
        link_cliente = next((s['link'] for s in out['sign_urls'] if (s['signatario'] or '').upper() == nome), None)
        links.append({'documento': d['documento'], 'token': out['token'], 'link': link_cliente,
                      'status': 'pendente'})
        print(f"   ZapSign: {d['documento']} enviado")
    return links


def whatsapp(telefone, texto):
    if not _tem('ATENDE_DIREITO_TOKEN'):
        print('   WhatsApp: sem ATENDE_DIREITO_TOKEN no .env, nada enviado.')
        return False
    from atendedireito_integration import enviar_texto_por_telefone
    ok, _ = enviar_texto_por_telefone(telefone, texto)
    print('   WhatsApp: mensagem enviada' if ok else '   WhatsApp: NAO enviada (contato nao achado no Atende Direito?)')
    return ok


def advbox(caso, base):
    if not _tem('ADVBOX_API_TOKEN'):
        print('   ADVBOX: sem ADVBOX_API_TOKEN no .env, pulando.')
        return {}
    from advbox_integration import cadastrar_cliente, cadastrar_processo
    q = caso['qualificacao']
    dados = {k: q.get(k, '') for k in ('nome', 'cpf', 'rg', 'email', 'telefone', 'data_nascimento', 'profissao',
                                       'bairro', 'cidade', 'uf', 'cep', 'estado_civil')}
    dados['estado'] = q.get('uf', '')
    dados['rua'] = ', '.join(x for x in (q.get('logradouro'), q.get('numero')) if x)
    cli = cadastrar_cliente(dados)
    if not cli or not cli.get('customers_id'):
        return {}
    t = caso['triagem']
    notas = (f"Fase de contratacao. Pasta: {base}\nBancos: {caso['campos'].get('BANCOS', '')}\n"
             f"Resumo: {(t.get('resumo_caso') or '')[:1500]}")
    proc = cadastrar_processo(cli['customers_id'], {'notas': notas, 'pasta': q.get('nome', '')[:30]})
    return {'cliente_id': cli.get('customers_id'), 'processo_id': (proc or {}).get('lawsuits_id')}


def _valor(txt):
    if txt in (None, ''):
        return None
    s = str(txt).replace('R$', '').replace(' ', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def _iso(data_br):
    try:
        return datetime.strptime(data_br, '%d/%m/%Y').strftime('%Y-%m-%d')
    except (TypeError, ValueError):
        return None


def honorarios(caso):
    """Cria as cobrancas no Asaas a partir dos campos numericos do CADASTRO (nunca do texto da reuniao)."""
    c = caso.get('cadastro', {})
    entrada, venc_entrada = _valor(c.get('honorarios_entrada_valor')), _iso(c.get('honorarios_entrada_vencimento'))
    qtd, parcela = c.get('honorarios_parcelas_qtd'), _valor(c.get('honorarios_parcela_valor'))
    venc_parc = _iso(c.get('honorarios_parcelas_primeiro_vencimento'))
    if not (entrada and venc_entrada) and not (qtd and parcela and venc_parc):
        print('   Asaas: cadastro sem valores numericos de honorarios, nada cobrado (ver RESUMO PARA O FINANCEIRO).')
        return []
    if not _tem('ASAAS_API_TOKEN'):
        print('   Asaas: sem ASAAS_API_TOKEN no .env, pulando.')
        return []
    from asaas_integration import buscar_ou_criar_cliente, criar_cobranca
    q = caso['qualificacao']
    cid = buscar_ou_criar_cliente(q['nome'], q.get('cpf'), q.get('email'), q.get('telefone'))
    links = []
    if entrada and venc_entrada:
        p = criar_cobranca(cid, entrada, venc_entrada, 'Honorarios advocaticios - entrada')
        links.append({'descricao': 'Entrada', 'link': p.get('invoiceUrl'), 'id': p.get('id')})
    if qtd and parcela and venc_parc:
        p = criar_cobranca(cid, parcela, venc_parc, 'Honorarios advocaticios - parcelas', parcelas=int(qtd))
        links.append({'descricao': f'{qtd} parcelas', 'link': p.get('invoiceUrl'), 'id': p.get('id')})
    for l in links:
        print(f"   Asaas: {l['descricao']} -> {l['link']}")
    return links


def tarefas(caso, base):
    if not _tem('ADVBOX_API_TOKEN'):
        print('   Tarefas: sem ADVBOX_API_TOKEN, pulando.')
        return []
    processo = (caso.get('advbox') or {}).get('processo_id')
    if not processo:
        print('   Tarefas: o processo ainda nao esta no ADVBOX, pulando.')
        return []
    from advbox_integration import buscar_tipo_tarefa, criar_publicacao
    remetente = CARGOS.get(REMETENTE_TAREFAS, {}).get('advbox_id')
    prazos = {p['id']: p['data'] for p in caso['prazos']}
    faltando = ', '.join(s['nome'] for s in caso['documentos_status']
                         if s['obrigatorio'] and s['situacao'] not in ('NA PASTA', 'JA ENTREGOU'))
    criadas = []
    for t in TAREFAS_CONTRATACAO:
        pessoa = CARGOS.get(t['cargo'], {}).get('advbox_id')
        tipo = buscar_tipo_tarefa(t['tipo'])
        if not (pessoa and remetente and tipo):
            print(f"   Tarefa '{t['marco']}' pulada: falta ID do cargo {t['cargo']}, do remetente ou do tipo '{t['tipo']}'.")
            continue
        prazo = _iso(prazos.get(t['marco']))
        texto = t['texto'].format(faltando=faltando or 'nada', pasta=base, bancos=caso['campos'].get('BANCOS', ''))
        r = criar_publicacao(processo, tipo, [str(pessoa)], texto, from_id=str(remetente), date_deadline=prazo)
        criadas.append({'marco': t['marco'], 'ok': bool(r)})
    return criadas

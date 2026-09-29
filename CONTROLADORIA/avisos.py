"""
AVISOS AO PRODUTOR sobre decisoes relevantes (fase 5).

Le a ultima varredura (SAIDA/controladoria/varreduras/*.json) e, para liminar concedida,
audiencia, pericia, sentenca e transito em julgado, escreve a mensagem em linguagem
do dia a dia. Texto de modelo fixo (nada inventado): o que a publicacao nao diz com
seguranca fica como [PREENCHER ...] e trava o envio ate o advogado completar.

Sai: SAIDA/controladoria/avisos/AAAA-MM-DD_HHMM/ (um .txt por aviso) + INDICE_PARA_REVISAO.csv.
Envio: `avisos-cliente --enviar` (so linhas com enviar=SIM e revisado_por, via Atende Direito).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NUCLEO'))
import ambiente  # noqa: E402,F401  (carrega .env e caminhos)
from datetime import datetime  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classificador  # noqa: E402
import comum  # noqa: E402
import envio_cliente  # noqa: E402
import saidas_varredura  # noqa: E402
from configuracao import ACOES  # noqa: E402
from config.escritorio import ESCRITORIO  # noqa: E402

ASSINATURA = ESCRITORIO['nome']


def _efeitos_liminar(frase):
    """O que a liminar garantiu, so pelo que esta escrito na decisao."""
    t = classificador.norm(frase)
    efeitos = []
    if 'exigibilidade' in t or 'suspend' in t and ('cobranc' in t or 'parcela' in t or 'divida' in t):
        efeitos.append('a cobrança das parcelas fica suspensa enquanto o processo corre')
    if re.search(r'negativ|serasa|spc|cadastro|registrato|scr', t):
        efeitos.append('o banco não pode colocar (ou manter) o seu nome no SERASA/SPC por causa dessa dívida')
    if re.search(r'execu|protesto|penhora|busca e apreensao|constric', t):
        efeitos.append('o banco não pode protestar, executar ou tomar bens por causa dessa dívida')
    if 'avalista' in t:
        efeitos.append('a proteção vale também para os avalistas')
    return efeitos


nome_proprio = comum.nome_proprio


def _banco(item):
    b = (item.get('parte_contraria') or '').strip()
    return nome_proprio(b) if b else 'o banco'


def mensagem(item):
    """(assunto, texto). Nunca promete resultado; o que nao se sabe vira [PREENCHER]."""
    nome = envio_cliente.primeiro_nome(item.get('cliente'))
    cat = item['categoria']
    abre = f'Olá, {nome}! Aqui é do {ASSINATURA}.'
    fecha = 'Qualquer dúvida, é só responder esta mensagem.\n\n' + ASSINATURA
    quando = f"{item.get('evento_data') or '[PREENCHER data]'}" + (f", às {item['evento_hora']}" if item.get('evento_hora') else ', [PREENCHER horário]')
    if cat == 'LIMINAR_DEFERIDA':
        efeitos = _efeitos_liminar(item.get('frase_chave') or '')
        lista = '\n'.join(f'- {e}' for e in efeitos) if efeitos else \
            '- [PREENCHER: o que a liminar garantiu, em palavras simples]'
        return ('Liminar concedida', f"{abre}\n\nBoa notícia no seu processo contra {_banco(item)}: o juiz aceitou o "
                f"nosso pedido de urgência (a liminar). Na prática:\n{lista}\n\nIsso ainda não é a decisão final. "
                "Agora a gente acompanha se o banco está cumprindo. Se o banco ligar, cobrar ou mandar mensagem, "
                f"não negocie direto: fale com a gente antes.\n\n{fecha}")
    if cat == 'AUDIENCIA':
        onde = 'por videoconferência (o link a gente manda antes)' if item.get('evento_virtual') else \
            (item.get('orgao') or '[PREENCHER local]')
        return ('Audiência marcada', f"{abre}\n\nO juiz marcou uma audiência no seu processo contra {_banco(item)}.\n\n"
                f"Dia: {quando}\nOnde: {onde}\n\nSua presença é importante. Antes da data a gente liga para "
                f"explicar como vai ser e o que levar.\n\n{fecha}")
    if cat == 'PERICIA':
        return ('Perícia', f"{abre}\n\nNo seu processo contra {_banco(item)}, o juiz mandou fazer a perícia (a análise "
                f"de um técnico sobre a sua situação). Data: {quando if item.get('evento_data') else '[PREENCHER: data e local da perícia, se já houver]'}.\n\n"
                "Vamos separar com você antes o que precisa estar pronto (notas fiscais, GTA, extrato do IDARON, fotos "
                f"da propriedade). A gente entra em contato para combinar.\n\n{fecha}")
    if cat == 'SENTENCA_FAVORAVEL':
        return ('Sentença favorável', f"{abre}\n\nBoa notícia: saiu a sentença do seu processo contra {_banco(item)} e o "
                "juiz deu razão para você.\n[PREENCHER: o que o juiz garantiu (carência, parcelas), em palavras simples]"
                "\n\nO banco ainda pode recorrer. A gente acompanha e te avisa de cada passo.\n\n" + fecha)
    if cat == 'SENTENCA_DESFAVORAVEL':
        return ('Sentença desfavorável (ligar antes)', f"{abre}\n\n{nome}, saiu a decisão do juiz no seu processo contra "
                f"{_banco(item)} e ela não foi a que esperávamos. Isso não é o fim: ainda cabe recurso. "
                "[PREENCHER: quem vai ligar e quando] vai te ligar para explicar e decidir os próximos passos com você."
                f"\n\n{ASSINATURA}")
    if cat == 'SENTENCA':
        return ('Sentença (conferir resultado)', f"{abre}\n\nSaiu a sentença do seu processo contra {_banco(item)}.\n"
                "[PREENCHER: resultado da sentença em palavras simples e o próximo passo]\n\n" + fecha)
    if cat == 'TRANSITO_JULGADO':
        return ('Processo encerrado na Justiça', f"{abre}\n\nO seu processo contra {_banco(item)} chegou ao fim na "
                "Justiça: não cabe mais recurso.\n[PREENCHER: o que isso significa para você e o que falta fazer]\n\n"
                + fecha)
    return (item.get('rotulo') or 'Andamento', f"{abre}\n\n[PREENCHER]\n\n{fecha}")


def _registro():
    return os.path.join(comum.pasta_saida('controladoria'), '_avisos_gerados.json')


def _telefone(item, exemplo):
    if exemplo:
        for p in comum.ex.processos():
            if str(p['id']) == str(item.get('advbox_processo_id')):
                return p['customers'][0].get('cellphone', '')
        return ''
    if item.get('pasta'):
        import caminhos
        from pasta_cliente import ler_caso, raiz_clientes
        # a varredura pode ter sido gravada em outra maquina (Z:\... x /Volumes/...)
        tel = (ler_caso(caminhos.pasta_do_cliente(item['pasta'], raiz_clientes())).get('qualificacao')
               or {}).get('telefone')
        if tel:
            return tel
    if item.get('advbox_processo_id') and comum.tem_advbox():
        try:
            import advbox_integration as advbox
            procs = advbox.buscar_processo(numero_processo=item['processo']) or []
            clientes = (procs[0].get('customers') or []) if procs else []
            cid = clientes[0].get('customer_id') or clientes[0].get('id') if clientes else None
            if cid:
                c = advbox.obter_cliente(cid) or {}
                c = c.get('data', c) if isinstance(c, dict) else {}
                return c.get('cellphone') or c.get('phone') or ''
        except Exception:
            return ''
    return ''


def gerar(exemplo=False):
    print('\n=== AVISOS AO CLIENTE ===')
    caminho, itens = saidas_varredura.ultima_varredura(exemplo)
    if not itens and exemplo:
        print('   Sem varredura de exemplo salva: rodando a varredura --exemplo primeiro...')
        import varredura
        varredura.executar(exemplo=True)
        caminho, itens = saidas_varredura.ultima_varredura(exemplo)
    if not itens:
        print('   Nenhuma varredura salva. Rode antes: python CONTROLADORIA/main.py varredura --dias 7')
        return None
    print(f'   Base: {os.path.basename(caminho)}')
    try:
        with open(_registro(), encoding='utf-8') as f:
            ja = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ja = {}
    relevantes = [i for i in itens if ACOES[i['categoria']]['aviso_cliente'] and i.get('prazo_nosso') != 'NÃO'
                  and (exemplo or str(i['id_djen']) not in ja)]
    if not relevantes:
        print('   Nenhuma decisão nova que peça aviso ao cliente.')
        return None

    pasta = comum.pasta_saida('controladoria', 'avisos',
                              datetime.now().strftime('%Y-%m-%d_%H%M') + ('_EXEMPLO' if exemplo else ''))
    indice = []
    for n, i in enumerate(relevantes, 1):
        assunto, texto = mensagem(i)
        arq = os.path.join(pasta, f"{n:02d} - {envio_cliente.primeiro_nome(i['cliente'])} - {assunto}.txt".replace('/', '-'))
        with open(arq, 'w', encoding='utf-8') as f:
            f.write(texto)
        tel = _telefone(i, exemplo) or '[PREENCHER telefone]'
        pend = 'SIM' if envio_cliente.PENDENCIA.search(texto + ' ' + tel) else 'nao'
        indice.append({'cliente': i['cliente'], 'telefone': tel, 'processo': i['processo'], 'assunto': assunto,
                       'texto': arq, 'precisa_preencher': pend, 'origem': 'modelo fixo', 'revisado_por': '',
                       'enviar': '', 'enviado_em': '', 'chave': i['id_djen']})
        ja[str(i['id_djen'])] = datetime.now().isoformat(timespec='seconds')
        print(f"   {assunto:38} {i['cliente'][:40]}" + ('  [PREENCHER]' if pend == 'SIM' else ''))
    csv_ = comum.salvar_csv(os.path.join(pasta, 'INDICE_PARA_REVISAO.csv'), indice, envio_cliente.CAMPOS)
    if not exemplo:
        with open(_registro(), 'w', encoding='utf-8') as f:
            json.dump(ja, f, ensure_ascii=False, indent=1)
    print(f'\n   {len(indice)} aviso(s) em {pasta}')
    print(f'   Revisão: {csv_}')
    print('   PRÓXIMO PASSO (humano): ler cada .txt, completar o [PREENCHER], pôr o nome em "revisado_por" e SIM em '
          '"enviar". Depois: python CONTROLADORIA/main.py avisos-cliente --enviar')
    return csv_


def enviar(so=None):
    return envio_cliente.enviar_indice(envio_cliente.ultimo_indice('avisos'), so)

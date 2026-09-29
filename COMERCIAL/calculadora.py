"""
CALCULADORA DE JUROS DO CREDITO RURAL (pagina de captacao, Provimento 205/2021).

A pagina e COMERCIAL/calculadora/index.html: um arquivo so, sem internet, que pode ser
publicado no site, aberto no celular ou mandado como link. Este comando reescreve o bloco
de configuracao do topo do arquivo (numero do WhatsApp, mensagem, dados do escritorio).

O que a pagina faz: parcela (Price/SAC), total pago, total de juros, taxa efetiva anual,
custo efetivo com tarifas/seguros/IOF, carencia com juros pagos ou somados, tabela resumida,
comparacao com outra taxa, texto informativo sobre prorrogacao e aviso de que nao e consultoria.
O que ela NAO faz (Provimento 205): nao promete resultado, nao mostra preco de honorario,
nao coleta dado nenhum (so abre o WhatsApp se a pessoa clicar).
"""
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from config.escritorio import ESCRITORIO, TITULAR  # noqa: E402

from config_comercial import MENSAGEM_WHATSAPP_CALCULADORA, WHATSAPP_CALCULADORA  # noqa: E402

PAGINA = os.path.join(AQUI, 'calculadora', 'index.html')
BLOCO = re.compile(r'<!-- CONFIG-INICIO -->.*?<!-- CONFIG-FIM -->', re.S)


def _numero_whatsapp(numero=None):
    d = re.sub(r'\D', '', numero or WHATSAPP_CALCULADORA or ESCRITORIO.get('central') or ESCRITORIO['telefone'])
    if len(d) in (10, 11):
        d = '55' + d
    if len(d) not in (12, 13):
        raise SystemExit(f'Numero de WhatsApp invalido: {numero!r} (use DDI+DDD+numero, ex.: 5569999999999)')
    return d


def gerar(whatsapp=None):
    if not os.path.exists(PAGINA):
        raise SystemExit(f'ERRO: {PAGINA} nao encontrado')
    e = ESCRITORIO
    config = {
        'whatsapp': _numero_whatsapp(whatsapp),
        'mensagem': MENSAGEM_WHATSAPP_CALCULADORA,
        'escritorio': e['nome'],
        'responsavel': f"Dr. {TITULAR['nome']} - {TITULAR['oab']}",
        'endereco': e['endereco'].split(', CEP')[0],
        'site': e['site'],
        'instagram': e['instagram'],
    }
    corpo = ',\n'.join(f'  {k}: {json.dumps(v, ensure_ascii=False)}' for k, v in config.items())
    bloco = ('<!-- CONFIG-INICIO -->\n<script>\nwindow.CONFIG_CALCULADORA = {\n' + corpo +
             '\n};\n</script>\n<!-- CONFIG-FIM -->')
    with open(PAGINA, encoding='utf-8') as f:
        html = f.read()
    if not BLOCO.search(html):
        raise SystemExit('ERRO: bloco CONFIG-INICIO/CONFIG-FIM nao encontrado na pagina')
    html = BLOCO.sub(lambda _: bloco, html, count=1)
    with open(PAGINA, 'w', encoding='utf-8') as f:
        f.write(html)
    print('Calculadora atualizada:')
    print(f'  {PAGINA}')
    print(f"  WhatsApp do botao: +{config['whatsapp']}")
    print('  Abra o arquivo no navegador para testar. Para publicar: subir o index.html no site '
          '(ou em qualquer hospedagem estatica) e divulgar o link nos anuncios e no Instagram.')
    return PAGINA

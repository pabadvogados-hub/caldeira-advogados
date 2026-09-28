"""
Chamadas a IA (Claude) usadas por todos os modulos.

- json_por_schema(): resposta em JSON garantido por schema (triagem, extracao, classificacao)
- texto_longo(): texto corrido longo (pecas, notificacoes, relatorios), em streaming

Modelos no config/.env: MODELO_TRIAGEM, MODELO_EXTRACAO, MODELO_PECAS.
O texto fixo do sistema (instrucoes + DNA das pecas) vai em cache entre uma chamada e outra.
"""
import json
import os

import anthropic

MODELO_PECAS = os.getenv('MODELO_PECAS', 'claude-opus-5')


def _cliente():
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise SystemExit('ERRO: ANTHROPIC_API_KEY nao configurada em config/.env')
    return anthropic.Anthropic(api_key=api_key)


def _extras(modelo):
    # se o filtro de seguranca recusar, a propria API refaz no modelo de reserva
    if modelo.startswith('claude-opus-5') or modelo.startswith('claude-fable'):
        return {'extra_headers': {'anthropic-beta': 'server-side-fallback-2026-07-01'},
                'extra_body': {'fallbacks': 'default'}}
    return {}


def _conferir(resposta):
    if resposta.stop_reason == 'refusal':
        raise RuntimeError('A IA recusou a tarefa (stop_reason=refusal). Rodar de novo ou revisar a entrada.')
    if resposta.stop_reason == 'max_tokens':
        raise RuntimeError('A resposta da IA foi cortada (max_tokens). Aumentar o limite e rodar de novo.')


def json_por_schema(modelo, sistema, conteudo, schema, max_tokens=16000):
    with _cliente().messages.stream(
        model=modelo,
        max_tokens=max_tokens,
        system=[{'type': 'text', 'text': sistema, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': conteudo}],
        output_config={'format': {'type': 'json_schema', 'schema': schema}},
        **_extras(modelo),
    ) as stream:
        resposta = stream.get_final_message()
    _conferir(resposta)
    return json.loads(next(b.text for b in resposta.content if b.type == 'text'))


def texto_longo(sistema, conteudo, modelo=None, max_tokens=64000, esforco='high'):
    modelo = modelo or MODELO_PECAS
    with _cliente().messages.stream(
        model=modelo,
        max_tokens=max_tokens,
        system=[{'type': 'text', 'text': sistema, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': conteudo}],
        output_config={'effort': esforco},
        **_extras(modelo),
    ) as stream:
        resposta = stream.get_final_message()
    _conferir(resposta)
    return ''.join(b.text for b in resposta.content if b.type == 'text').strip()

---
name: fase-contratacao
description: Conduz a fase de contratacao de um produtor rural recem-fechado pelo Closer do Caldeira Advogados - le a transcricao da reuniao, gera Relatorio de Triagem, contrato, procuracao e declaracao, envia para assinatura e acompanha a cobranca de documentos. Use quando pedirem "contratacao", "cliente novo", "fechou", "gerar contrato/procuracao", "relatorio de triagem" ou "cobrar documentos".
---

# Fase de contratacao

1. Peca ao usuario: transcricao da reuniao de fechamento, documento pessoal (CNH/RG) e o CADASTRO.txt do Closer
   (modelo em `exemplos/CADASTRO_MODELO.txt`). Se faltar o cadastro, monte um com o que o usuario disser.
2. Rode `python CONTRATACAO/main.py novo "<transcricao>" "<documentos...>" --cadastro "<cadastro>"`.
3. Mostre ao usuario: gatilhos ALTA do relatorio, prazos do caso e as pendencias que travam o envio.
4. Pendencias `[PREENCHER ...]`/`[CONFERIR ...]`: pergunte o dado que falta e corrija no .docx em `00 CONTRATACAO/`
   (ou no cadastro e rode `novo` de novo). Nunca invente o dado. Nunca remova a marca de modelo provisorio
   sem o escritorio ter mandado o modelo oficial.
5. So com autorizacao explicita do usuario: `python CONTRATACAO/main.py enviar "<pasta>"` (e `--criar-tarefas` se ele pedir).
6. Depois: `python CONTRATACAO/main.py painel` para acompanhar; `acompanhar --enviar` roda sozinho 3x ao dia.

Regras: a IA nao decide a estrategia fora dos casos simples e padronizados; nao envia nada ao banco;
senha GOV.BR nunca por mensagem; nada sai sem `--enviar`.

---
name: peca-caldeira
description: Gera ou revisa peca judicial do Caldeira Advogados no padrao do escritorio (timbrado, DNA das pecas) - checklist pre-protocolo, inicial da Acao Mandamental de Prorrogacao Compulsoria de Divida Rural, agravo de instrumento, replica, embargos a execucao, contrarrazoes e peticao de andamento. Use quando pedirem "inicial", "acao mandamental", "prorrogacao", "alongamento", "liminar negada", "agravo", "replica", "contestacao do banco", "embargos", "execucao do banco", "contrarrazoes", "apelacao do banco", "peticao", "manifestacao" ou "checklist do protocolo".
---

# Peca judicial (Fase 4 - Judicial)

1. Descubra a pasta do cliente (`AGRONEGOCIO/NOME/`, com `00 CONTRATACAO/caso.json`) e o banco reu.
   Um caso com mais de um banco gera uma acao por banco (`--banco`).
2. Sempre rode primeiro: `python JUDICIAL/main.py checklist "<pasta>"` e mostre ao usuario os itens BLOQUEIA e
   ATENCAO. O que falta de documento ja sai como texto pronto em `20 JUDICIAL/PEDIDO AO ESTAGIARIO - data.txt`.
   Laudos sao do Gestor Juridico; notificacao e do Adv. Extrajudicial.
3. Gere a peca pedida:
   - `inicial "<pasta>" --banco "<banco>" [--revisional] [--federal]`
   - `agravo "<pasta>" --decisao <decisao.pdf>` | `replica "<pasta>" --contestacao <contestacao.pdf>`
   - `embargos "<pasta>" --execucao <execucao.pdf>` | `contrarrazoes "<pasta>" --recurso <apelacao.pdf>`
   - `manifestacao "<pasta>" --instrucao "<o que dizer>" [--documento <intimacao.pdf>]`
   - Orientacao extra do advogado: `--instrucao "..."`. Ver o prompt sem gastar IA: `--simular`.
4. Mostre ao usuario: caminho do .docx/.pdf em `20 JUDICIAL/`, numero de pendencias em vermelho e as citacoes que a
   conferencia com o DNA marcou. Leia o .md em `20 JUDICIAL/_texto_ia/` e aponte o que precisa de decisao humana.
5. Ajustes: edite o .md e rode `python JUDICIAL/main.py docx "<arquivo.md>"`. Nao gere de novo so para corrigir texto.
6. Revisao profunda: use o subagente `caldeira-pecas-agro`.

Regras: nunca remover `[CONFERIR]`/`[PREENCHER]` sem o dado ou a fonte oficial; jurisprudencia so do DNA; a IA nao
protocola nem envia nada; comarca, gratuidade, agravo sim/nao e acordo sao do Coordenador Juridico; toda peca sai com
"PRONTA PARA REVISAO DO(A) ADVOGADO(A) RESPONSAVEL".

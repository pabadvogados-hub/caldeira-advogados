# Caldeira Advogados Associados - Central de Automacoes

> Escritorio: **Caldeira Advogados Associados** (CNPJ 51.038.631/0001-30), Cacoal/RO.
> Titular: **Dr. Augusto Alves Caldeira (OAB/RO 11.101; no PJe tambem OAB/MG 182.814)**.
> Tambem assina pecas: Dra. Lorena Gois Fontenele (OAB/RO 14.429). Coordenador Juridico: Dr. Willian.
> Nicho: **defesa do produtor rural contra bancos e cooperativas de credito** (prorrogacao e alongamento
> compulsorio de divida rural, tutela de urgencia, embargos a execucao). Tambem faz previdenciario rural.
> Ja usa: ADVBOX, Asaas, ZapSign, Atende Direito (WhatsApp), Gmail, servidor interno + Google Drive.

## Regra de ouro
- **A IA nao protocola e nao envia nada ao banco.** Toda peca, notificacao e relatorio sai para revisao humana.
- Briefing do escritorio (28/09/2026): a IA **pode definir a estrategia em casos simples e padronizados e em
  peticoes de andamento**; nos demais, a decisao e do Gestor Juridico / Coordenador.
- Nunca inventar dado de cliente, banco, valor, data, e-mail de banco ou jurisprudencia. Sem dado: `[CONFERIR]` / `[PREENCHER]`.
- Documento com `[CONFERIR]` ou `[PREENCHER]` **nunca** vai para assinatura nem vira rascunho de e-mail (trava no codigo).
- Nada sai do escritorio sem flag explicita (`--enviar`, `--rascunho-gmail`, `--criar-tarefas`) E a credencial no `.env`.
- Senha GOV.BR do cliente nunca por mensagem escrita. Publicidade dentro do Provimento 205/2021 da OAB.

## Mapa: fluxo do escritorio -> modulo
| Fase do manual | Modulo | Comandos principais | POP |
|---|---|---|---|
| Fluxo inicial (SDR, Closer, captacao) | `COMERCIAL/` | `sdr`, `radar`, `calculadora`, `meta-ads`, `auditoria-atendimento` | `docs/POP_COMERCIAL.md`, `docs/ROTEIRO_CLOSER.md` |
| 1 Onboarding + 2 Formalizacao | `CONTRATACAO/` | `novo`, `enviar`, `acompanhar`, `painel`, `exemplo` | `docs/POP_FASE_CONTRATACAO.md` |
| 3 Extrajudicial | `EXTRAJUDICIAL/` | `notificar`, `rascunho`, `registrar-envio`, `registrar-resposta`, `acompanhar`, `consumidor-gov`, `proposta`, `decisao`, `relatorio-gestor`, `painel` | `docs/POP_FASE_EXTRAJUDICIAL.md` |
| 4 Judicial | `JUDICIAL/` | `checklist`, `inicial`, `agravo`, `replica`, `embargos`, `contrarrazoes`, `manifestacao`, `pecas` | `docs/POP_FASE_JUDICIAL.md` |
| 5 Acompanhamento + 6 Finalizacao | `CONTROLADORIA/` | `varredura`, `avisos-cliente`, `relatorio-clientes`, `planilha`, `parados`, `finalizar` | `docs/POP_FASE_ACOMPANHAMENTO.md` |
| Gestao (pauta de segunda, auditoria de sexta) | `GESTAO/` | `pauta`, `auditoria`, `gargalos` | `docs/POP_GESTAO.md` |
| Financeiro | `FINANCEIRO/` | `cobranca`, `inadimplencia`, `fechamento`, `honorarios-novos` | `docs/MAPA_DO_SISTEMA.md` |

Uso: `python MODULO/main.py <comando>` na pasta do sistema. Quase todo comando aceita `--exemplo` (dados ficticios).
Tabela completa (cargo, rotina agendada, credencial de cada comando): `docs/MAPA_DO_SISTEMA.md`.
Guia da equipe: `docs/COMECE_AQUI.md`. O que falta configurar: `docs/ONBOARDING.md`.

## Estrutura
```
NUCLEO/          ambiente (.env, caminhos), ia (Claude: JSON por schema e texto longo), docx_caldeira (timbrado)
INTEGRACOES/     advbox, asaas, zapsign, atendedireito, gmail (so rascunho), comunica_djen, meta_ads (so leitura)
CONTRATACAO/ EXTRAJUDICIAL/ JUDICIAL/ CONTROLADORIA/ GESTAO/ COMERCIAL/ FINANCEIRO/
BASE_CONHECIMENTO/  DNA_PECAS.md (teses, foro, estilo, o que os bancos alegam) + ESQUELETOS/ por tipo de peca
DOCS_MODELOS/    contrato, procuracao, declaracao (hoje PROVISORIOS - travam o envio)
config/          escritorio.py, equipe.py, regras_financeiras.py, bancos_emails.json, timbrado, .env (nao versionar)
deploy/          Windows (instalar + agendar todas as rotinas) e VPS (systemd/Docker + healthcheck)
SAIDA/           relatorios gerados (nao versionado: tem dado de cliente)
```
Pasta de cada cliente: `PASTA_CLIENTES_RAIZ/AGRONEGOCIO/NOME/` com `00 CONTRATACAO/caso.json` = estado do caso,
lido e gravado por todas as fases (`etapa`, `prazos`, `extrajudicial`, `judicial`).

## Onde mexer
| O que | Arquivo |
|---|---|
| Nome, advogados da procuracao, prazos (15/60 dias), checklist, pastas | `config/escritorio.py` |
| Cargos -> usuarios do ADVBOX, tarefas abertas | `config/equipe.py` |
| E-mails dos bancos por agencia | `config/bancos_emails.json` |
| Comissoes e exclusoes do financeiro | `config/regras_financeiras.py` |
| Valores das propostas do comercial | `COMERCIAL/config_comercial.py` |
| Regras da controladoria (classificacao, D-3, pecas sugeridas) | `CONTROLADORIA/configuracao.py` |
| Teses e estilo das pecas | `BASE_CONHECIMENTO/DNA_PECAS.md` e `ESQUELETOS/` |

## Padrao de pecas (tirado das pecas reais)
Times New Roman 12, justificado, espacamento 1,5, titulos e nomes das partes em laranja #C45911 (iniciais e
notificacoes; replicas e recursos em preto), timbrado com logo, marca d'agua e rodape (`config/timbrado_modelo.docx`).
Carro-chefe: "Acao Mandamental de Prorrogacao Compulsoria de Divida Rural com Pedido de Tutela Provisoria Antecipada
em Carater de Urgencia" (Sumula 298/STJ + MCR 2.6.4). Justica Federal so contra a Caixa.

## ADVBOX
Tarefas pelo endpoint `/posts`; texto no campo `comments`; remetente = cargo em `config/equipe.py`.
Rate limit 30 GET/min. Nunca criar tarefa sem `--criar-tarefas` explicito (confirmacao item a item).

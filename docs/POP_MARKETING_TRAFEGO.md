# POP - Marketing: tráfego pago e funil (Caldeira Advogados Associados)

> Objetivo: gerar conversas no WhatsApp com produtores rurais de Rondônia e do norte do Mato Grosso, medir
> quais anúncios e regiões trazem **contrato** (e não só clique) e decidir a verba com número na mão, sem agência.
> Guia de 10 minutos por dia para quem monitora: `docs/GUIA_MONITOR_CAMPANHAS.md`.

## Visão geral

| Etapa | Quem | O sistema faz | A pessoa faz |
|---|---|---|---|
| Planejar a campanha | Gestor + quem monitora | `plano`: regiões pelo radar de crédito rural, divisão da verba, públicos, 4 ângulos com roteiro de vídeo, teste A/B de 14 dias, CSV de montagem | Revisar os textos (advogado), gravar os vídeos, montar no Gerenciador **pausado**, ativar |
| Acompanhar todo dia | quem monitora | `criativos` (7h15): cada anúncio recebe ESCALAR / MANTER / PAUSAR / TROCAR CRIATIVO com o motivo | Ler o resumo do WhatsApp; decidir |
| Mexer na conta | Gestor | `acoes`: lista o que faria (pausar, orçamento ±20%, duplicar pausado); só executa com `--aplicar` e "SIM" digitado item a item | Confirmar ou pular cada item |
| Medir o resultado | Gestor / titular | `funil` (dia 2): gasto -> conversas -> qualificados -> reuniões -> contratos; CPL, custo por reunião, custo por contrato, ROI | Decidir a verba do mês seguinte |
| Receber o lead | SDR | `landing` e `utm`: página do produtor e links com código "ref." | Registrar a ORIGEM do lead com o código |

## Comandos

Rodados na pasta do sistema. Todo comando aceita `--exemplo` (dados fictícios) e `--saida PASTA`.

```
python MARKETING/trafego.py plano --orcamento-mensal 3000 [--uf RO,MT] [--radar ARQ.json] [--ia]
python MARKETING/trafego.py criativos --dias 7|14|30 [--sem-ia]
python MARKETING/trafego.py acoes --dias 7 [--aplicar]
python MARKETING/trafego.py funil [--mes MM/AAAA] [--csv ATENDIMENTO.csv] [--gasto VALOR]
python MARKETING/trafego.py landing [--whatsapp 5569...] [--pixel ID] [--calculadora-url URL]
python MARKETING/trafego.py utm --campanha X --conjunto Y --anuncio Z [--landing-url URL]
```

Saídas em `SAIDA/marketing/` (`plano/`, `criativos/`, `acoes/`, `funil/`, `acoes_log.json`, `utm_codigos.csv`).
A landing é gerada em `MARKETING/landing/index.html` (o `modelo.html` ao lado é o molde; não publicar o molde).

## 1. Plano de campanha (`plano`)

1. Gerar o radar antes (leva alguns minutos, dado público do Banco Central): `python COMERCIAL/main.py radar`.
2. `python MARKETING/trafego.py plano --orcamento-mensal 3000` (use `--ia` para 2 variações de texto por ângulo).
3. Sai um DOCX no timbrado + um CSV (uma linha por anúncio) + JSON.

Como o plano é montado (regras em `REGRAS`, no topo de `MARKETING/trafego.py`):
- **Regiões**: os 15 municípios do topo do índice do radar (RO + só o norte do MT), agrupados por estado e
  mesorregião; grupo grande é dividido em "núcleo" e "ampliação" (até 6 cidades por conjunto, em partes iguais).
- **Verba**: piso de R$ 20/dia por conjunto; o que sobra é dividido pelo volume de crédito rural das cidades do
  conjunto; com 3 ou mais conjuntos, nenhum leva mais de 50% durante o teste. Conjunto que não cabe na verba vai para a "fase 2".
- **Público**: cidade + raio de 40 km, 28 a 65+ anos, interesses do agro. Interesse marcado `[CONFERIR]` precisa ser
  achado pelo nome no Gerenciador (com `META_ACCESS_TOKEN`, o comando já confere na API de busca de interesses).
- **Ângulos**: A1 o que diz a regra (MCR 2-6-4 / Súmula 298), A2 documentos que ajudam, A3 produtor de soja,
  A4 calculadora de juros (conteúdo útil). Cada um com título, texto, mensagem pré-preenchida e roteiro de vídeo
  de 15-30 s (cena, fala, texto na tela). Todos passam pela checagem de conformidade (`MARKETING/conformidade.py`).
- **Teste A/B de 14 dias** e **critérios de corte**: no DOCX (seções 5 e 6).

O CSV é o roteiro de montagem, não o arquivo de importação em massa do Meta. Montar: 1 campanha (objetivo de
conversas no WhatsApp, orçamento no **conjunto**), 1 conjunto por região, 1 anúncio por ângulo em cada conjunto,
tudo pausado até a revisão do texto.

## 2. Análise de criativos (`criativos`, diário 7h15)

Lê a conta (só leitura): gasto, conversas, CPL, CTR, frequência, retenção do vídeo (3 s / impressões, 50%, 100%),
compara com o período anterior do mesmo tamanho e dá um veredito por anúncio:

| Veredito | Regra (valores em `REGRAS` e `COMERCIAL/config_comercial.py`, `META`) |
|---|---|
| PAUSAR | gastou >= R$ 50 (ou 2x o CPL de referência) sem conversa; ou CPL >= 2x a referência com gasto >= 3x; ou texto com alerta grave de conformidade |
| TROCAR CRIATIVO | frequência > 3 com CTR caindo 20%+ (cansaço); frequência > 4,5; CTR < 0,8% depois de 1.000 impressões; menos de 15% assistem 3 s do vídeo |
| ESCALAR | 5+ conversas e CPL <= 80% da referência, sem cansaço |
| MANTER | o resto (inclui "poucos dados": menos de 1.000 impressões) |

Referência de CPL = `META['cpl_alvo']` em `COMERCIAL/config_comercial.py`; enquanto estiver `None`, é a média da conta
no período. Definir o alvo depois dos 7 primeiros dias.

Saídas: HTML (tabelas ordenáveis), TXT curto para colar no WhatsApp e JSON. Com `ANTHROPIC_API_KEY`, a IA escreve
uma leitura em linguagem simples **só com os números calculados** (nunca troca o veredito); `--sem-ia` desliga.
Sem Meta configurado, a rotina registra "nada feito" e sai sem erro.

## 3. Ações na conta (`acoes`) - com trava

`python MARKETING/trafego.py acoes --dias 7` mostra o que seria feito (simulação, nada é enviado). Para executar:
`--aplicar`. As travas estão no código (`MARKETING/meta_acoes.py`) e não dependem de configuração:

1. Credencial própria de escrita `META_ACCESS_TOKEN_ACOES` (usuário do sistema com `ads_management`). O token de
   leitura das rotinas não serve: a rotina diária nunca consegue alterar a conta.
2. Só com uma pessoa no terminal (não roda pelo agendador) e **"SIM" digitado em cada item**. Qualquer outra resposta pula.
3. Status só vai para PAUSADO. Nada é ativado pelo sistema.
4. Orçamento diário de conjunto: no máximo **20% por vez**, calculado sobre o valor lido da API na hora, e no máximo
   **1 mudança a cada 72 h** no mesmo conjunto. Conjunto com orçamento na campanha (CBO) ou vitalício: bloqueado,
   ajuste à mão.
5. Duplicar conjunto vencedor: a cópia nasce **PAUSADA** e é conferida logo depois (se vier ativa, é pausada na hora).
   Máximo 1 cópia do mesmo conjunto por semana; máximo 10 ações por rodada.
6. Tudo vai para `SAIDA/marketing/acoes_log.json` (quem, quando, antes/depois, resultado).

"TROCAR CRIATIVO" aparece na lista como tarefa da equipe (não há ação automática).

Chamadas da Graph API usadas: `POST /{ad_id} status=PAUSED`, `POST /{adset_id} daily_budget=<centavos>`,
`POST /{adset_id}/copies deep_copy=true status_option=PAUSED`, `POST /{ad_id}/copies status_option=PAUSED`.
`daily_budget` vai em centavos (R$ 50,00 = 5000).

## 4. Funil do mês (`funil`, dia 2 às 8h, mês anterior)

| Número | De onde vem |
|---|---|
| Gasto e conversas iniciadas | Meta Ads (só leitura) ou `--gasto` informado à mão |
| Leads de anúncio, qualificados, reuniões | `--csv` do atendimento (mesmas colunas da auditoria, `docs/POP_COMERCIAL.md`) ou API Flow do Atende Direito |
| Contratos | casos da CONTRATACAO pela `data_contrato` (a coluna "fechou" do CSV é conferência) |
| Receita | campo `valor` (ou `valor_contrato`, `valor_honorarios`) no caso ou no cadastro, se existir |

Indicadores: CPL, custo por qualificado, custo por reunião, **custo por contrato (CAC)**, receita e ROI
((receita - gasto) ÷ gasto), e a comparação com a agência antiga (R$ 2.200/mês de taxa, 5 a 6 contratos/mês no
total). Número sem fonte aparece como **"sem dado"**, nunca como zero. Saídas: DOCX no timbrado + HTML + JSON.

Lead de anúncio = origem com "Meta", "Facebook", "Instagram" (menos "orgânico"), "anúncio", "tráfego" ou o
código `MKT-XXXXX`. Por isso o SDR precisa registrar a **origem** de cada conversa (e o `origem` no cadastro da
contratação).

## 5. Landing e links com UTM

- `landing`: gera `MARKETING/landing/index.html`, um arquivo só (logo embutido), para o celular: para quem é, o que
  diz a regra, como o escritório ajuda, documentos, perguntas frequentes, botão de WhatsApp com mensagem
  pré-preenchida e link para a calculadora. Pixel do Meta **desligado**; `--pixel ID` liga (com aviso de cookies).
  Ao publicar, rodar de novo com `--calculadora-url https://...` (o padrão aponta para a calculadora no computador).
- `utm`: gera o código `MKT-XXXXX`, a UTM padronizada (`utm_source=meta`, `utm_medium=trafego_pago`,
  `utm_campaign`, `utm_term`=conjunto, `utm_content`=anúncio), o link de WhatsApp e o link da landing. O código é
  gravado em `SAIDA/marketing/utm_codigos.csv` e o funil o traduz de volta para campanha/conjunto/anúncio.
- Anúncio de WhatsApp (clique para conversar) não usa link: colar a mensagem com o código no campo "mensagem
  pré-preenchida" do anúncio. A landing repassa o `ref` e as UTMs para a mensagem e para a calculadora.

## Rotinas

| Rotina | Quando | Log |
|---|---|---|
| `MARKETING/trafego.py criativos --dias 7` | todo dia 7h15 | `logs/marketing_criativos.log` |
| `MARKETING/trafego.py funil` (mês anterior) | dia 2, 8h | `logs/marketing_funil.log` |

Agendadas em `deploy/agendar_tarefas_windows.bat` **ou** na VPS (`deploy/vps/systemd/caldeira-marketing-*`,
`deploy/vps/docker/crontab`), nunca nas duas. `acoes --aplicar` nunca é agendado.

## Checklist do anúncio (Provimento 205/2021) - antes de ativar

- [ ] Informativo: explica a regra ou o documento, sem prometer resultado ("garantimos", "resolvemos", "suspensão garantida").
- [ ] Sem preço, sem "grátis", sem desconto, sem forma de pagamento.
- [ ] Sem sensacionalismo nem urgência artificial ("última chance", "não perca", "!!").
- [ ] Sem "melhor escritório", "nº 1" ou comparação com colegas.
- [ ] Sem caso de cliente identificável, sem número sem fonte oficial.
- [ ] Nome do escritório e OAB no vídeo ou na página.
- [ ] A checagem automática (`conformidade`) não substitui a leitura de um advogado.

## Variáveis do `config/.env`

| Variável | Para quê | Obrigatória? |
|---|---|---|
| `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_API_VERSION` | leitura da conta (criativos, funil, conferir interesses) | para os relatórios com dado real |
| `META_ACCESS_TOKEN_ACOES` | escrita, só para `acoes --aplicar` (permissão `ads_management`) | não |
| `ANTHROPIC_API_KEY`, `MODELO_MARKETING` | leitura da IA nos criativos e variações do plano (`--ia`) | não (padrão `MODELO_SDR`) |
| `ATENDE_DIREITO_FLOW_TOKEN` | funil sem `--csv` | não |
| `MARKETING_LANDING_URL`, `MARKETING_CALCULADORA_URL` | endereços publicados (links com UTM e botão da calculadora) | não |
| `PASTA_CLIENTES_RAIZ` | contratos do funil | sim, para o funil |

## Limites e o que conferir no primeiro uso com a conta real

- Tudo foi testado com dados fictícios e com a API simulada: **nenhuma chamada real ao Meta foi feita**. No 1º uso:
  rodar `criativos` e conferir se os campos de vídeo (`video_p50_watched_actions` etc.) e as conversas
  (`onsite_conversion.messaging_conversation_started_7d`) chegam preenchidos.
- `acoes --aplicar`: testar primeiro com um anúncio de teste; conferir a cópia profunda de conjunto com muitos
  anúncios (a API pode exigir cópia assíncrona) e o nome do parâmetro `rename_options` na versão da API em uso.
- Interesses `[CONFERIR]`, objetivo e nome dos campos do Gerenciador mudam com frequência: conferir na tela.
- Se o Meta exigir "categoria especial de anúncio" (serviços financeiros), idade e raio ficam limitados.
- O radar mostra crédito rural **emitido** por município (não inadimplência) e é dado agregado: serve para escolher
  onde anunciar, nunca para abordar pessoas.
- O funil só é tão bom quanto o registro da origem: sem origem no atendimento e no cadastro, o custo por contrato
  sai calculado sobre todos os contratos (e o relatório avisa).

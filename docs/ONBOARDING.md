# Onboarding - o que falta para o sistema rodar em produção

Enquanto um item não chega, a etapa correspondente fica em modo seguro (gera arquivos, nada sai do escritório).
Variáveis completas: `config/.env.example`. Tabela de qual comando usa qual chave: `docs/MAPA_DO_SISTEMA.md`.

## 1. Credenciais (canal seguro, direto no config/.env de CADA máquina - Windows e Mac)
- [ ] `ANTHROPIC_API_KEY` - conta Anthropic do escritório (obrigatória)
- [ ] `PASTA_CLIENTES_RAIZ` - pasta de clientes no servidor interno, do jeito de cada máquina:
      Windows `Z:\CLIENTES` ou `\\SERVIDOR\CLIENTES`; Mac `/Volumes/CLIENTES` (conectar antes em `smb://SERVIDOR/CLIENTES`)
- [ ] `ZAPSIGN_API_TOKEN` - ZapSign > Configurações > API
- [ ] `ATENDE_DIREITO_TOKEN` (e, se houver, `ATENDE_DIREITO_FLOW_TOKEN` para medir tempo de resposta)
- [ ] `ADVBOX_API_TOKEN` - conferir se o plano libera API
- [ ] `ASAAS_API_TOKEN`
- [ ] Gmail do escritório: cliente OAuth em `config/credentials_gmail.json` + `python INTEGRACOES/gmail_integration.py autorizar` (só cria rascunho)
- [ ] `META_ACCESS_TOKEN` + `META_AD_ACCOUNT_ID` (relatório do Meta Ads, só leitura)
- [ ] `ALERTA_WHATSAPP` - número que recebe alerta quando algo cai

## 2. Do escritório
- [ ] Modelos oficiais em .docx: contrato de honorários, procuração, declaração (campos em `docs/CAMPOS_DOS_MODELOS.md`)
- [ ] Timbrado oficial em .docx (hoje reconstruído das peças: `config/timbrado_modelo.docx`)
- [ ] Advogados da procuração (hoje: Augusto Caldeira e Lorena Gois Fontenele) e confirmar a OAB/MG 182.814 do Dr. Augusto
- [ ] Nome e ID do ADVBOX de cada cargo (`config/equipe.py`); tipos de tarefa e de processo usados no ADVBOX
- [ ] E-mails dos bancos por agência, com razão social e CNPJ (`config/bancos_emails.json`) - sem isso a notificação não vira rascunho
- [ ] Valores das propostas do comercial (`COMERCIAL/config_comercial.py`) e número de WhatsApp da calculadora
- [ ] Comissões e exclusões do financeiro (`config/regras_financeiras.py`) e `FINANCEIRO/clientes_nao_cobrar.txt`
- [ ] Nomenclatura das pastas no servidor e pasta de ARQUIVO para casos encerrados (`PASTA_ARQUIVO_CLIENTES`)
- [ ] Feriados estaduais e municipais (`FERIADOS_EXTRAS`)
- [ ] Prazos: manter 15/60 dias ou reduzir para 5/15 (`PRAZOS` em `config/escritorio.py`)
- [ ] Notificação: fixar prazo de resposta no texto? padrão de 3 anos de carência + 15 parcelas sem laudo?
- [ ] Cor das peças: laranja só na inicial e notificação (como hoje) ou em todas
- [ ] Marketing: logo em vetor/PNG grande, fontes da marca (se houver, em `config/fontes/`), fotos reais da equipe e do
      escritório, aprovação do tom de voz e da linha de identificação das legendas; publicar a landing e a calculadora
      no site e informar os endereços (`MARKETING_LANDING_URL`, `MARKETING_CALCULADORA_URL`)
- [ ] Token separado do Meta com `ads_management` (`META_ACCESS_TOKEN_ACOES`), só se o escritório quiser executar ações pela IA
- [ ] Checklist do previdenciário (salário-maternidade, BPC), se entrar na contratação

## 3. Conferir no primeiro uso real
- [ ] Jurisprudência citada no DNA com número a conferir (lista em `docs/POP_FASE_JUDICIAL.md`) antes de protocolar
- [ ] Nomes de campos do ADVBOX (transações, /posts, /last_movements) e filtro de data do Asaas
- [ ] Uma análise de proposta de banco com IA (`EXTRAJUDICIAL/main.py proposta`)
- [ ] Algumas conversas da auditoria de atendimento contra o painel do Atende Direito

## 4. Instalação (o escritório tem Windows e Mac)
- [ ] Definir **qual máquina roda as rotinas automáticas** (uma só: um Windows, um Mac ou a VPS) e quais
      só usam os comandos sob demanda
- [ ] Instalar em cada máquina que vai usar o sistema e criar o `config/.env` dela
- [ ] Conferir em cada máquina: `/checar` (Windows) ou `--checar` (Mac)

**Windows**
```
deploy\instalar_windows.bat             (instala, cria .env, testa com caso fictício)
deploy\agendar_tarefas_windows.bat      (como administrador; /listar e /remover disponíveis)
```
Instalar num caminho curto (ex.: `C:\CALDEIRA`).

**Mac** (Python 3.10+ do python.org ou `brew install python@3.12`; PDF: Word ou `brew install --cask libreoffice`;
OCR: `brew install tesseract tesseract-lang`)
```
bash deploy/mac/instalar_mac.sh          (ou duplo clique em deploy/mac/Instalar no Mac.command)
bash deploy/mac/agendar_tarefas_mac.sh   (ou "Agendar rotinas no Mac.command"; --listar e --remover disponíveis)
```
Instalar fora de Documentos/Mesa/Downloads/iCloud (ex.: `~/CALDEIRA_ADVOGADOS`). Mac das rotinas: ligado nos
horários, usuário logado, sem repouso automático (Ajustes > Bateria/Energia) e servidor em Itens de Início.

Nunca ligar rotinas em duas máquinas (ou máquina + VPS) ao mesmo tempo: o cliente recebe mensagem em dobro.
VPS 24h: `docs/DEPLOY_VPS.md`.

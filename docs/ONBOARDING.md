# Onboarding - o que falta para a fase de contratacao rodar em producao

Enquanto um item nao chega, a etapa correspondente fica em modo seguro (nada sai do escritorio).

## Credenciais (canal seguro, direto no config/.env da maquina do escritorio)
- [ ] `ANTHROPIC_API_KEY` - conta Anthropic do escritorio (obrigatoria)
- [ ] `ZAPSIGN_API_TOKEN` - ZapSign > Configuracoes > API
- [ ] `ATENDE_DIREITO_TOKEN` - Atende Direito > Integracoes
- [ ] `ADVBOX_API_TOKEN` - ADVBOX > Configuracoes > API (conferir se o plano libera API)
- [ ] `ASAAS_API_TOKEN` - Asaas > Integracoes > Chave de API
- [ ] `PASTA_CLIENTES_RAIZ` - caminho da pasta de clientes no servidor interno

## Do escritorio
- [ ] Modelos oficiais em .docx: contrato de honorarios, procuracao, declaracao de hipossuficiencia
      (trocar dados pelos campos de `docs/CAMPOS_DOS_MODELOS.md`)
- [ ] Timbrado oficial em .docx (hoje reconstruido das pecas: `config/timbrado_modelo.docx`)
- [ ] Lista de advogados que devem constar na procuracao (hoje: Augusto Caldeira e Lorena Gois Fontenele)
- [ ] Nome de cada pessoa por cargo e o ID no ADVBOX (`config/equipe.py`)
- [ ] Tipo de processo e fase inicial usados no ADVBOX para o agro (`ADVBOX_TIPO_PROCESSO`, `ADVBOX_FASE_INICIAL`)
- [ ] Nomenclatura padrao das pastas no servidor (ajustar `config/escritorio.py`)
- [ ] Decisao sobre prazos: manter 15/60 dias ou reduzir para 5/15 (`PRAZOS` em `config/escritorio.py`)
- [ ] Checklist do previdenciario (salario-maternidade, BPC), se for entrar nesta fase tambem

## Instalacao na maquina do escritorio
```
pip install -r requirements.txt
copy config\.env.example config\.env      (preencher)
python CONTRATACAO/main.py exemplo         (teste com caso ficticio)
deploy\agendar_acompanhamento_windows.bat  (como administrador)
```

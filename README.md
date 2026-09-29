# Caldeira Advogados Associados - Automações

Ecossistema de IA do escritório, instalado na máquina e no servidor do próprio escritório (e opcionalmente numa
VPS 24h). Cobre o fluxo inteiro do serviço, do primeiro contato do produtor à finalização do processo.

| Módulo | O que faz |
|---|---|
| `COMERCIAL/` | SDR de IA, roteiro do Closer, radar de crédito rural por município, calculadora de juros, Meta Ads, auditoria de atendimento |
| `CONTRATACAO/` | Relatório de Triagem da reunião, contrato + procuração + declaração no timbrado, ZapSign, ADVBOX, Asaas, cobrança de documentos |
| `EXTRAJUDICIAL/` | Notificação a cada banco, rascunho no Gmail, prazo de resposta, consumidor.gov, parecer de proposta |
| `JUDICIAL/` | Checklist pré-protocolo, inicial mandamental com tutela, agravo, réplica, embargos, contrarrazões |
| `CONTROLADORIA/` | Intimações do DJEN, prazos com D-3, tarefas no ADVBOX, avisos e relatório ao cliente, planilha, finalização |
| `GESTAO/` | Pauta de segunda, auditoria de sexta, gargalos da equipe |
| `FINANCEIRO/` | Régua de cobrança de honorários, inadimplência, fechamento mensal |

```
deploy\instalar_windows.bat          instala e testa
python CONTRATACAO/main.py exemplo   caso fictício de ponta a ponta
deploy\agendar_tarefas_windows.bat   liga as rotinas automáticas
```

- Guia da equipe: `docs/COMECE_AQUI.md`
- Mapa fase → comando → cargo → rotina → credencial: `docs/MAPA_DO_SISTEMA.md`
- O que falta configurar: `docs/ONBOARDING.md`
- VPS: `docs/DEPLOY_VPS.md`

A IA não protocola e não envia nada ao banco. Toda saída passa por revisão humana.

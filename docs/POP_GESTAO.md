# POP - Gestão: pauta de segunda, auditoria de sexta e gargalos (Caldeira Advogados Associados)

A dor dita na reunião: "cada um fica num setor, eles se perdem, eu me perco". O controle é de pauta:
na **segunda**, o que cada um faz na semana; na **sexta**, a auditoria (fez? protocolou? prazos cumpridos?).
A automação monta os dois a partir do ADVBOX, das varreduras do DJEN (Controladoria) e das pastas dos clientes.
Tudo é só leitura: nada é criado, alterado ou enviado.

## Visão geral

| Rotina | Quem conduz | O que a automação entrega | O que continua humano |
|---|---|---|---|
| Reunião de pauta (segunda) | Titular / Gestor Jurídico | `pauta`: por pessoa, tarefas atrasadas e da semana; prazos fatais, audiências e perícias; casos em cada fase; documentos pendentes; notificações (15 dias) e iniciais (60 dias) perto do limite | Redistribuir, cobrar, registrar as decisões na seção 7 |
| Auditoria (sexta) | Titular / Coordenador | `auditoria`: concluído x não concluído por pessoa, concluídas com atraso, tempo médio por pessoa e por tipo, casos que estouraram 15/60 dias e indicadores dos manuais | Conferir no PJe o que aparece como "prazo possivelmente perdido"; leads e tempo de atendimento |
| Gargalos (mensal ou quando precisar) | Titular | `gargalos`: tempo médio de conclusão por pessoa/tipo, abertas há muito tempo, quem acumula mais, peça pronta sem protocolo e sugestões objetivas | Decidir redistribuição, modelos e mutirões |

## Passo a passo

1. **Segunda, antes da reunião (agendado 07:00 pelo `deploy/`):** `python GESTAO/main.py pauta`
   Sai em `SAIDA/gestao/pauta/`: o documento no timbrado e o `... - WhatsApp.txt` (resumo curto para colar no grupo).
2. **Na reunião:** percorrer a seção 3 (por pessoa) e a 5 (marcos 15/60). Anotar na seção 7 quem faz o quê até quando.
3. **Sexta (agendado 16:00):** `python GESTAO/main.py auditoria` → documento + resumo em `SAIDA/gestao/auditoria/`.
4. **Gargalos:** `python GESTAO/main.py gargalos --dias 90` → documento + CSV por pessoa e por tipo em `SAIDA/gestao/gargalos/`.
5. **Testar sem ADVBOX:** qualquer comando com `--exemplo` (dados fictícios).

## Indicadores da auditoria (dos manuais do escritório)

| Indicador | Como é medido |
|---|---|
| Zero perda de prazo fatal | Tarefa de PRAZO (ou criada pela Controladoria) vencida e não concluída no ADVBOX = "possível prazo perdido: conferir no PJe" |
| Antecedência nos protocolos | Dias entre a conclusão e o prazo das tarefas de protocolo/prazo concluídas na semana |
| Rapidez no protocolo da inicial | Dias do contrato ao protocolo da inicial (registrado no caso.json pelo módulo judicial) |
| Índice de liminares obtidas | Liminares deferidas ÷ (deferidas + indeferidas) nas publicações da semana |
| Taxa de decisões favoráveis | Sentenças favoráveis x desfavoráveis (pelo polo do cliente; "a conferir" quando o texto não permite) |
| Notificação em até 15 dias do onboarding | Casos com notificação enviada dentro do limite ÷ casos com o limite já vencido |
| Fase extrajudicial em até 60 dias | Casos com inicial protocolada dentro do limite ÷ casos com o limite já vencido |
| Novos contratos | Casos com data de contrato na semana |
| Leads e tempo de atendimento | Não vêm pela API do Atende Direito usada hoje: preencher na reunião |

## Critérios usados
- **Pessoa/cargo:** o usuário do ADVBOX é casado com o cargo por `config/equipe.py` (ID ou nome). Sem cadastro, aparece só o nome.
- **Atrasada:** tarefa aberta com prazo antes de hoje. **Da semana:** prazo de segunda a sexta.
- **Tempo de conclusão:** da criação da tarefa até a baixa no ADVBOX. Tarefa feita e não baixada conta como aberta
  (a API do ADVBOX não conclui tarefas: a baixa é manual e faz parte do controle).
- **Fases dos casos:** CONTRATAÇÃO → EXTRAJUDICIAL (notificação registrada) → JUDICIAL (inicial protocolada ou etapa judicial),
  a partir do `caso.json` de cada pasta (chaves `etapa`, `prazos`, `extrajudicial`, `judicial`).
- **Marcos 15/60:** limites calculados na contratação (`config/escritorio.py`, `PRAZOS`); "perto do limite" = 5 dias ou menos.

## Travas de segurança
- Só leitura: nenhum comando da Gestão cria tarefa, altera o ADVBOX ou envia mensagem.
- Sem `ADVBOX_API_TOKEN`, a parte do ADVBOX sai vazia com aviso na tela e no documento (`[CONFERIR]`).
- Leitura do ADVBOX ritmada (limite de 30 leituras por minuto): em escritório grande a pauta pode levar alguns minutos.
- Documentos com nomes de clientes ficam em `SAIDA/` (fora do Git).

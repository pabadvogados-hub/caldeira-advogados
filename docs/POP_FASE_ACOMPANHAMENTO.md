# POP - Fases 5 e 6: Acompanhamento processual e Finalização (Caldeira Advogados Associados)

Da primeira publicação do processo até o arquivamento da pasta.
Espelha o FLUXO DO SERVIÇO do escritório (5 Acompanhamento e 6 Finalização) e as funções do
Coordenador Jurídico (zero perda de prazo fatal, destravar processos parados, despachar liminares).

## Visão geral

| Etapa do manual | Quem era | O que a automação faz | O que continua humano |
|---|---|---|---|
| Ler as publicações/intimações | Coordenador / advogados | `varredura`: busca no DJEN tudo o que saiu nas OABs do escritório, cruza com o ADVBOX pelo número do processo e classifica cada publicação | Ler as marcadas como REVISÃO MANUAL e conferir as de confiança média |
| Calcular o prazo | Advogado responsável | Prazo fatal PRELIMINAR (publicação = 1º dia útil após a disponibilização; dias úteis; recesso 20/12 a 20/01) + prazo interno D-3 | Conferir o prazo no processo antes de trabalhar em cima dele |
| Distribuir a tarefa | Coordenador | Sugere o responsável (Coordenador para liminar negada, sentença, execução; senão o responsável do processo no ADVBOX) e, com `--criar-tarefas`, cria a tarefa no ADVBOX com prazo D-3, confirmando item a item | Confirmar cada tarefa; concluir no ADVBOX quando fizer |
| Pôr na agenda | Advogado | Arquivo `Agenda.ics` com prazos internos, fatais, audiências e perícias (importa no Google Agenda/Outlook); a tarefa do ADVBOX também entra na agenda do ADVBOX | Importar o .ics na agenda do escritório |
| Liminar concedida: avisar o cliente e acompanhar o cumprimento | Advogado judicial | `avisos-cliente`: mensagem pronta ao produtor (o que a liminar garantiu, tirado do texto da decisão) + lembrete de conferir o cumprimento em 10 dias úteis | Revisar a mensagem e enviar; peticionar descumprimento se o banco não cumprir |
| Liminar negada: avaliar recurso | Coordenador | Prazo de agravo (15 dias úteis) e comando sugerido da peça | Decidir se agrava; a IA não protocola |
| Comunicar audiências e perícias | Advogado | Data, hora e local tirados da publicação; mensagem ao cliente; evento na agenda | Ligar para o cliente antes da audiência/perícia |
| Atualizar a planilha de clientes | Estagiário / advogados | `planilha`: uma linha por cliente com fase, gravidade, travado?, próxima ação, responsável e prazos | Usar na reunião operacional e corrigir o que estiver errado no ADVBOX |
| Informar o andamento ao produtor (15 ou 30 dias) | Advogado | `relatorio-clientes`: um texto por cliente, em linguagem do dia a dia, com o que aconteceu no período | Revisar e marcar para envio |
| Identificar processos parados | Coordenador | `parados`: processos sem movimentação há N dias, com a provável causa (custas, juntada, tarefa aberta) e casos travados antes da ação | Conferir no PJe e destravar |
| Resultado favorável / desfavorável | Coordenador | Classifica a sentença pelo polo do cliente (quando o texto permite) e gera o aviso ao cliente | Explicar ao cliente; decidir recurso ou acordo |
| 6 Finalização (ADVBOX, agenda, pasta, registros) | Advogado / Estagiário | `finalizar`: checklist de encerramento, Termo de Encerramento, caso marcado ENCERRADO e pasta movida para o ARQUIVO | Concluir as tarefas no ADVBOX (a API não conclui) e mandar a mensagem final |

## Passo a passo

1. **Todo dia (agendado 07:30 pelo `deploy/`):** `python CONTROLADORIA/main.py varredura --dias 3` (3 dias para não perder
   publicação disponibilizada depois do horário da rodada anterior; o que repete não duplica tarefa nem aviso).
   Sai em `SAIDA/controladoria/varreduras/`: relatório no timbrado (DOCX), planilha (CSV), agenda (.ics) e o
   histórico (.json) que alimenta avisos, planilha e auditoria. Nada é criado nem enviado.
2. **Coordenador lê o relatório** (seção 2 = prazos por prioridade). ALTA = age hoje ou vence em até 5 dias úteis.
3. **Criar as tarefas:** `python CONTROLADORIA/main.py varredura --dias 3 --criar-tarefas`
   Mostra a lista e pergunta item a item. Não duplica (marca `DJEN#id` no texto da tarefa e guarda o registro).
   O que não achou processo no ADVBOX aparece no relatório para cadastrar.
4. **Opcional:** `--ia` pede à IA uma sugestão só para o que ficou em REVISÃO MANUAL (no máximo 3 chamadas por padrão;
   a sugestão vem marcada "IA - conferir").
5. **Avisos ao produtor:** `python CONTROLADORIA/main.py avisos-cliente` → ler os .txt em `SAIDA/controladoria/avisos/`,
   completar o que estiver em `[PREENCHER]`, escrever o nome em `revisado_por` e `SIM` em `enviar` no
   `INDICE_PARA_REVISAO.csv` → `python CONTROLADORIA/main.py avisos-cliente --enviar` (pede confirmação digitada).
   Sentença desfavorável: ligar antes; a mensagem só confirma a ligação.
6. **Relatório periódico (15 ou 30 dias):** `python CONTROLADORIA/main.py relatorio-clientes --dias 30` → mesma revisão
   → `--enviar`. Só entra quem não recebeu relatório no período. A coluna `sem_movimento` avisa quem ficou parado
   (conferir antes de dizer ao cliente que "está tudo andando").
7. **Reunião operacional:** `python CONTROLADORIA/main.py planilha` (.xlsx em `SAIDA/controladoria/planilhas/`).
8. **Processos parados (semanal):** `python CONTROLADORIA/main.py parados --dias 30`.
9. **Encerramento (fase 6):** `python CONTROLADORIA/main.py finalizar "PASTA DO CLIENTE" --motivo "..."`
   Com `--atualizar-advbox` grava a data de encerramento no processo do ADVBOX (pergunta antes).
10. **Testar sem tocar em nada:** qualquer comando com `--exemplo` usa dados fictícios.

## O que cada publicação pede (CONTROLADORIA/configuracao.py)

| Classificação | Prazo padrão (texto sem prazo) | Responsável | Providência / peça |
|---|---|---|---|
| Liminar deferida | conferir cumprimento em 10 dias úteis | Adv. Judicial | Avisar o cliente; petição de descumprimento se preciso |
| Liminar indeferida | 15 dias úteis | Coordenador | Agravo de instrumento (`python JUDICIAL/main.py agravo "PASTA"`) |
| Sentença favorável / desfavorável / a conferir | 5 (embargos de declaração) / 15 (apelação) | Coordenador | Avisar o cliente; ED, apelação ou acordo |
| Intimação para réplica | 15 dias úteis | Adv. Judicial | Réplica (`python JUDICIAL/main.py replica "PASTA"`) |
| Intimação para manifestação | 5 dias úteis (art. 218, §3º) | Adv. Judicial | Petição de manifestação |
| Custas / emenda / juntada | 15 dias úteis | Adv. Judicial (prioridade do Coordenador) | Guia, emenda ou juntada: o processo trava sem isso |
| Audiência | a própria data (interno D-3) | Adv. Judicial | Avisar cliente, preparar, agenda |
| Perícia | 15 dias úteis (quesitos/assistente) | Adv. Judicial | Avisar cliente, quesitos, documentos da propriedade |
| Execução / penhora / bloqueio contra o cliente | 15 dias úteis | Coordenador | Embargos à execução + efeito suspensivo + prejudicialidade |
| Recurso / embargos de declaração julgados | 15 dias úteis | Adv. Judicial / Coordenador | Contrarrazões ou recurso cabível |
| Trânsito em julgado | conferir em 2 dias úteis | Coordenador | Cumprimento pelo banco; depois `finalizar` |
| Despacho | sem prazo | - | Ciência |
| Não classificado | conferir em 2 dias úteis | Coordenador | REVISÃO MANUAL |

O classificador também descobre de que lado o cliente está (pelo "Advogados do(a) AUTOR/EXECUTADO..." do próprio
texto; sem isso, presume pela classe e avisa) e se o prazo do texto é da parte contrária ("intime-se o exequente") —
nesse caso não cria prazo, só acompanhamento.

## Travas de segurança
- Nada sai do escritório sem flag explícita (`--criar-tarefas`, `--enviar`, `--atualizar-advbox`) **e** credencial no `.env`.
- Tarefa no ADVBOX: só com `--criar-tarefas`, mostrando a lista antes e confirmando item a item; agendado (sem terminal) nunca cria.
- Mensagem ao cliente: só o que tiver `revisado_por` + `enviar=SIM`, sem `[PREENCHER]`/`[CONFERIR]` e com confirmação digitada `SIM`.
- Prazo é sempre PRELIMINAR: feriados locais só os de `FERIADOS_EXTRAS`; Carnaval e Corpus Christi não são pulados
  (na dúvida, a data sai mais cedo, nunca mais tarde).
- A IA não protocola e não decide estratégia: a providência é sugestão para o responsável e o Coordenador.
- Relatórios com dados de clientes ficam em `SAIDA/` (fora do Git).

## Configuração (config/.env)
| Variável | Para quê |
|---|---|
| `OABS_MONITORADAS=11101/RO,14429/RO,182814/MG` | OABs consultadas no DJEN (a 182814/MG é a inscrição do titular usada no PJe do TJRO/TRF1) |
| `PRAZO_INTERNO_DIAS_ANTES=3` | Antecedência do prazo interno (dias úteis) |
| `FERIADOS_EXTRAS=` | Feriados locais (DD/MM ou DD/MM/AAAA, separados por vírgula) |
| `RELATORIO_CLIENTE_DIAS=30` | Periodicidade do relatório ao produtor |
| `PASTA_ARQUIVO_CLIENTES=` | Onde ficam as pastas encerradas (padrão: `PASTA_CLIENTES_RAIZ/ARQUIVO`) |
| `ADVBOX_TIPO_TAREFA_PADRAO=` | Tipo de tarefa do ADVBOX usado quando o tipo sugerido não existir |
| `MODELO_CONTROLADORIA=` | Modelo da IA do `--ia` (padrão: `MODELO_EXTRACAO`) |
| `ADVBOX_INTERVALO_GET=2.1` | Segundos entre leituras do ADVBOX (limite de 30 por minuto) |

Agendamento: central, em `deploy\agendar_tarefas_windows.bat` (Windows) ou `deploy/vps/` (servidor): varredura diária,
relatório aos clientes nos dias 1 e 16, pauta na segunda e auditoria na sexta. Agendado nunca cria tarefa nem envia.

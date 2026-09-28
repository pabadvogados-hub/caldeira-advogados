# POP - Fase de Contratacao (Caldeira Advogados Associados)

Do "fechou" do Closer ate o caso pronto para a notificacao extrajudicial.
Espelha o FLUXO DO SERVICO do escritorio (Fluxo inicial, 1 Onboarding e 2 Formalizacao) e mostra
o que a automacao faz e o que continua com cada cargo.

## Visao geral

| Etapa do manual | Quem era | O que a automacao faz | O que continua humano |
|---|---|---|---|
| Closer faz reuniao e fecha | Closer | - | Gravar a reuniao (Meet/ligacao) e preencher o `CADASTRO.txt` |
| Entrega relatorio ao Gestor (gatilhos, gaps, pontos importantes) | Closer | **Relatorio de Triagem** gerado da transcricao: gatilhos por gravidade, operacoes por banco, linha do tempo, 10 pontos de atencao, gaps, estrategia candidata, roteiro do onboarding | Gestor Juridico le e decide a estrategia |
| Entrega contrato ao Financeiro | Closer | `RESUMO PARA O FINANCEIRO.txt` + cobranca no Asaas (se o cadastro tiver os valores) | Financeiro confere |
| Levanta vencimentos, bancos, cedulas, natureza dos contratos | Gestor + Estagiario | Ja vem no relatorio (e dos documentos lidos, se enviados junto) | Confirmar na reuniao de onboarding |
| Estagiario pede documentos (checklist) e cadastra no ADVBOX | Estagiario | Mensagem no WhatsApp com a lista + cadastro de cliente e processo no ADVBOX + cobranca automatica D+1, D+3, D+7 ate chegar tudo | Separar o que chega fora do WhatsApp; pedir a senha GOV.BR por ligacao |
| Cria pasta no servidor | Estagiario | Pasta `AGRONEGOCIO/NOME/` com subpastas por item do checklist; documentos entram na subpasta certa | Salvar na subpasta certa o que chegar depois |
| Preenche procuracao + declaracao + contrato | Estagiario | Gerados no timbrado, com qualificacao da CNH/RG | **Revisar** antes de enviar |
| Envia para assinatura (ZapSign) | Estagiario | Envio + link ao cliente pelo WhatsApp + download dos assinados | - |
| Contrato assinado? Nao -> volta | Estagiario | `acompanhar` confere 3x ao dia | Ligar para quem nao assinou |
| Gestor providencia laudos | Gestor | O relatorio diz o que cada laudo precisa provar (e o que os bancos atacam: ART, vistoria) | Contratar agronomo e laudo financeiro |

## Passo a passo

1. **Reuniao de fechamento gravada.** Closer grava e baixa a transcricao (PDF, TXT, DOCX ou SRT do Meet).
2. **Cadastro.** Closer preenche `CADASTRO.txt` (modelo em `exemplos/CADASTRO_MODELO.txt`): telefone, e-mail,
   estado civil, profissao, data do contrato e honorarios (texto do contrato + numeros para o Asaas).
3. **Rodar:**
   `python CONTRATACAO/main.py novo "TRANSCRICAO.pdf" "CNH.pdf" [outros documentos] --cadastro CADASTRO.txt`
4. **Gestor le o Relatorio de Triagem** (`00 CONTRATACAO/... - Relatorio de Triagem - data.pdf`).
   Gatilhos ALTA = agir no mesmo dia (parcela vencendo, busca e apreensao, execucao).
5. **Revisar os 3 documentos** em `00 CONTRATACAO/`. Pode editar no Word. Tudo que estiver em vermelho
   (`[CONFERIR ...]`, `[PREENCHER ...]`) precisa sumir, senao o envio trava.
6. **Enviar:** `python CONTRATACAO/main.py enviar "PASTA DO CLIENTE" --criar-tarefas`
   -> ZapSign + WhatsApp com links e lista de documentos + ADVBOX (cliente e processo) + Asaas + tarefas por cargo.
7. **Acompanhamento automatico** (agendado 3x ao dia): baixa os assinados e cobra os documentos que faltam.
   Chegou tudo: agradece e para. Esgotou a regua (3 mensagens): alerta o Gestor no `painel`.
8. **Painel:** `python CONTRATACAO/main.py painel` mostra dias de cada caso, documentos faltando e prazos
   (notificacao e inicial) com alerta a 3 dias do vencimento.

## Prazos calculados (config/escritorio.py)
| Marco | Regra | Responsavel |
|---|---|---|
| Pedir documentos | contrato + 1 dia | Estagiario |
| Reuniao de onboarding | contrato + 2 dias | Gestor Juridico |
| Notificacao extrajudicial | onboarding + 15 dias | Adv. Extrajudicial |
| Protocolo da inicial | contrato + 60 dias | Adv. Judicial / Coordenador |

## Travas de seguranca
- Documento com `[CONFERIR]`/`[PREENCHER]` nao vai para o ZapSign (nome incompleto, CPF invalido,
  nacionalidade ausente, modelo provisorio).
- Sem credencial no `.env`, a etapa e pulada e nada sai.
- Cobranca no Asaas so com valores numericos do cadastro, nunca do texto da reuniao.
- Tarefas no ADVBOX so com `--criar-tarefas` e IDs preenchidos em `config/equipe.py`.
- Senha GOV.BR nunca por mensagem.

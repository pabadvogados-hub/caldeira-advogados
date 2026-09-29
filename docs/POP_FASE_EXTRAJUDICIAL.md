# POP - Fase Extrajudicial (Caldeira Advogados Associados)

Do caso formalizado (contrato e procuracao assinados, documentos na pasta) ate o acordo com o banco
ou o encaminhamento ao judicial. Espelha a etapa 3 do FLUXO DO SERVICO e o manual do Adv. Extrajudicial,
e mostra o que a automacao faz e o que continua com cada cargo.

## Visao geral

| Etapa do manual | Quem era | O que a automacao faz | O que continua humano |
|---|---|---|---|
| Gestor delega o caso ao Adv. Extrajudicial | Gestor Juridico | `painel` mostra todos os casos, credores e prazos | Delegar e acompanhar |
| Conferir documentos (cedulas, laudos, procuracao) | Adv. Extrajudicial | Le as cedulas (pasta 03) e os laudos (pasta 06); valor que nao aparece na cedula sai com `[CONFERIR na cedula]` | Conferir o que ficou marcado |
| Elaborar a notificacao ao banco pedindo prorrogacao/renegociacao | Adv. Extrajudicial | **Uma notificacao por banco** no modelo do escritorio (longo: alongamento; curto: pedido de contratos), no timbrado, com fatos redigidos pela IA a partir do caso e dos documentos; DOCX + PDF em `10 EXTRAJUDICIAL` | **Revisar** e tirar todas as marcas vermelhas |
| Enviar ao banco por e-mail | Adv. Extrajudicial | Com `--rascunho-gmail`: **rascunho** no Gmail do escritorio com o e-mail do banco (base centralizada), assunto, corpo padrao, PDF da notificacao + procuracao assinada + laudos | Abrir o rascunho, revisar e **clicar em Enviar**; depois `registrar-envio` |
| Cobrar retorno dos bancos | Adv. Extrajudicial | `acompanhar` conta o prazo de resposta (10 dias corridos) e avisa quando vence | Ligar/escrever ao gerente |
| Banco respondeu? SIM | Adv. Extrajudicial | `registrar-resposta --arquivo` guarda a resposta na pasta; `proposta` gera o **PARECER PARA O GESTOR** (vantagens, riscos, clausulas de atencao, contraproposta) | Repassar TODA proposta ao Gestor; reuniao com o gerente se preciso |
| Acordo? SIM -> finaliza acordo extrajudicial | Gestor Juridico | `decisao --resultado acordo` registra | Formalizar o acordo, avisar o cliente, ADVBOX |
| Acordo? NAO / banco nao respondeu | Adv. Extrajudicial | `registrar-resposta --sem-resposta`; `consumidor-gov` gera o texto da reclamacao; `notificar` de novo gera a **reiteracao** | Protocolar no consumidor.gov.br com a conta GOV.BR do cliente; enviar a reiteracao |
| Encaminhar ao judicial | Adv. Extrajudicial -> Adv. Judicial | `relatorio-gestor` mostra o que falta na pasta para a inicial; `decisao --resultado judicial` registra | Gestor decide; Adv. Judicial assume |
| Relatorio/feedback ao Gestor | Adv. Extrajudicial | `relatorio-gestor` (DOCX + PDF): alertas, prazos, situacao por banco, propostas, reclamacoes, proxima acao | Revisar e entregar |
| Avisar o cliente | Adv. Extrajudicial | `acompanhar --enviar`: WhatsApp "notificamos o banco X em dd/mm" (1 vez por notificacao, so depois de `registrar-envio`) | Atender duvidas |
| ADVBOX/CRM atualizados | Adv. Extrajudicial | Tudo fica no `caso.json` (chave `extrajudicial`) | Lancar andamentos no ADVBOX |

## Passo a passo

1. **Base de e-mails dos bancos.** Preencher `config/bancos_emails.json` (uma entrada por agencia) so com
   e-mail conferido. Conferir com `python EXTRAJUDICIAL/main.py bancos` (mostra entradas vazias, e-mails
   invalidos e credores dos casos que ainda nao estao na base).
2. **Gerar as notificacoes:**
   `python EXTRAJUDICIAL/main.py notificar "PASTA DO CLIENTE"`
   - uma por banco/cooperativa do caso (credor nao bancario, como cerealista, so com `--banco`);
   - `--tipo contratos` quando o cliente nao tem as cedulas (modelo curto "PEDIDO DE CONTRATOS RURAIS");
   - `--carencia 3 --parcelas 15` quando o Gestor ja definiu o pedido (senao sai o que o laudo trouxer ou
     3 + 15 com `[CONFERIR]`);
   - `--sem-ia` gera o texto-base sem IA (fatos em `[PREENCHER]`).
3. **Revisar o .docx** em `10 EXTRAJUDICIAL/{Nome} - Notificacao Extrajudicial - {BANCO} - {data}.docx`.
   Pode editar no Word. Tudo em vermelho (`[CONFERIR ...]`, `[PREENCHER ...]`) precisa sumir: razao social,
   CNPJ e endereco da agencia (vem da base de e-mails), numero da cedula, valores confirmados na cedula,
   carencia e parcelas do laudo, fatos sem fonte. A ultima linha cinza ("MINUTA GERADA PELA IA - PRONTA
   PARA REVISAO") nao vai no PDF de envio.
4. **Rascunho no Gmail:** `python EXTRAJUDICIAL/main.py rascunho "PASTA" --banco "Banco do Brasil"`
   (ou `notificar ... --rascunho-gmail` se a minuta ja saiu sem marcas). O PDF e refeito a partir do .docx
   revisado. Abrir o Gmail, conferir destinatario e anexos, **clicar em Enviar**.
5. **Registrar o envio:** `python EXTRAJUDICIAL/main.py registrar-envio "PASTA" --banco "Banco do Brasil" [--data 30/09/2026]`
   Comeca a contar o prazo de resposta (10 dias corridos) e libera o aviso ao cliente.
6. **Acompanhamento diario** (agendar junto com o da contratacao):
   `python EXTRAJUDICIAL/main.py acompanhar --enviar`
   Alertas: notificacao atrasada (limite do caso), prazo de resposta vencido, minuta/rascunho parado,
   inicial a 15 dias ou menos do limite. Sugere a proxima acao de cada banco.
7. **Resposta do banco:**
   - chegou: `registrar-resposta "PASTA" --banco X --arquivo resposta.pdf`
   - com proposta: `proposta "PASTA" --banco X --arquivo proposta.pdf` -> parecer ao Gestor
   - nao chegou: `registrar-resposta "PASTA" --banco X --sem-resposta`
8. **Decisao do Gestor:** `decisao "PASTA" --banco X --resultado acordo|sem-acordo|judicial [--obs "..."]`
9. **Sem acordo:** `consumidor-gov "PASTA" --banco X` (texto pronto .txt/.docx) -> protocolar com a conta
   GOV.BR do cliente -> `consumidor-gov "PASTA" --banco X --protocolo NUMERO`; e `notificar "PASTA" --banco X`
   para a reiteracao (sai com "ASSUNTO: ... - REITERACAO" e cita a data da primeira).
10. **Relatorio ao Gestor:** `relatorio-gestor "PASTA"`; **painel geral:** `painel`.

## Fluxo de decisao (sugerido pela automacao em "proxima acao")

```
notificacao gerada -> revisada -> rascunho -> ENVIADA (prazo 10 dias)
   |- banco respondeu com proposta -> parecer -> Gestor decide
   |      |- acordo -> formalizar acordo extrajudicial
   |      '- sem acordo -> consumidor.gov + reiteracao -> judicial
   |- banco respondeu negando -> sem acordo (idem)
   |- banco mandou os contratos (modelo curto) -> guardar na pasta 03 -> notificacao de alongamento
   '- sem resposta -> consumidor.gov + reiteracao -> judicial
```

## Prazos

| Marco | Regra | Onde muda |
|---|---|---|
| Notificacao enviada | onboarding + 15 dias (proposta: 5) | `PRAZOS` em `config/escritorio.py` (vale para casos novos) |
| Resposta do banco (controle interno) | envio + 10 dias corridos | `PRAZO_RESPOSTA_BANCO_DIAS` em `EXTRAJUDICIAL/registro.py` ou no `.env` |
| Protocolo da inicial / fim da fase extrajudicial | contrato + 60 dias (proposta: 15) | `PRAZOS` em `config/escritorio.py` |
| Alerta de inicial | 15 dias antes do limite | `ALERTA_INICIAL_DIAS` em `EXTRAJUDICIAL/registro.py` |

A notificacao real do escritorio nao fixa prazo de resposta no texto; os 10 dias sao so controle interno.

## Travas de seguranca
- A IA nao envia nada ao banco. O sistema so cria **rascunho** no Gmail (escopo `gmail.compose`, sem funcao
  de envio); quem envia e o advogado, pelo Gmail.
- Rascunho so com `--rascunho-gmail`/`rascunho`, credencial do Gmail em `config/`, e-mail conferido na base,
  agencia sem ambiguidade e **nenhuma** marca `[CONFERIR]`/`[PREENCHER]` no .docx.
- Nunca inventar banco, CNPJ, e-mail, valor, data, numero de cedula ou decreto: sem dado, marca vermelha.
- Valor dito na reuniao e nao encontrado na cedula sai com `[CONFERIR na cedula]`.
- Proposta de banco nunca e aceita nem recusada pela automacao: o parecer vai ao Gestor.
- WhatsApp ao cliente so com `--enviar`, token do Atende Direito e envio registrado; 1 vez por notificacao.
- Reclamacao no consumidor.gov.br e protocolada com a conta GOV.BR do cliente; a senha e pedida por
  ligacao, nunca por mensagem.
- Credor nao bancario (cerealista, revenda) fica fora da fase ate o Gestor decidir.

## Primeira configuracao do Gmail
1. No Google Cloud do escritorio: ativar a Gmail API e criar um cliente OAuth "App para computador".
2. Salvar o JSON como `config/credentials_gmail.json` (nunca versionar).
3. `python INTEGRACOES/gmail_integration.py autorizar` -> login na conta que vai enviar as notificacoes
   -> cria `config/token_gmail.json`.

## O que fica no caso.json (chave `extrajudicial`)
Uma entrada por notificacao: `banco`, `tipo`, `numero` (1a, 2a...), `arquivo`, `pdf`, `gerada_em`,
`pendencias`, `email_destino`, `rascunho_id`, `rascunho_em`, `anexos`, `enviada_em`, `prazo_resposta`,
`resposta` (recebida/sem resposta, data, arquivo), `propostas` (arquivo, parecer), `consumidor_gov`
(texto, protocolo), `decisao` (acordo/sem-acordo/judicial), `whatsapp_cliente_em`, `proxima_acao`,
`historico`. A fase judicial le daqui a data da notificacao e a prova da resposta ou do silencio do banco.

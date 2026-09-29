# Roteiro do Closer - Reunião de fechamento (Caldeira Advogados Associados)

Baseado no Manual de Funções do escritório (cargo CLOSER) e no DNA das peças (`BASE_CONHECIMENTO/DNA_PECAS.md`, seção 4).
Serve para duas coisas ao mesmo tempo:

1. **Fechar o contrato** de forma consultiva, técnica e ética (Provimento 205/2021 e Código de Ética da OAB).
2. **Colher na própria reunião tudo o que o Relatório de Triagem precisa.** A reunião é gravada e a transcrição
   entra em `python CONTRATACAO/main.py novo ...`, que monta o Relatório para o Gestor Jurídico. O que não for
   perguntado aqui vira lacuna (`gaps`) no relatório e atrasa a notificação ao banco.

> Regra do manual: "O Relatório de Triagem DEVE ser preenchido durante o atendimento, não após."
> Na prática: pergunte tudo em voz alta com a gravação ligada e preencha a tabela de operações (seção 4) enquanto conversa.

---

## 1. Antes da reunião (5 minutos)

- [ ] Ler o **Resumo para o Closer** gerado pelo SDR (`python COMERCIAL/main.py sdr "conversa.txt"`) e o histórico do lead no CRM.
- [ ] Anotar o que o SDR já sabe e o que falta (`FALTA SABER`) e os `SINAIS DE ALERTA` (ex.: pediu garantia, não é produtor).
- [ ] Conferir urgência: parcela vencida ou vencendo em 30 dias, execução, leilão, negativação → reunião no mesmo dia.
- [ ] Ter aberta a tabela de propostas do escritório (`COMERCIAL/config_comercial.py`, `PROPOSTAS`).
- [ ] Preparar a gravação (item 2) e a tabela de operações em branco (item 4.2).

## 2. Como gravar a reunião (obrigatório)

- **Pedir autorização no início, com a gravação já ligada**, para que o consentimento fique registrado:
  *"Seu Fulano, posso gravar nossa conversa? É só para o escritório não perder nenhum detalhe do seu caso;
  a gravação fica guardada com a gente e não é divulgada."* Se ele não autorizar: não gravar e anotar tudo por escrito.
- **Reunião por vídeo (Google Meet):** ativar **Gravação + Transcrição** (Atividades → Transcrições). Ao final, baixar a
  transcrição (Google Docs → baixar .docx ou .txt) ou a legenda (.srt).
- **Reunião por telefone/WhatsApp:** usar gravador no computador ou celular, com o viva-voz, e transcrever depois
  (a equipe pode mandar o áudio para transcrição). Nunca gravar sem avisar o cliente.
- **Presencial:** celular gravando sobre a mesa, com o mesmo aviso.
- Salvar como `TRANSCRICAO - NOME DO CLIENTE - DD-MM-AAAA.txt` (ou .pdf/.docx/.srt) e rodar
  `python CONTRATACAO/main.py novo "TRANSCRICAO.txt" "CNH.pdf" --cadastro CADASTRO.txt` (POP da fase de contratação).
- Falar em voz alta os números e datas que o cliente mostrar em papel ("então a cédula do Sicredi é de 900 mil,
  vence em 15 de agosto, certo?"). A IA só registra o que foi dito na gravação.
- **Senha GOV.BR nunca por mensagem escrita** e nunca falada na gravação: combinar ligação separada com o Estagiário.

## 3. Estrutura da reunião (30 a 45 minutos)

| Etapa | Tempo | Objetivo |
|---|---|---|
| 1. Abertura | 2 min | Apresentação, autorização da gravação, combinar a pauta |
| 2. Confirmar o que o SDR levantou | 3 min | Mostrar que o escritório ouviu; corrigir dados |
| 3. Diagnóstico (dores reais) | 15-20 min | Atividade, custos, produtividade, riscos, endividamento, avalistas, alienações, juros |
| 4. Apresentar a solução | 5-8 min | Explicar o caminho de forma consultiva, técnica e objetiva, sem promessa |
| 5. Proposta e objeções | 5-10 min | Honorários da tabela do escritório; tratar objeções com racionalidade |
| 6. Fechamento e próximos passos | 3 min | Contrato, documentos, onboarding em até 2 dias |

### Abertura (fala sugerida)
*"Seu Fulano, obrigado pelo tempo. Eu sou [nome], do Caldeira Advogados. A ideia de hoje é entender bem a sua
situação com os bancos, ver o que tem de documento e te explicar como o escritório trabalha. No fim eu te digo com
franqueza se é caso para a gente e quais são os caminhos. Pode ser?"*

---

## 4. Diagnóstico - o que perguntar (e por que)

Os itens com **(!)** são os que os bancos atacaram nas contestações quando faltaram (DNA, seção 4 e 7).

### 4.1 Produtor e atividade
- Nome completo, estado civil, profissão como aparece nos documentos (produtor rural, pecuarista...), município onde mora.
- Produz em nome próprio ou também por **empresa (CNPJ)**? As dívidas estão no nome de quem (PF, PJ, cônjuge)?
- Nome da propriedade (Fazenda/Sítio), município, **área total e área produtiva em hectares** (lavoura x pasto).
- Atividade: soja/milho (sacas/ha), gado de corte (cria, recria, engorda, ciclo completo), leite. Sistema (a pasto, confinado).
- **Rebanho hoje**: quantas cabeças e como é composto (matrizes, bezerros, bois). Vendeu matriz ou parte do rebanho para pagar banco?
- Há quantos anos é cliente/associado do banco ou da cooperativa? Sempre pagou em dia antes?
- Alguma situação pessoal grave (doença, incapacidade)? Tem laudo médico?

### 4.2 Operações - UMA LINHA POR CÉDULA, POR BANCO (preencher durante a conversa)

| # | Banco/cooperativa e agência (cidade) | Nº da cédula/operação | Tipo de título | Finalidade (declarada e real) | Fonte de recursos | Data e valor contratado | Saldo hoje | Vencimentos (parcelas) | Juros (a.m./a.a.), mora, multa | Garantias | Avalistas/fiadores | Situação | Já prorrogou? | Pedido administrativo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | | | | | |
| 2 | | | | | | | | | | | | | | |

Perguntas para cada linha:
- **Banco e agência** (cidade). Tem o e-mail da agência ou do gerente? (a notificação vai por e-mail oficial)
- **Número da cédula** e **tipo do título**: cédula de crédito rural (pignoratícia, hipotecária), CPR/CPR financeira,
  **CCB**, crédito pessoal, capital de giro, cheque especial, renegociação. **(!)** CCB, CPR financeira e cheque especial
  o banco diz que "não é crédito rural": perguntar **para que o dinheiro foi usado de verdade** (insumo, gado, máquina)
  e se há nota fiscal/GTA que prove.
- **Finalidade**: custeio (soja, pecuária), investimento (máquina, trator, plantadeira, calcário, animais), comercialização.
- **Fonte de recursos**: FNO (Banco da Amazônia), BNDES, Pronaf, Pronamp, recurso livre. **(!)** FNO tem regra própria.
- Data da contratação, **valor contratado**, **saldo atual**, **datas de vencimento de cada parcela**, quais pagou, quais atrasou.
- **Juros**: taxa ao mês ou ao ano, juros de mora, multa, se é Price ou SAC, tarifas e seguros cobrados.
  (A calculadora do escritório ajuda a mostrar ao cliente quanto ele paga de juros: `COMERCIAL/calculadora/index.html`.)
- **Garantias**: penhor da safra ou do rebanho, hipoteca da terra, alienação fiduciária de máquina.
- **Avalistas e fiadores**: nome de cada um (a proteção pedida ao juiz se estende a eles).
- Débito automático na conta? (a notificação pede a suspensão)
- **(!)** Essa operação **já foi prorrogada** antes? Quando?
- **(!)** O banco **ofereceu renegociação**? Em que condições (entrada exigida, prazo)? Foi aceita ou implementada?
- **(!)** Quais operações estão **em dia** e quais **vencidas**?
- **(!)** Já tem **execução**, protesto, nome negativado (Serasa/SPC/Registrato), busca e apreensão, bloqueio de conta,
  leilão marcado? Número do processo e cidade.
- Já teve **ação anterior** contra esse banco (com outro advogado ou com o escritório)?
- Tem **cópia de todas as cédulas e aditivos**? Se não tiver, o primeiro passo é a notificação pedindo os contratos.

### 4.3 Perdas - com MÊS e ANO (base do laudo de frustração de safra)
- O que aconteceu na propriedade e **quando** (mês/ano): seca/estiagem, calor forte, queimada, excesso de chuva,
  praga (lagarta, cigarrinha), doença, morte de animais (quantos), onça, enchente, estrada fechada.
- Houve decreto de emergência no município? Registro na EMATER, no IDARON, laudo, Proagro, seguro?
- **Produção esperada x obtida**: sacas por hectare esperadas e colhidas; cabeças/arrobas que ia vender e vendeu.
- **Preço esperado x obtido**: por saca, por arroba, por cabeça. **(!)** Projeção precisa ser realista
  (o banco já chamou de "surreal" uma expectativa de preço inflada).
- **Receita esperada x obtida** e aumento de custo (adubo, ração, sal mineral, diesel, suplementação).
- **(!)** O período da perda bate com o ciclo que a cédula financiou? (custeio de uma safra, venda prevista para quando?)
- Tem outra renda (arrendamento, frete, aluguel de máquina)? **(!)** O banco usa isso contra o pedido.
- Outros credores: revenda de insumo, cerealista, outros bancos (endividamento total).

### 4.4 Documentos que sustentam o caso (pedir e marcar quem tem)
- Cédulas e aditivos de todos os bancos; extratos; comprovantes de pagamento.
- Fotos da lavoura/pasto no período da perda.
- **Notas fiscais de venda**, **GTAs**, **extrato de movimentação do IDARON** (pecuária).
- **Declaração de Imposto de Renda dos últimos 3 anos** (e livro caixa, se tiver). **(!)** Os bancos pedem IDARON e IR.
- Matrícula do imóvel, CAR, CCIR, ITR.
- Laudos já feitos (agrônomo com ART e vistoria no local; os bancos atacam laudo sem isso).

### 4.5 Pedido ao banco e urgência
- Já pediu prorrogação ao banco **por escrito**? Quando, por qual canal, e o que o banco respondeu (com qual motivo)?
- **Quanto tempo falta para o próximo vencimento?** (quanto mais perto, mais urgente a notificação)

### 4.6 Capacidade de pagamento e condição financeira
- Quanto consegue pagar por ano, com a atividade normalizada? A partir de quando (ano de retomada)?
- Quanto de carência e quantos anos de prazo seriam viáveis para ele?
- Liquidez hoje (dinheiro disponível) x patrimônio (terra, gado, máquina). Receita bruta x lucro do último ano.
  (Serve para o pedido de justiça gratuita ou de custas ao final; o banco costuma impugnar.)

---

## 5. Apresentar a solução (consultiva, técnica e objetiva)

Explique o caminho em linguagem simples, **sem prometer resultado**:

1. **Levantamento**: o escritório reúne as cédulas de todos os bancos, os vencimentos e as provas da perda
   (laudo de frustração de safra e laudo financeiro).
2. **Pedido ao banco (notificação extrajudicial)**: pedido formal de prorrogação/alongamento, com os documentos,
   pedindo também a suspensão do débito automático e que o banco fale só com os advogados.
3. **Se o banco não atender**: ação na Justiça pedindo a prorrogação, com pedido urgente para suspender a cobrança e
   impedir a negativação do produtor e dos avalistas. Contra a Caixa, na Justiça Federal; contra os demais, na estadual.
4. **Se já existe execução**: defesa na própria execução (embargos) junto com o pedido de prorrogação.

Base que pode ser citada ao cliente (como o escritório usa nas peças): Manual de Crédito Rural, Capítulo 2, Seção 6,
item 4 (prorrogação quando há dificuldade temporária de pagamento por frustração de safra, dificuldade de
comercialização ou outras ocorrências prejudiciais) e Súmula 298 do STJ (o alongamento é direito do devedor nos termos
da lei, não favor do banco).

**Expectativa honesta** (DNA, seção 7.4): o juiz pode conceder prazo e carência menores do que o pedido; o banco
costuma recorrer; decisões variam por comarca. Falar isso **antes** de fechar evita cliente frustrado depois.

Pode dizer | Não pode dizer
---|---
"A lei prevê a prorrogação quando há frustração de safra comprovada; vamos juntar as provas do seu caso." | "A gente garante que o banco vai prorrogar."
"O escritório já atuou em vários casos como o seu na região." | "Ganhamos todas", "100% de êxito", "causa ganha".
"O prazo e a carência dependem do laudo e da decisão do juiz." | "Você vai ter 4 anos de carência e 10 de prazo."
"Os honorários são estes, conforme a tabela do escritório." | Dar desconto para "fechar hoje" com pressão; falar mal de outro advogado.

---

## 6. Proposta e fechamento

- Usar o **pacote sugerido** no resumo do SDR (Extrajudicial / Extrajudicial + Judicial / Embargos à execução /
  Previdenciário rural) e os valores da **tabela do escritório** (nunca abaixo da tabela de honorários da OAB/RO).
- Explicar entrada, parcelas e êxito com clareza; dizer que tudo vai no contrato.
- **Fechou**: confirmar dados para o contrato (telefone, e-mail, estado civil, profissão, endereço), pedir foto da
  CNH/RG e explicar os próximos passos:
  1. contrato, procuração e declaração chegam pelo WhatsApp para assinatura digital (ZapSign);
  2. o Estagiário pede a lista de documentos no dia seguinte;
  3. o Gestor Jurídico marca a reunião de onboarding em até 2 dias.

### Tratamento de objeções (com racionalidade)

| Objeção | Como responder |
|---|---|
| "Vocês garantem que dá certo?" | "Nenhum advogado sério pode garantir resultado. O que garantimos é o trabalho: pedido bem feito, com prova da perda e dentro dos prazos. Por isso o levantamento dos documentos é tão importante." |
| "Está caro." | Voltar ao tamanho do problema: saldo em jogo, risco de execução, garantia (terra, gado) e avalistas. Mostrar o que está incluído (levantamento, laudos orientados, notificação, ação e tutela). Oferecer a forma de pagamento da tabela; não reduzir abaixo do que o escritório autoriza. |
| "Vou pensar / falar com a esposa." | "Claro. Posso chamar ela agora para eu explicar junto?" (a esposa costuma ser avalista). Deixar data e hora do retorno marcadas e lembrar o próximo vencimento. |
| "O gerente disse que vai renegociar." | "Ótimo se ele formalizar. Pergunte por escrito as condições (entrada, juros, prazo). A renegociação oferecida pelo banco às vezes pede entrada alta ou juros maiores; o pedido de prorrogação mantém os encargos do contrato. Se quiser, analisamos a proposta dele antes de assinar." |
| "Tenho medo de o banco cortar meu crédito." | Reconhecer o medo. Explicar que o pedido é previsto nas regras do próprio crédito rural e que a ação pede para o banco não negativar o produtor e os avalistas enquanto o caso é discutido. Não prometer que o banco vai continuar emprestando. |
| "O banco disse que só dava para pedir antes do vencimento." | "Essa é a posição do banco. Nas peças, o escritório sustenta que o item 2.6.4 do Manual de Crédito Rural não fixa prazo fatal, e há decisões nesse sentido; cada caso é analisado." (Sem prometer.) |
| "Já está em execução, não tem mais jeito." | "Tem defesa na própria execução (embargos), com pedido de suspensão enquanto se discute a prorrogação. O prazo para isso corre: quanto antes, melhor." (Pedir número do processo e data da citação.) |
| "Não tenho as cédulas." | "Não é problema para começar: o primeiro passo pode ser a notificação pedindo ao banco a cópia de todos os contratos." |
| "E se eu perder?" | Explicar com franqueza o risco de custas e honorários do advogado do banco (sucumbência) e como a justiça gratuita ou as custas ao final são pedidas. |
| "Moro longe." | Atendimento todo pelo WhatsApp e por vídeo; assinatura digital; o escritório atua em várias comarcas de RO. |
| "Quero pagar só no êxito." | Seguir a tabela do escritório; se não houver essa modalidade, explicar por que há entrada (levantamento, laudos, notificação e ação começam já). |

---

## 7. Depois do "fechou" (no mesmo dia - manual do Closer)

- [ ] Preencher o `CADASTRO.txt` (modelo em `exemplos/CADASTRO_MODELO.txt`) com telefone, e-mail, estado civil,
      profissão, endereço, origem, data do contrato e honorários.
- [ ] Rodar `python CONTRATACAO/main.py novo "TRANSCRICAO..." "CNH..." --cadastro CADASTRO.txt`.
- [ ] Entregar o **contrato ao Financeiro** (sai o `RESUMO PARA O FINANCEIRO.txt`) e o **Relatório de Triagem ao Gestor Jurídico**.
- [ ] Registrar no CRM/ADVBOX: resultado da reunião (fechou / perdeu + motivo / retorno marcado). A auditoria semanal
      cobra isso (`auditoria-atendimento`, bloco "Fluxo não seguido").
- [ ] Se não fechou: registrar o **motivo da perda** e a data do retorno.

## 8. Cola de bolso (1 página)

1. Autorização da gravação. 2. Confirmar o resumo do SDR. 3. Atividade + área + rebanho.
4. Tabela de operações: banco, nº, tipo, finalidade, fonte, valor, saldo, vencimentos, juros, garantias, avalistas,
   situação, já prorrogou, proposta do banco, pedido administrativo. 5. Perdas com mês/ano; produção, preço e receita
   esperado x obtido. 6. Documentos: cédulas, notas, GTAs, IDARON, IR 3 anos, fotos, laudos. 7. Execução/negativação.
8. Capacidade de pagamento e prazo desejado. 9. Solução sem promessa. 10. Proposta da tabela, objeções, fechamento.
11. Cadastro + transcrição no sistema + contrato ao Financeiro + relatório ao Gestor.

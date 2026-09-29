# Comece aqui - Sistema de IA do Caldeira Advogados Associados

Bem-vindo(a). Este é o guia da equipe para usar o sistema no dia a dia. Não precisa saber programar:
você pede em português e a IA faz o trabalho repetitivo, deixando a decisão com você.

## O que é o sistema

Um conjunto de assistentes que acompanha o caso do produtor rural do começo ao fim, seguindo o fluxo do
escritório: **Fluxo inicial (SDR e Closer) -> 1 Onboarding -> 2 Formalização -> 3 Extrajudicial ->
4 Judicial -> 5 Acompanhamento -> 6 Finalização**.

- Gera o Relatório de Triagem, o contrato, a procuração e a declaração a partir da reunião do Closer.
- Envia para assinatura (ZapSign), cadastra no ADVBOX, cria a cobrança no Asaas e cobra os documentos pelo WhatsApp.
- Prepara notificações aos bancos, minutas de inicial e de recursos, sempre para revisão.
- Varre publicações, controla prazos, monta a pauta da semana e o relatório aos clientes.
- Cuida da régua de cobrança dos honorários, da inadimplência e do fechamento do mês.

Tudo roda na máquina do escritório (e, se o escritório quiser, numa VPS ligada 24 horas). Os dados dos
clientes ficam na pasta de clientes do escritório, nunca no repositório do sistema.

## Regra de ouro

1. **A IA não protocola e não envia nada ao banco.** Toda peça, notificação e relatório sai como minuta
   para revisão de uma pessoa da equipe.
2. **Estratégia:** a IA pode definir a estratégia em casos simples e padronizados e em petições de
   andamento. Nos demais casos, a decisão é do Gestor Jurídico ou do Coordenador.
3. **Nada inventado.** Se falta um dado, aparece `[CONFERIR]` ou `[PREENCHER]` em vermelho. Documento
   com essas marcas não vai para assinatura (o sistema trava).
4. **Senha GOV.BR do cliente nunca por mensagem escrita.** Só por ligação.
5. **Nada sai sozinho sem autorização:** envios só acontecem com a opção de enviar e com a chave
   configurada. Sem isso, o sistema só mostra o que faria.

## Como abrir no Claude Code

1. No computador do escritório, abra a pasta do sistema no **Claude Code** (no Terminal, dentro da pasta,
   digite `claude`; ou no VS Code: Arquivo > Abrir pasta, e abra o painel do Claude).
2. O Claude lê o `CLAUDE.md` e já sabe como o escritório trabalha, quais são os módulos e as regras.
3. Peça em português, como pediria a um colega. Para mandar um arquivo, arraste para a janela ou cole o
   caminho (ex.: `Z:\CLIENTES\AGRONEGOCIO\JOAO DA SILVA`).
4. Antes de qualquer envio (WhatsApp, ZapSign, Asaas), o Claude mostra o que vai sair e pede o seu ok.

## Exemplos de pedidos por cargo

**SDR**
- "Qualifica este lead e me sugere a próxima resposta: [cole a conversa do WhatsApp]"
- "Como foram as campanhas do Meta ontem? Quantos leads e quanto custou cada um?"

**Closer**
- "Fechei com o produtor. Aqui estão a transcrição da reunião, a CNH e a cédula do banco: gera a triagem e os documentos."
- "Abre a calculadora para eu usar na reunião."
- "O cadastro do cliente está completo para gerar a cobrança no Asaas?"

**Gestor Jurídico**
- "Qual a situação dos casos em contratação? Algum prazo vencendo?"
- "Lê o Relatório de Triagem do cliente João da Silva e me resume os gatilhos de gravidade alta."
- "Me dá a pauta da semana." / "Quais são os gargalos do escritório hoje?"

**Coordenador Jurídico**
- "Roda a varredura de publicações de hoje e me mostra os prazos que abriram."
- "Quais processos estão parados há mais de 60 dias?"
- "Gera o relatório quinzenal dos clientes para eu revisar antes de enviar."
- "Faz o checklist de encerramento do caso da pasta do João da Silva."

**Advogado(a) Extrajudicial**
- "Gera a notificação extrajudicial do cliente João da Silva para o Banco do Brasil."
- "Quais bancos já passaram do prazo de resposta?"
- "Registra que o banco respondeu hoje e resume a resposta."

**Advogado(a) Judicial**
- "Confere o checklist da inicial do cliente João da Silva: o que falta?"
- "Faz a minuta da inicial de prorrogação compulsória do João da Silva."
- "Prepara um agravo contra a decisão que está na pasta 20 JUDICIAL do cliente."

**Estagiário(a)**
- "Envia os documentos do João da Silva para assinatura." (só depois de revisados)
- "Quem ainda não mandou os documentos do checklist?"
- "Guarda estes arquivos que o cliente mandou na pasta certa."

**Financeiro**
- "Mostra o que a régua de cobrança vai mandar hoje." (só simula)
- "Quem está com honorário vencido? Quero a planilha."
- "Faz o fechamento de setembro." / "Tem contrato novo sem cobrança no Asaas?"
- "Coloca o cliente Fulano na lista de quem não recebe cobrança automática."

Se preferir o comando direto, cada pedido corresponde a um comando: veja `docs/MAPA_DO_SISTEMA.md`.

## Rotinas automáticas (rodam sozinhas)

| Quando | O que roda |
|---|---|
| todo dia 7h / 7h30 | resultado das campanhas; varredura de publicações e prazos |
| todo dia 8h30 | acompanhamento das notificações aos bancos |
| todo dia 9h, 13h e 17h | assinaturas e cobrança de documentos da contratação |
| segunda a sexta 10h | régua de cobrança dos honorários |
| segunda a sexta 18h | contratos novos sem cobrança no Asaas |
| segunda 7h e 8h | pauta da semana; relatório de inadimplência |
| sexta 15h e 16h | auditoria do atendimento; auditoria da semana |
| dias 1 e 16 | relatório aos clientes (só gera; envio depois da revisão) |
| dia 1 / dia 5 | radar mensal / fechamento do mês anterior |

Agenda completa e o que cada uma manda (ou não) para o cliente: `docs/MAPA_DO_SISTEMA.md`.

## Onde ver os resultados

- **Documentos do cliente:** na pasta do cliente (`AGRONEGOCIO/NOME DO CLIENTE/`): triagem, contrato,
  procuração, notificações, minutas.
- **Relatórios:** pasta `SAIDA/` do sistema, uma subpasta por módulo (ex.: `SAIDA/FINANCEIRO/FECHAMENTO/`).
- **O que cada rotina fez:** pasta `logs/` (um arquivo por rotina). Pode pedir ao Claude:
  "o que a cobrança mandou hoje?" ou "por que a rotina da contratação deu erro?".

## Quando algo não funciona

1. Peça ao Claude: "confere a saúde do sistema" (roda `python deploy/vps/healthcheck.py --sem-aviso`).
2. "VAZIO" = falta a chave no `config/.env` (a etapa está em modo seguro). "FALHA" = a chave existe mas
   o serviço não respondeu (senha trocada, sistema fora do ar).
3. Na máquina do escritório: `deploy\instalar_windows.bat /checar` mostra o que está instalado e o que falta.
4. Se estiver configurado, o número de `ALERTA_WHATSAPP` recebe aviso quando alguma integração cai.

## Para quem instala

```
deploy\instalar_windows.bat            (instala; depois preencher config\.env)
deploy\instalar_windows.bat /checar    (confere sem mudar nada)
deploy\agendar_tarefas_windows.bat     (agenda as rotinas; como administrador)
```
VPS 24 horas (bônus): `docs/DEPLOY_VPS.md`. As rotinas ficam **ou** no Windows **ou** na VPS, nunca nos dois.

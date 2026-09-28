# Caldeira Advogados Associados - Central de Automacoes

> Escritorio: **Caldeira Advogados Associados** (CNPJ 51.038.631/0001-30), Cacoal/RO.
> Titular: **Dr. Augusto Alves Caldeira (OAB/RO 11.101)**. Tambem assina pecas: Dra. Lorena Gois Fontenele (OAB/RO 14.429).
> Coordenador Juridico: Dr. Willian. Central (69) 99348-3443.
> Nicho: **defesa do produtor rural contra bancos e cooperativas de credito** (prorrogacao e alongamento
> compulsorio de divida rural, tutela de urgencia, embargos a execucao). Tambem faz previdenciario (salario-maternidade, BPC).
> Ja usa: ADVBOX, Asaas, ZapSign, Atende Direito (WhatsApp), servidor interno + Google Drive.

## Regra de ouro
- **A IA nao protocola e nao envia nada ao banco.** Toda peca e todo relatorio saem para revisao humana.
- Resposta do escritorio no briefing (28/09/2026): a IA **pode definir a estrategia em casos simples e padronizados
  e em peticoes de andamento**; nos demais, a decisao e do Gestor Juridico / Coordenador.
- Nunca inventar dado de cliente, banco, valor, data ou jurisprudencia. Sem dado: `[CONFERIR]` / `[PREENCHER]`.
- Documento com `[CONFERIR]` ou `[PREENCHER]` **nunca** vai para assinatura (trava no codigo).
- Senha GOV.BR do cliente nunca por mensagem escrita.

## Fluxo do servico (manual de funcoes do escritorio)
Fluxo inicial (SDR -> Closer fecha) -> 1 Onboarding -> 2 Formalizacao -> 3 Extrajudicial -> 4 Judicial ->
5 Acompanhamento -> 6 Finalizacao. Prazo interno: notificacao em ate 15 dias do onboarding; inicial em ate
60 dias do contrato (proposto reduzir para 5 e 15 dias; ajustar em `config/escritorio.py`).

## Modulo 1: FASE DE CONTRATACAO (CONTRATACAO/)
Cobre: Closer fecha -> Relatorio de Triagem ao Gestor -> onboarding (bancos, cedulas, vencimentos, linha do tempo)
-> procuracao + declaracao + contrato -> ZapSign -> ADVBOX -> pasta no servidor -> cobranca dos documentos.

```
python CONTRATACAO/main.py novo "TRANSCRICAO.pdf" "CNH.pdf" "CEDULA.pdf" --cadastro CADASTRO.txt
python CONTRATACAO/main.py enviar "PASTA DO CLIENTE" [--criar-tarefas]
python CONTRATACAO/main.py acompanhar [--enviar]     # agendado 3x/dia (deploy/)
python CONTRATACAO/main.py painel
python CONTRATACAO/main.py exemplo                   # caso ficticio, nao envia nada
```
POP completo: `docs/POP_FASE_CONTRATACAO.md`. Campos dos modelos: `docs/CAMPOS_DOS_MODELOS.md`.

## Onde mexer
| O que | Arquivo |
|---|---|
| Nome, endereco, advogados da procuracao, prazos, checklist, pastas | `config/escritorio.py` |
| Cargos -> usuarios do ADVBOX, tarefas abertas | `config/equipe.py` |
| Modelos de contrato/procuracao/declaracao | `DOCS_MODELOS/*.docx` (hoje PROVISORIOS - travam o envio) |
| Teses, foro, estilo das pecas (a IA le isso na triagem) | `BASE_CONHECIMENTO/DNA_PECAS.md` |
| Credenciais | `config/.env` (copiar de `.env.example`; nunca versionar) |

## Padrao de pecas (tirado das pecas reais)
Times New Roman 12, justificado, espacamento 1,5, titulos e nomes das partes em laranja #C45911,
timbrado com logo CALDEIRA no topo, marca d'agua e rodape com contatos (`config/timbrado_modelo.docx`).
Acao carro-chefe: "Acao Mandamental de Prorrogacao Compulsoria de Divida Rural com Pedido de Tutela Provisoria
Antecipada em Carater de Urgencia" (Sumula 298/STJ + MCR 2.6.4). Justica Federal so contra a Caixa.

## Tarefas no ADVBOX
Endpoint `/posts`; campo de texto `comments`; remetente = cargo em `config/equipe.py`.
Nunca criar tarefa sem `--criar-tarefas` explicito.

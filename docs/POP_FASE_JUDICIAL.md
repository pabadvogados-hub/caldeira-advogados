# POP - Fase Judicial (Caldeira Advogados Associados)

Da notificacao sem acordo ate o protocolo da inicial e as pecas seguintes (agravo, replica, embargos,
contrarrazoes, peticoes de andamento). Espelha a etapa "4 Fase Judicial" do FLUXO DO SERVICO do escritorio
e mostra o que a automacao faz e o que continua com cada cargo.

## Visao geral

| Etapa do manual | Quem era | O que a automacao faz | O que continua humano |
|---|---|---|---|
| Gestor transfere o caso ao Adv. Judicial | Gestor Juridico | - | Transferir no ADVBOX |
| Verificar notificacao, resposta/ausencia do banco, laudos (safra com ART e vistoria + financeiro), documentos | Adv. Judicial | **Checklist pre-protocolo**: BLOQUEIA / ATENCAO / OK lendo o `caso.json` e a pasta; alerta o prazo de 60 dias; aponta os pontos que os bancos atacam (DNA secao 7) | Conferir o que o robo nao ve (ex.: ART assinada, laudo por operacao) |
| Faltou documento: aciona o Estagiario | Adv. Judicial | `PEDIDO AO ESTAGIARIO - data.txt` com o que falta e a pasta onde salvar | Estagiario pede ao cliente e salva; rodar o checklist de novo |
| Elaborar a inicial (tutela, suspensao da exigibilidade, nao negativacao do cliente e avalistas) | Adv. Judicial | **Minuta completa no timbrado** (.docx + .pdf) seguindo o esqueleto real do escritorio, com os dados do caso, o texto das cedulas/laudos e o banco de teses (DNA); foro sugerido; valor da causa somado; citacoes conferidas contra o DNA | Revisar, completar o que esta em vermelho, colar as imagens (decretos, tabelas do laudo) |
| Coordenador supervisiona e decide gratuidade, comarca, acordo | Coordenador Juridico | Marca `[CONFERIR]` no foro e deixa o pedido de gratuidade com o subsidiario (custas ao final / 8 parcelas) | Decidir |
| Protocolar no PJe/E-Saj e despachar com o juiz | Adv. Judicial | - (a IA nao protocola) | Protocolar e despachar |
| Liminar concedida: avisar cliente e acompanhar cumprimento | Adv. Judicial | `manifestacao` para informar descumprimento e pedir multa | Avisar o cliente; conferir SERASA/Registrato |
| Liminar negada: analisar agravo com o Coordenador | Adv. Judicial + Coordenador | **Agravo de instrumento pronto** (TJRO, ou TRF1 se Caixa) a partir da decisao | Decidir se agrava; revisar; protocolar no prazo |
| Contestacao do banco | Adv. Judicial | **Replica** rebatendo ponto a ponto com a tabela "banco alega x escritorio rebate" | Revisar |
| Banco executou | Adv. Judicial | **Embargos a execucao** com efeito suspensivo e prejudicialidade externa | Revisar; calcular excesso |
| Apelacao do banco | Adv. Judicial | **Contrarrazoes** | Revisar |

## Passo a passo

1. **Checklist.** `python JUDICIAL/main.py checklist "PASTA DO CLIENTE"` (ou `--banco NOME`).
   - Le `00 CONTRATACAO/caso.json` (qualificacao, operacoes da triagem, `extrajudicial`, `prazos`) e todos os arquivos
     da pasta (procuracao assinada, declaracao, cedulas por banco, extratos, comprovantes, matricula, notas fiscais,
     IR, GTA/IDARON, laudos, notificacoes e respostas em `10 EXTRAJUDICIAL`).
   - Gera em `20 JUDICIAL/`: `... - Checklist Pre-Protocolo - data.docx/.pdf` e `PEDIDO AO ESTAGIARIO - data.txt`.
   - BLOQUEIA: procuracao assinada, qualificacao (nome/CPF), cedulas de cada banco, laudo de frustracao de safra,
     laudo financeiro/capacidade de pagamento, notificacao ao banco. ATENCAO: o resto e os pontos fracos.
2. **Inicial.** `python JUDICIAL/main.py inicial "PASTA" --banco "NOME" [--revisional] [--federal]`.
   Uma acao por banco. Caixa = Justica Federal automaticamente. Leva alguns minutos.
   - Cabecalho fixo (enderecamento sugerido, qualificacao do autor tirada do caso, titulo) e fecho fixo
     (intimacoes em nome dos advogados, valor da causa por extenso, aviso de revisao, fecho, assinaturas) sao
     escritos pelo sistema; a IA escreve do reu aos pedidos.
   - Saida: `20 JUDICIAL/Nome - Inicial Mandamental - Banco - data.docx` + `.pdf`, e o texto em
     `20 JUDICIAL/_texto_ia/` (para refazer o .docx sem nova chamada de IA).
3. **Revisao.** Tudo em vermelho precisa sumir antes do protocolo: `[PREENCHER ...]` (dado que falta),
   `[CONFERIR ...]` (foro, valores aproximados, citacao fora do DNA, divergencias que o DNA aponta) e o aviso
   "PRONTA PARA REVISAO DO(A) ADVOGADO(A) RESPONSAVEL". Colar as imagens nos `@@ [PREENCHER: IMAGEM ...]`.
   Corrigir no Word ou no .md e rodar `python JUDICIAL/main.py docx "arquivo.md"`.
   Se a automacao for atualizada (regras de conferencia, cabecalho), refazer sem nova chamada de IA:
   `python JUDICIAL/main.py inicial "PASTA" --banco "NOME" --resposta "20 JUDICIAL/_texto_ia/... - resposta bruta da IA.txt"`.
   Ver o que seria enviado a IA, sem gastar: `--simular`.
4. **Protocolo** no PJe/E-Saj pelo advogado. Registrar no ADVBOX.
5. **Depois do protocolo** (cada uma com o documento do processo):
   - `agravo "PASTA" --decisao DECISAO.pdf` (liminar negada; prazo de 15 dias uteis)
   - `replica "PASTA" --contestacao CONTESTACAO.pdf`
   - `embargos "PASTA" --execucao EXECUCAO.pdf`
   - `contrarrazoes "PASTA" --recurso APELACAO.pdf`
   - `manifestacao "PASTA" --instrucao "informar descumprimento da liminar..." [--documento PRINT.pdf]`
   O documento-base e copiado para `20 JUDICIAL/`. A ultima minuta de inicial do caso vai junto como contexto.
6. **Consulta:** `python JUDICIAL/main.py pecas "PASTA"` lista as pecas geradas, pendencias e a etapa.

## Registro no caso.json
- `judicial`: lista de pecas `{tipo, arquivo, pdf, banco, gerada_em, pendencias, citacoes_marcadas, texto_marcado}`.
- `judicial_checklist`: ultimo checklist (contagem e pendencias).
- `etapa`: `JUDICIAL - CHECKLIST COM PENDENCIAS` / `JUDICIAL - PRONTO PARA A INICIAL` / `JUDICIAL - INICIAL EM REVISAO` /
  `JUDICIAL - AGRAVO EM REVISAO` / `JUDICIAL - REPLICA EM REVISAO` / `JUDICIAL - EMBARGOS EM REVISAO` /
  `JUDICIAL - CONTRARRAZOES EM REVISAO`.

## Prazos
| Marco | Regra | Responsavel |
|---|---|---|
| Protocolo da inicial | contrato + 60 dias (`config/escritorio.py`) | Adv. Judicial / Coordenador |
| Alerta no checklist | 10 dias antes, e VENCIDO depois | Adv. Judicial |
| Silencio do banco = recusa tacita | 10 dias apos a notificacao (padrao do escritorio: ajuizar 2 a 4 semanas depois) | Adv. Judicial |
| Agravo de instrumento | 15 dias uteis da intimacao | Adv. Judicial + Coordenador |
| Replica | 15 dias uteis da intimacao | Adv. Judicial |
| Embargos a execucao | 15 dias uteis da juntada do mandado de citacao | Adv. Judicial |

## Travas de seguranca
- A IA nao protocola, nao envia nada ao banco nem ao cliente.
- Jurisprudencia so do `BASE_CONHECIMENTO/DNA_PECAS.md`. A conferencia automatica marca `[CONFERIR]` em todo julgado,
  sumula ou tema fora do DNA e dos documentos do caso, e nas divergencias que o proprio DNA aponta.
- Dado faltante vira `[PREENCHER ...]`; valor da causa so e somado quando todas as operacoes tem valor.
- Toda peca sai com "PRONTA PARA REVISAO DO(A) ADVOGADO(A) RESPONSAVEL" em vermelho antes do fecho.
- Esqueletos em `BASE_CONHECIMENTO/ESQUELETOS/` sao genericos (sem dado de cliente). O de agravo nao veio de peca real
  do escritorio: revisar com o Coordenador na primeira vez.
- Cor: inicial com laranja (como as iniciais do escritorio); replica, embargos, contrarrazoes e andamento em preto
  (como as pecas reais). Trocar em `JUDICIAL/pecas.py` (TIPOS -> perfil) se o escritorio preferir.

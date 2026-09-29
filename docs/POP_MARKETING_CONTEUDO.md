# POP - Marketing: Produção de Conteúdo (Caldeira Advogados Associados)

Produção de conteúdo do Instagram (@caldeira.advogados) **sem agência**: a IA monta o calendário, escreve os posts
e desenha as artes; a responsável pelo marketing organiza e agenda; **o advogado revisa e aprova antes de publicar**.

Comandos: `python MARKETING/conteudo.py <comando>` na pasta do sistema (ajuda: `python MARKETING/conteudo.py -h`).
Identidade visual e tom de voz: `docs/GUIA_IDENTIDADE_VISUAL.md`.

## Regras que não mudam

1. **Nada é publicado automaticamente.** O sistema só gera material para revisão (TXT, DOCX, PNG, CSV, HTML).
2. **Todo texto passa pelo verificador de conformidade** (Código de Ética da OAB e Provimento 205/2021):
   - **BLOQUEIA** → o material sai marcado `NÃO PUBLICAR ATÉ CORRIGIR` (arquivos com prefixo `NAO_PUBLICAR_` e faixa
     vermelha nas artes). Corrigir e conferir de novo.
   - **ATENÇÃO** → ler o alerta e decidir com o advogado.
   - **Sem alerta** não é aprovação: o verificador procura palavras; quem aprova é o advogado.
3. Conteúdo **informativo e educativo**. Nunca: promessa ou garantia de resultado, preço, honorários, desconto,
   "consulta grátis", "o melhor", "o único", comparação com colegas, medo exagerado, urgência apelativa, ataque a banco,
   caso ou resultado de cliente, número de processo, quantidade de clientes, depoimento.
4. **Nunca inventar dado** (estatística, valor, data, julgado). O que a IA não tem certeza sai com `[CONFERIR: ...]`,
   e isso bloqueia a publicação até alguém conferir.
5. Só as teses do escritório (`BASE_CONHECIMENTO/DNA_PECAS.md`, resumidas no `MARKETING/conteudo.py`), em linguagem do
   produtor. Nenhuma imagem gerada por IA: artes só com texto, formas e logo; fotos sempre reais.

## Rotina

| Quando | Quem | Comando / ação | Resultado |
|---|---|---|---|
| Dia 1 a 3 do mês | Marketing | `python MARKETING/conteudo.py calendario --mes MM/AAAA` | Calendário do mês (DOCX no timbrado, CSV, HTML) em `SAIDA/marketing/calendario/` |
| Dia 1 a 3 do mês | Advogado + Marketing | Ler o calendário (15 min), trocar temas se quiser | Calendário aprovado |
| Segunda de manhã | Marketing | Para cada post da semana: copiar o comando da coluna "Comando para gerar" do CSV | Posts em `SAIDA/marketing/posts/` |
| Segunda à tarde | Advogado | Ler `POST_revisao.docx` e a `PRANCHA_revisao.png` de cada post; assinar a aprovação | Posts aprovados ou devolvidos |
| Terça | Marketing | Corrigir o que voltou, rodar `conferir` no texto final, agendar no Meta Business Suite | Semana agendada |
| Todo dia (10 min) | Marketing | Stories do calendário; ler comentários e direct | Interação |
| Quando surgir pergunta nova no atendimento | Marketing / SDR | Anotar em `MARKETING/exemplos/CONTEUDO_PERGUNTAS_PRODUTOR.txt` (sem nome nem dado pessoal) | Banco de pautas vivo |
| Quando faltar pauta | Marketing | `python MARKETING/conteudo.py ideias --quantidade 20` | 20 pautas prontas |
| 1 vez por mês | Marketing | Coletar anúncios de outros escritórios e rodar `concorrentes` | Ângulos e 5 variações éticas |

Ritmo recomendado: **3 posts por semana no feed** (carrossel, reels, estático, alternados) **+ 2 stories**.
Pilares alternados automaticamente: direitos do produtor na dívida rural, frustração de safra, negativação/execução e
avalista, documentos que o produtor deve guardar, bastidores do escritório e, ocasionalmente, previdenciário rural.

## Comandos

```
# Calendário editorial do mês (padrão: 3 posts/semana + 2 stories)
python MARKETING/conteudo.py calendario --mes 10/2026 [--posts-semana 3] [--stories-semana 2] [--sem-ia]

# Post pronto + legenda + hashtags (+ artes PNG com --arte)
python MARKETING/conteudo.py post --tema "Estiagem quebrou a safra: o que a norma prevê" --formato carrossel --arte
python MARKETING/conteudo.py post --tema "Avalista: o que acontece com quem assinou junto" --formato reels
python MARKETING/conteudo.py post --tema "..." --formato estatico --arte [--fundo claro|escuro]
python MARKETING/conteudo.py post --tema "..." --formato story --arte
   opções: --pilar direitos_divida|frustracao_safra|negativacao_avalista|documentos|bastidores|previdenciario
           --mes 7 (gancho sazonal de outro mês)   --contexto "saiu decreto de estiagem esta semana"   --sem-ia

# Conferir um texto escrito à mão (legenda, roteiro, texto de anúncio)
python MARKETING/conteudo.py conferir legenda.txt        (ou --texto "..." ; --exemplo para ver funcionando)

# Concorrentes: textos colados num .txt, um anúncio por bloco separado por uma linha ---
python MARKETING/conteudo.py concorrentes anuncios.txt [--sem-ia]      (--exemplo para ver funcionando)

# Banco de pautas (perguntas frequentes do produtor)
python MARKETING/conteudo.py ideias --quantidade 20 [--sem-ia]

# Calendário do produtor (plantio, colheita, seca, vencimentos) de um mês
python MARKETING/conteudo.py agro --mes 7

# Teste visual das artes, sem IA
python MARKETING/arte.py --demo [--tema escuro]
```

`--sem-ia` não gasta nada: o calendário e as ideias saem do banco de pautas + calendário do produtor; o post sai como
**esqueleto** com `[PREENCHER]` (bloqueado até ser completado à mão).

## O que sai de cada post (`SAIDA/marketing/posts/AAAAMMDD_HHMM_formato_tema/`)

| Arquivo | Para quê |
|---|---|
| `POST.txt` | Tudo para copiar: slides ou roteiro, legenda pronta (com aviso informativo, identificação do escritório e do advogado e hashtags), pontos para o revisor e o relatório de conformidade |
| `POST_revisao.docx` | Mesmo conteúdo no timbrado, com tabela de alertas e campo de aprovação do advogado |
| `artes/slide_01.png ...` | Artes 1080x1350 (story 1080x1920) para subir no Instagram |
| `artes/PRANCHA_revisao.png` | Todas as artes numa folha só, para o advogado revisar de uma vez |
| `post.json` | Registro completo (histórico) |

Reels não tem arte: grave seguindo o roteiro (gancho de 3 segundos, falas, cenas, texto na tela). Use legenda
automática do Instagram no vídeo.

## Checklist antes de publicar (o advogado assina)

- [ ] Conformidade sem **BLOQUEIA**; alertas de **ATENÇÃO** lidos e resolvidos.
- [ ] Nenhum `[CONFERIR]` ou `[PREENCHER]` no texto nem na arte.
- [ ] Norma ou julgado citado confere com a fonte (Súmula 298/STJ, MCR 2.6.4 etc.); nada inventado.
- [ ] Direito sempre condicionado ("a norma prevê", "depende dos requisitos e das provas").
- [ ] Sem preço, gratuidade, promessa, autoelogio, comparação, medo exagerado ou ataque a banco/cooperativa.
- [ ] Nenhum cliente identificável (nome, foto, documento, número de processo, cidade + detalhe do caso).
- [ ] Foto real e autorizada por escrito por quem aparece. Nada de imagem gerada por IA.
- [ ] Legenda termina com a identificação do escritório e do advogado responsável (já vem pronta).

## Comentários e direct

- Responder em termos gerais e com educação; **não dar parecer sobre o caso da pessoa** em comentário ou direct.
- Quem quiser atendimento: "Vamos conversar pelo WhatsApp do escritório" → segue o fluxo do SDR (`docs/POP_COMERCIAL.md`).
- Nunca procurar ativamente quem comentou em perfil de outro escritório ou de banco (captação indevida).
- Crítica ou reclamação: não discutir em público; avisar o advogado.

## Concorrentes (Biblioteca de Anúncios do Meta)

A API da Biblioteca de Anúncios do Meta só entrega anúncios de **temas sociais, eleições ou política** (e anúncios
exibidos na União Europeia). **Anúncios comerciais no Brasil não saem pela API.** Coleta manual:
1. Abrir `facebook.com/ads/library`, país **Brasil**, categoria **Todos os anúncios**.
2. Pesquisar o nome da página ou palavras como "dívida rural", "prorrogação", "crédito rural".
3. Copiar o texto de cada anúncio para um `.txt`, separando com uma linha `---` (modelo:
   `MARKETING/exemplos/CONTEUDO_CONCORRENTES_EXEMPLO.txt`).
4. `python MARKETING/conteudo.py concorrentes anuncios.txt` → ângulos, ganchos, formatos, promessas que violam o
   Provimento (a não copiar) e 5 variações próprias e éticas, com o comando para gerar cada uma.

O relatório é de **uso interno**: nunca citar concorrente em post, nunca copiar frase.

## Indicadores (ver toda segunda)

| Indicador | Onde ver | Para quê |
|---|---|---|
| Salvamentos e compartilhamentos por post | Instagram (Insights) | Mede se o conteúdo foi útil (o que mais importa) |
| Alcance de não seguidores | Instagram (Insights) | Mede se o conteúdo está chegando a produtores novos |
| Conversas iniciadas no WhatsApp | `python COMERCIAL/main.py auditoria-atendimento --dias 7` | Liga conteúdo a atendimento |
| Posts publicados x planejados | Calendário do mês | Constância |
| Temas que mais geraram perguntas | Comentários e direct | Entram no arquivo de perguntas → novas pautas |

## Configuração (`config/.env`)

```
ANTHROPIC_API_KEY=         # obrigatória para os modos com IA (sem ela, tudo roda como --sem-ia)
MODELO_MARKETING=          # opcional; padrão = MODELO_EXTRACAO ou claude-sonnet-5
```

Fontes da marca (opcional): colocar `titulo.ttf`, `corpo.ttf` e `corpo_negrito.ttf` em `config/fontes/`; sem elas, as
artes usam Georgia (títulos) e Segoe UI (texto) no Windows, ou DejaVu/Liberation no Linux.

**Agendar o calendário no Windows** (dia 1, 7h; ajustar caminhos):
```
schtasks /Create /TN "Caldeira Calendario conteudo" /SC MONTHLY /D 1 /ST 07:00 /TR "cmd /c cd /d C:\CALDEIRA_ADVOGADOS && python MARKETING\conteudo.py calendario --mes %date:~3,7%"
```
(conferir o formato de data do Windows da máquina; se preferir, rodar à mão no dia 1.)

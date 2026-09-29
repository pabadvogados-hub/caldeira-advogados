# Guia de Identidade Visual e Tom de Voz - Caldeira Advogados Associados

Referência para quem produz e revisa o conteúdo do Instagram (@caldeira.advogados) e das artes geradas por
`MARKETING/arte.py`. Tirado do timbrado e das peças do escritório. Pontos a confirmar com o escritório estão marcados
**[CONFERIR]**.

## 1. Cores

| Cor | Hex | Onde usar |
|---|---|---|
| Laranja Caldeira | `#C45911` | Destaques, barras, numeração dos slides, fundo do slide de fechamento. É a cor dos títulos das peças do escritório. |
| Grafite | `#20201F` | Fundo da capa do carrossel e dos estáticos; texto principal sobre fundo claro. |
| Papel | `#FBF8F4` | Fundo claro dos slides do meio. |
| Laranja claro (só texto em fundo escuro) | `#EA8A4E` | Palavra destacada sobre o grafite. O laranja `#C45911` sobre grafite tem contraste baixo para texto (cerca de 2,8:1); o tom claro chega a cerca de 6:1. |
| Branco | `#FFFFFF` | Texto sobre o laranja (contraste cerca de 5,9:1). |
| Cinza quente | `#857D75` (claro) / `#A39B92` (escuro) | Rodapé, @ do perfil, numeração secundária. |

Regras: no máximo **uma** cor de destaque por peça (o laranja). Nada de degradê, neon, sombra pesada ou cores de
outras marcas. Vermelho `#B3261E` só aparece na faixa interna "NÃO PUBLICAR ATÉ CORRIGIR" e nunca vai ao ar.

## 2. Logo

- Arquivo: `config/logo_caldeira.png` (monograma + "CALDEIRA ADVOGADOS").
- As artes geram três versões sozinhas: **normal** (fundo claro), **clara** (letras em tom creme, para o grafite) e
  **branca** (sobre o laranja). Não recolorir de outro jeito, não distorcer, não girar, não aplicar sobre foto poluída.
- Posição: canto superior direito nos slides; canto superior esquerdo no slide de fechamento. Largura de 140 a 170 px
  numa arte de 1080 px, com respiro de pelo menos a altura do monograma em volta.
- O PNG atual tem 210 px de largura: serve para as artes do Instagram. **[CONFERIR]** pedir ao escritório o logo em
  vetor (SVG/PDF) ou PNG grande com fundo transparente para impressos e capas de vídeo.

## 3. Tipografia

| Uso | Fonte nas artes | Reserva (Linux/VPS) |
|---|---|---|
| Títulos | Georgia Bold (serifa, conversa com o logo e com o timbrado das peças) | DejaVu Serif Bold / Liberation Serif Bold |
| Texto | Segoe UI | DejaVu Sans / Liberation Sans / Noto Sans |
| Texto em negrito e destaques | Segoe UI Bold | DejaVu Sans Bold / Liberation Sans Bold |

- Peças jurídicas continuam em Times New Roman 12 (timbrado); isso não muda.
- **[CONFERIR]** se o escritório tem fontes oficiais da marca. Se tiver, colocar os arquivos em `config/fontes/` com os
  nomes `titulo.ttf`, `corpo.ttf` e `corpo_negrito.ttf`: as artes passam a usar essas fontes sem mudar código.
- Tamanhos nas artes (1080 px): título do slide 42 a 72 px, texto 30 a 52 px (a fonte diminui sozinha até caber;
  se não couber no mínimo, o texto é cortado e o relatório avisa para encurtar). Nunca menor que 30 px.

## 4. Formatos e grade

| Formato | Tamanho | Estrutura |
|---|---|---|
| Carrossel | 1080 x 1350 (4:5), 7 a 9 slides | Capa grafite (etiqueta do tema, título grande, subtítulo) → miolo claro ou escuro (número do slide, barra laranja, título, texto ou lista) → fechamento laranja (chamada ética, aviso informativo, identificação do escritório e do advogado) |
| Estático | 1080 x 1350 | Etiqueta, título grande, barra laranja, texto de apoio, chamada, identificação |
| Story | 1080 x 1920 (9:16) | Bloco centralizado; 250 px no topo e 330 px na base ficam livres para a interface do Instagram; caixa marcando onde entra a figurinha (enquete, teste) |
| Reels | vídeo 9:16, 30 a 60 s | Gancho nos 3 primeiros segundos, texto na tela curto, legenda automática ligada |

Margem lateral de 96 px. Conteúdo importante longe das bordas (o Instagram corta a miniatura do perfil).
Uma ideia por slide. Lista com no máximo 5 itens.

## 5. Fotos e vídeos

- **Sempre reais**: equipe no escritório, advogado explicando para a câmera, paisagem da região (lavoura, pasto,
  estrada vicinal), papéis sobre a mesa **sem dados pessoais**.
- **Nunca** imagem gerada por IA, banco de imagem com cara de estrangeiro, foto de cliente, documento com nome/CPF,
  fachada de agência bancária com a marca do banco em tom de ataque.
- Quem aparece assina autorização de uso de imagem. Cliente não aparece (mesmo com autorização, evitar: vira caso
  concreto).
- **[CONFERIR]** pendência: fazer uma sessão de fotos da equipe e do escritório (retratos, equipe trabalhando,
  reunião, detalhes) para ter banco próprio de imagens.

## 6. Tom de voz

O escritório fala com o produtor como quem conhece a lida: **direto, respeitoso, sem juridiquês, sóbrio**.

| Diga | Evite |
|---|---|
| "A norma prevê a prorrogação quando o produtor comprova..." | "Você tem direito garantido à prorrogação!" |
| "Cada caso depende da análise dos contratos e das provas." | "Resolvemos sua dívida." |
| "Cédula de crédito rural, o contrato do financiamento" | "Título executivo extrajudicial" sem explicar |
| "Ficou com dúvida? Converse com a equipe do escritório." | "Chame agora!", "Link na bio e garanta já" |
| "A seca afetou a lavoura? Registre datas e fotos." | "O banco vai tomar sua fazenda!" |
| "O banco não respondeu ao pedido escrito" | "Banco ladrão", "golpe do banco" |
| "Atuação em crédito rural e agronegócio" | "Especialista" (sem título certificado), "o melhor", "o único", "número 1" |

Exemplos da lida funcionam: soja, milho safrinha, pasto, arroba, sacas por hectare, estiagem, custeio, GTA, IDARON,
gerente, cooperativa. Frases curtas. No máximo 2 emojis na legenda e nenhum nos slides.

## 7. O que nunca postar

- Promessa ou garantia de resultado, prazo de resultado, "100%", "causa ganha".
- Preço, honorários, forma de pagamento, desconto, promoção, "Black Friday", "consulta grátis", sorteio, brinde.
- Autoelogio e comparação: "o melhor", "o único", "líder", "referência", "diferente dos outros".
- Resultado de cliente, depoimento, print de decisão, número de processo, quantidade de clientes ou de ações, valores
  recuperados, "conseguimos a liminar".
- Medo exagerado e urgência apelativa: "antes que seja tarde", "vai perder tudo", "últimas vagas", "corra".
- Ataque a banco, cooperativa, gerente, juiz ou colega.
- Estrutura física e ostentação (escritório, carro, viagem) como argumento.
- Dado sem fonte (estatística, percentual) e qualquer `[CONFERIR]` ou `[PREENCHER]` não resolvido.
- Resposta a caso concreto em comentário ou direct.

O verificador (`python MARKETING/conteudo.py conferir arquivo.txt`) procura esses termos, mas **não substitui** a
leitura do advogado.

## 8. Assinatura, legenda e hashtags

- Toda legenda termina com: "Conteúdo informativo. Não substitui a análise do caso concreto." + "Caldeira Advogados
  Associados · Dr. Augusto Alves Caldeira · OAB/RO 11.101" (o sistema coloca sozinho). **[CONFERIR]** se o escritório
  quer incluir o número de registro da sociedade na OAB e o nome da Dra. Lorena Gois Fontenele (OAB/RO 14.429).
- Bio do Instagram: nome do escritório, advogado responsável com OAB, cidade, link do site. **[CONFERIR]** texto
  atual da bio.
- Hashtags: 8 a 12, misturando tema (#CreditoRural #DividaRural #ProdutorRural #FrustracaoDeSafra) e região
  (#Cacoal #Rondonia #PimentaBueno #JiParana #NorteMatoGrossense). Nada de hashtag de outra marca.

## 9. Acessibilidade

- Escrever o texto alternativo das imagens no Instagram (Configurações avançadas → Acessibilidade).
- Reels com legenda na tela. Contraste mínimo 4,5:1 no texto (já respeitado nas cores acima).
- Não colocar informação importante só na imagem: a legenda repete o essencial.

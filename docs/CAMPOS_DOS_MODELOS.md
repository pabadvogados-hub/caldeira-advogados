# Campos dos modelos (DOCS_MODELOS/)

Para usar o modelo OFICIAL do escritorio: abra o .docx de contrato, procuracao ou declaracao que voces
ja usam, troque os dados do cliente pelos campos abaixo (com as chaves duplas, exatamente assim) e salve
em `DOCS_MODELOS/` com o nome:

- `CONTRATO_HONORARIOS_MODELO.docx`
- `PROCURACAO_MODELO.docx`
- `DECLARACAO_HIPOSSUFICIENCIA_MODELO.docx`

Os modelos que estao la hoje sao PROVISORIOS e tem uma linha vermelha no topo que trava o envio.

| Campo | O que entra | De onde vem |
|---|---|---|
| `{{NOME}}` | Nome completo em maiusculas | CNH/RG |
| `{{NACIONALIDADE}}` | brasileiro(a) | CNH/RG ou cadastro |
| `{{ESTADO_CIVIL}}` | casado(a), solteiro(a)... | Cadastro do Closer |
| `{{PROFISSAO}}` | produtor(a) rural, pecuarista... | Cadastro do Closer |
| `{{RG}}` / `{{ORGAO_EMISSOR}}` | numero e orgao (ex.: SESDEC/RO) | CNH/RG |
| `{{CPF}}` | 000.000.000-00 (validado) | CNH/RG |
| `{{ENDERECO_COMPLETO}}` | rua, numero, bairro, cidade/UF, CEP | Cadastro / comprovante |
| `{{TELEFONE}}` / `{{EMAIL}}` | contato do cliente | Cadastro do Closer |
| `{{BANCOS}}` | "Banco do Brasil, Sicredi e Sicoob" | Operacoes citadas na reuniao (ou `Bancos:` no cadastro) |
| `{{OBJETO}}` | finalidade da procuracao | Montado dos bancos (ou `Objeto:` no cadastro) |
| `{{OUTORGADOS}}` | advogados com OAB | `config/escritorio.py` |
| `{{HONORARIOS_ENTRADA}}` | texto da entrada | `Honorarios entrada:` no cadastro |
| `{{HONORARIOS_PAGAMENTO}}` | forma de pagamento | `Honorarios pagamento:` no cadastro |
| `{{HONORARIOS_EXITO}}` | percentual e base do exito | `Honorarios exito:` no cadastro |
| `{{NUMERO_CONTRATO}}` | 001/2026, 002/2026... | Sequencia automatica |
| `{{CIDADE_UF}}` / `{{DATA_EXTENSO}}` | Cacoal/RO, 28 de setembro de 2026 | Automatico |
| `{{TITULAR_NOME}}` / `{{TITULAR_OAB}}` | quem assina pelo escritorio | `config/escritorio.py` |
| `{{ESCRITORIO_CNPJ}}` / `{{ESCRITORIO_ENDERECO}}` / `{{ESCRITORIO_EMAIL}}` | dados do escritorio | `config/escritorio.py` |

Campo sem dado vira `[PREENCHER CAMPO]` em vermelho no documento e trava o envio ate alguem corrigir.

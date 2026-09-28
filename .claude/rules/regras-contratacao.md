# Regras da fase de contratacao

## Origem dos dados
- Do documento oficial (CNH, RG): nome completo, CPF, RG e orgao emissor, data de nascimento, nacionalidade.
- Do cadastro do Closer: telefone, e-mail, endereco, estado civil, profissao, honorarios, origem, indicante.
- Da reuniao: fatos, bancos, operacoes, vencimentos, garantias, avalistas, perda de safra.
- Nunca inventar. Sem fonte: `[PREENCHER CAMPO]` / `[CONFERIR]`.

## Validacoes
- CPF com digito verificador valido, formato 000.000.000-00.
- Datas DD/MM/AAAA; CEP 00000-000; UF com 2 letras.
- Nome sempre completo, como no documento. Nome incompleto nunca vai para contrato.

## O que nunca acontece sem ordem humana
- Enviar documento para assinatura (`enviar`), mensagem ao cliente, cobranca no Asaas, tarefa no ADVBOX.
- Notificar banco ou protocolar qualquer peca.

## Nomes de arquivo
- `{Nome} - Relatorio de Triagem - {dd-mm-aaaa}`
- `{Nome} - Contrato de Honorarios` / `{Nome} - Procuracao` / `{Nome} - Declaracao de Hipossuficiencia`
- Assinados: `{Nome} - {Documento} (ASSINADO).pdf`

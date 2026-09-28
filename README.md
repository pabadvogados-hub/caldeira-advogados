# Caldeira Advogados Associados - Automacoes

Ecossistema de IA do escritorio, instalado na maquina e no servidor do proprio escritorio.

## Modulo 1 - Fase de Contratacao
Do "fechou" do Closer ate o caso pronto para a notificacao extrajudicial: Relatorio de Triagem para o
Gestor Juridico, contrato + procuracao + declaracao no timbrado, assinatura no ZapSign, cadastro no ADVBOX,
cobranca no Asaas, pasta no servidor e cobranca automatica dos documentos pelo WhatsApp.

```
pip install -r requirements.txt
copy config\.env.example config\.env
python CONTRATACAO/main.py exemplo
```

- Como usar no dia a dia: `docs/POP_FASE_CONTRATACAO.md`
- O que falta configurar: `docs/ONBOARDING.md`
- Campos dos modelos de documento: `docs/CAMPOS_DOS_MODELOS.md`
- Contexto para o Claude Code: `CLAUDE.md`

A IA nao protocola e nao envia nada ao banco. Toda saida passa por revisao humana.

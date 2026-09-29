#!/bin/bash
# =============================================================================
#  Instalador do sistema do Caldeira Advogados Associados - MAC (macOS)
#
#    bash deploy/mac/instalar_mac.sh            instala: ambiente .venv, dependencias,
#                                               config/.env a partir do modelo, pastas,
#                                               e oferece um teste com caso ficticio
#    bash deploy/mac/instalar_mac.sh --checar   SO confere o que existe e o que falta
#                                               - nao instala, nao cria e nao altera nada
#    --teste / --sem-teste                      roda (ou pula) o teste sem perguntar
#
#  Quem nao usa o Terminal: duplo clique em "deploy/mac/Instalar no Mac.command"
#  (na primeira vez: botao direito > Abrir, porque o arquivo veio da internet).
#
#  Depois de instalar: preencher config/.env (cada maquina tem o seu) e, SO na
#  maquina que vai rodar as rotinas automaticas, bash deploy/mac/agendar_tarefas_mac.sh
#  Guia: docs/COMECE_AQUI.md e docs/MAPA_DO_SISTEMA.md
# =============================================================================
cd "$(dirname "$0")/../.." || exit 1
PASTA="$(pwd)"
MODO=instalar
TESTE=perguntar
for a in "$@"; do
  case "$a" in
    --checar) MODO=checar ;;
    --teste) TESTE=sim ;;
    --sem-teste) TESTE=nao ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Opcao desconhecida: $a (use --checar, --teste, --sem-teste ou --help)"; exit 2 ;;
  esac
done

echo "==============================================================="
echo "  Caldeira Advogados Associados - instalacao no Mac [$MODO]"
echo "  Pasta: $PASTA"
echo "==============================================================="
[ "$(uname)" = "Darwin" ] || echo "AVISO: este instalador e para Mac. No Windows: deploy\\instalar_windows.bat"

# ------------------------------------------------------------------ Python >= 3.10
# O python3 que vem com o Mac (/usr/bin/python3) costuma ser 3.9: por isso procura
# primeiro o do python.org e o do Homebrew.
versao_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }
PYTHON=""
for c in python3.13 python3.12 python3.11 python3.10 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  caminho="$(command -v "$c" 2>/dev/null)" || continue
  if versao_ok "$caminho"; then PYTHON="$caminho"; break; fi
done
if [ -z "$PYTHON" ]; then
  echo
  echo "ERRO: Python 3.10 ou mais novo nao encontrado."
  echo "  Opcao 1 (mais simples): baixar o instalador do Python 3.12 para macOS em"
  echo "          https://www.python.org/downloads/macos/  e depois rodar este instalador de novo."
  echo "  Opcao 2 (Homebrew):     brew install python@3.12"
  echo "          (Homebrew: https://brew.sh)"
  exit 1
fi
echo "  OK    $("$PYTHON" --version 2>&1) ($PYTHON)"

tem_libreoffice() {
  command -v soffice >/dev/null 2>&1 || [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ] \
    || [ -x "$HOME/Applications/LibreOffice.app/Contents/MacOS/soffice" ]
}
caminho_tesseract() {
  for t in "$(command -v tesseract 2>/dev/null)" /opt/homebrew/bin/tesseract /usr/local/bin/tesseract; do
    [ -n "$t" ] && [ -x "$t" ] && { echo "$t"; return 0; }
  done
  return 1
}
tem_word() { [ -d "/Applications/Microsoft Word.app" ] || [ -d "$HOME/Applications/Microsoft Word.app" ]; }

orientar_programas() {
  if tem_word; then echo "  OK    Microsoft Word - PDF"; fi
  if tem_libreoffice; then
    echo "  OK    LibreOffice - PDF"
  elif ! tem_word; then
    echo "  FALTA LibreOffice (ou Word): sem ele os documentos saem so em .docx, sem PDF."
    echo "        Instalar: brew install --cask libreoffice   ou baixar em https://pt-br.libreoffice.org"
  else
    echo "  AVISO sem LibreOffice: o PDF usa o Word (ele pode pedir permissao na primeira vez)."
  fi
  if TESS="$(caminho_tesseract)"; then
    if "$TESS" --list-langs 2>/dev/null | grep -qx por; then
      echo "  OK    Tesseract com portugues - OCR de documento escaneado"
    else
      echo "  AVISO Tesseract sem o idioma portugues: brew install tesseract-lang"
    fi
  else
    echo "  AVISO sem Tesseract (opcional): CNH/RG escaneados nao sao lidos."
    echo "        Instalar: brew install tesseract tesseract-lang"
  fi
  if ! command -v brew >/dev/null 2>&1; then
    echo "        (Homebrew nao instalado: https://brew.sh - ou use os instaladores dos sites)"
  fi
}

avisar_pasta_protegida() {
  case "$PASTA" in
    "$HOME/Documents"*|"$HOME/Desktop"*|"$HOME/Downloads"*|"$HOME/Library/Mobile Documents"*|"$HOME/Library/CloudStorage"*)
      echo "  AVISO o sistema esta em Documentos/Mesa/Downloads/iCloud/Drive. Para uso manual tudo bem;"
      echo "        para as ROTINAS AUTOMATICAS o macOS bloqueia essas pastas. Nesse caso use $HOME/CALDEIRA_ADVOGADOS."
      ;;
  esac
}

if [ "$MODO" = "checar" ]; then
  # ---------------------------------------------------------------- checar (nao muda nada)
  echo
  PY="$PYTHON"
  if [ -x ".venv/bin/python" ]; then PY="$PASTA/.venv/bin/python"; echo "  OK    .venv"
  else echo "  FALTA .venv - rodar: bash deploy/mac/instalar_mac.sh"; fi
  [ -f requirements.txt ] && echo "  OK    requirements.txt" || echo "  FALTA requirements.txt"
  for m in CONTRATACAO EXTRAJUDICIAL JUDICIAL CONTROLADORIA GESTAO COMERCIAL MARKETING FINANCEIRO; do
    if [ -f "$m/main.py" ] || [ -f "$m/trafego.py" ]; then echo "  OK    modulo $m"
    else echo "  ----  modulo $m ainda nao instalado"; fi
  done
  if "$PY" -c "import anthropic, docx, dotenv, requests, openpyxl, fitz, PIL" >/dev/null 2>&1; then
    echo "  OK    pacotes Python principais"
  else
    echo "  FALTA pacotes Python - rodar: bash deploy/mac/instalar_mac.sh"
  fi
  [ -f config/.env ] && echo "  OK    config/.env" || echo "  FALTA config/.env - copiar de config/.env.example"
  [ -d logs ] && echo "  OK    pasta logs" || echo "  FALTA pasta logs"
  [ -d SAIDA ] && echo "  OK    pasta SAIDA" || echo "  FALTA pasta SAIDA"
  orientar_programas
  avisar_pasta_protegida
  echo
  echo "Credenciais do config/.env - so diz se estao preenchidas, nunca mostra o valor:"
  "$PY" -c "import sys; sys.path.insert(0,'NUCLEO'); import ambiente as a; [print('  ', 'OK   ' if a.tem_credencial(v) else 'VAZIO', v) for v in ('ANTHROPIC_API_KEY','ASAAS_API_TOKEN','ADVBOX_API_TOKEN','ZAPSIGN_API_TOKEN','ATENDE_DIREITO_TOKEN','PASTA_CLIENTES_RAIZ','ALERTA_WHATSAPP')]" 2>/dev/null \
    || echo "   (instale primeiro para conferir as credenciais)"
  "$PY" -c "
import os, sys
sys.path.insert(0, 'NUCLEO')
import ambiente
p = os.getenv('PASTA_CLIENTES_RAIZ', '')
if not p:
    print('   VAZIO pasta dos clientes (PASTA_CLIENTES_RAIZ) - no Mac: /Volumes/CLIENTES')
elif os.path.isdir(p):
    print('   OK    pasta dos clientes acessivel:', p)
else:
    print('   FALTA pasta dos clientes nao encontrada:', p)
    print('         Conectar no Finder: Ir > Conectar ao Servidor > smb://SERVIDOR/CLIENTES')
    if ':' in p[:3] or p.startswith(chr(92) * 2):
        print('         ATENCAO: esse caminho e do Windows. No Mac use /Volumes/CLIENTES')
" 2>/dev/null
  echo
  N="$(ls "$HOME/Library/LaunchAgents"/br.com.caldeira.*.plist 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$N" -gt 0 ]; then
    echo "  Rotinas automaticas AGENDADAS neste Mac: $N (bash deploy/mac/agendar_tarefas_mac.sh --listar)"
  else
    echo "  Rotinas automaticas: nenhuma neste Mac (so os comandos sob demanda)."
  fi
  echo
  echo "Checagem concluida - nada foi instalado nem alterado."
  exit 0
fi

# ------------------------------------------------------------------ instalar
echo
echo "[1/5] Ambiente Python isolado (.venv)..."
if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON" -m venv .venv || { echo "ERRO ao criar a .venv."; exit 1; }
else
  echo "  .venv ja existe."
fi
PY="$PASTA/.venv/bin/python"

echo "[2/5] Dependencias..."
"$PY" -m pip install --upgrade pip >/dev/null
if ! "$PY" -m pip install -r requirements.txt; then
  # o docx2pdf (PDF pelo Word) e o unico pacote que pode falhar no Mac; sem ele o PDF sai pelo LibreOffice
  echo "  ATENCAO: falhou a instalacao completa. Tentando sem o docx2pdf (o PDF passa a usar o LibreOffice)..."
  grep -v -i '^docx2pdf' requirements.txt > .requirements_sem_docx2pdf.txt
  "$PY" -m pip install -r .requirements_sem_docx2pdf.txt || echo "  ATENCAO: falha no pip install - ver mensagens acima."
  rm -f .requirements_sem_docx2pdf.txt
fi
for req in */requirements.txt; do
  [ -f "$req" ] || continue
  echo "  extras de $(dirname "$req")"
  "$PY" -m pip install -r "$req" || echo "  ATENCAO: falha em $req"
done

echo "[3/5] config/.env..."
if [ ! -f config/.env ]; then
  cp config/.env.example config/.env && chmod 600 config/.env
  echo "  config/.env criado a partir do modelo. PRECISA SER PREENCHIDO (cada maquina tem o seu)."
  echo "  No Mac, a pasta do servidor fica assim: PASTA_CLIENTES_RAIZ=/Volumes/CLIENTES"
else
  echo "  config/.env ja existe, nao foi mexido."
fi

echo "[4/5] Pastas de trabalho e atalhos..."
mkdir -p logs SAIDA
echo "  logs/ e SAIDA/ prontas."
chmod +x deploy/mac/*.sh deploy/mac/*.command deploy/vps/*.sh 2>/dev/null
# arquivo baixado da internet fica em quarentena e o duplo clique e bloqueado
xattr -dr com.apple.quarantine deploy/mac 2>/dev/null
echo
echo "Programas de apoio (PDF e OCR):"
orientar_programas
avisar_pasta_protegida

echo
echo "[5/5] Teste com caso ficticio - nada e enviado para ninguem."
if [ "$TESTE" = "perguntar" ]; then
  if [ -t 0 ]; then
    printf "Rodar o teste agora? [s/N] (30s = N) "
    read -r -t 30 r || r=n
    case "$r" in s|S|sim|SIM) TESTE=sim ;; *) TESTE=nao ;; esac
  else
    TESTE=nao
  fi
fi
if [ "$TESTE" = "sim" ]; then
  export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
  "$PY" CONTRATACAO/main.py exemplo
  "$PY" FINANCEIRO/main.py cobranca --exemplo
fi

echo
echo "==============================================================="
echo "  Instalacao concluida."
echo "==============================================================="
echo "Proximos passos:"
echo "  1. Preencher config/.env com as chaves - ver docs/MAPA_DO_SISTEMA.md"
echo "     (abrir: open -e config/.env ; pasta do servidor no Mac: /Volumes/CLIENTES)"
echo "  2. Conferir:  bash deploy/mac/instalar_mac.sh --checar"
echo "  3. SO na maquina que vai rodar as rotinas automaticas (uma so no escritorio):"
echo "     bash deploy/mac/agendar_tarefas_mac.sh"
echo "  4. Usar os comandos:  source .venv/bin/activate  e depois  python CONTRATACAO/main.py painel"
echo "  5. Guia da equipe: docs/COMECE_AQUI.md"

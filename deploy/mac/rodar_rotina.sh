#!/bin/bash
# =============================================================================
#  rodar_rotina.sh (Mac) - roda UMA rotina com log em logs/NOME.log. E o que o
#  launchd chama (deploy/mac/agendar_tarefas_mac.sh), mas serve para rodar a mao:
#
#    bash deploy/mac/rodar_rotina.sh financeiro_inadimplencia FINANCEIRO/main.py inadimplencia
#
#  So acerta o ambiente do Mac e reaproveita deploy/vps/rodar_rotina.sh (mesma
#  logica da VPS): usa a .venv, grava o log, pula modulo que ainda nao existe e,
#  se a rotina falhar, avisa por WhatsApp (healthcheck.py --falha).
# =============================================================================
PASTA="$(cd "$(dirname "$0")/../.." && pwd)"

# o launchd comeca com um PATH minimo: inclui o Homebrew (Tesseract, LibreOffice)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export LANG="${LANG:-pt_BR.UTF-8}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

exec /bin/bash "$PASTA/deploy/vps/rodar_rotina.sh" "$@"

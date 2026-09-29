#!/usr/bin/env bash
# =============================================================================
#  rodar_rotina.sh - roda UMA rotina com log em logs/NOME.log. Usado pelo cron da
#  alternativa Docker (deploy/vps/docker/crontab) e serve para rodar a mao na VPS:
#
#    bash deploy/vps/rodar_rotina.sh financeiro_cobranca FINANCEIRO/main.py cobranca --enviar
#
#  Modulo ainda nao instalado: registra e sai sem erro. Falha: avisa por WhatsApp
#  (healthcheck.py --falha), igual ao OnFailure do systemd.
# =============================================================================
set -uo pipefail

APP="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$APP"
NOME="${1:?uso: rodar_rotina.sh NOME_DO_LOG MODULO/main.py argumentos...}"
shift
SCRIPT="${1:?falta o script}"
PY="$APP/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
mkdir -p logs
LOG="logs/$NOME.log"

{ echo; echo "===== $(date '+%d/%m/%Y %H:%M:%S') ====="; } >> "$LOG"
if [ ! -f "$SCRIPT" ]; then
  echo "Modulo ainda nao instalado: $SCRIPT - nada feito." >> "$LOG"
  exit 0
fi
"$PY" "$@" >> "$LOG" 2>&1
RC=$?
echo "----- fim, codigo $RC" >> "$LOG"
if [ "$RC" -ne 0 ] && [ "$NOME" != "healthcheck" ]; then
  "$PY" deploy/vps/healthcheck.py --falha "$NOME" >> logs/healthcheck.log 2>&1 || true
fi
exit "$RC"

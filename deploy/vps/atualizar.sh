#!/usr/bin/env bash
# =============================================================================
#  atualizar.sh - traz a versao nova do repositorio para a VPS, reinstala as
#  dependencias e as rotinas do systemd. Rodar como root:
#
#    sudo bash /opt/caldeira/app/deploy/vps/atualizar.sh
#
#  - git pull so avanca (--ff-only): nunca apaga mudanca feita na VPS; se houver
#    conflito, para e avisa
#  - config/.env, logs/ e SAIDA/ nao sao tocados
#  - se as rotinas ja estavam ligadas, rotinas novas tambem sao ligadas
# =============================================================================
set -euo pipefail

USUARIO=caldeira
APP=/opt/caldeira/app
MODULOS="CONTRATACAO EXTRAJUDICIAL JUDICIAL CONTROLADORIA GESTAO COMERCIAL FINANCEIRO"
como_app() { sudo -u "$USUARIO" -H "$@"; }

[ "$(id -u)" -eq 0 ] || { echo "Rodar como root: sudo bash $0"; exit 1; }
[ -d "$APP/.git" ] || { echo "Nao achei $APP. Instalar antes com deploy/vps/instalar_vps.sh"; exit 1; }

echo ">> 1/4 Codigo (git pull)"
ANTES=$(como_app git -C "$APP" rev-parse --short HEAD)
como_app git -C "$APP" pull --ff-only
DEPOIS=$(como_app git -C "$APP" rev-parse --short HEAD)
echo "   $ANTES -> $DEPOIS"

echo ">> 2/4 Dependencias"
como_app "$APP/.venv/bin/pip" install --quiet -r "$APP/requirements.txt"
for m in $MODULOS; do
  if [ -f "$APP/$m/requirements.txt" ]; then
    como_app "$APP/.venv/bin/pip" install --quiet -r "$APP/$m/requirements.txt"
  fi
done

echo ">> 3/4 Rotinas (systemd)"
LIGADAS=0
for t in /etc/systemd/system/caldeira-*.timer; do
  if [ -f "$t" ] && systemctl is-enabled --quiet "$(basename "$t")"; then LIGADAS=1; fi
done
install -m 644 "$APP"/deploy/vps/systemd/*.service "$APP"/deploy/vps/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
if [ "$LIGADAS" -eq 1 ]; then
  for t in "$APP"/deploy/vps/systemd/*.timer; do
    systemctl enable --now "$(basename "$t")" >/dev/null
    systemctl restart "$(basename "$t")"
  done
  echo "   rotinas ligadas e com o horario atualizado"
else
  echo "   rotinas continuam DESLIGADAS (ligar com instalar_vps.sh ... --ativar-rotinas)"
fi

echo ">> 4/4 Checagem"
como_app bash -c "cd '$APP' && .venv/bin/python deploy/vps/healthcheck.py --sem-aviso" || true
echo
echo "Atualizado. Agenda: systemctl list-timers 'caldeira-*'"

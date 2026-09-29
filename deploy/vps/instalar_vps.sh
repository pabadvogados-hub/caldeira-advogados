#!/usr/bin/env bash
# =============================================================================
#  instalar_vps.sh - instala o sistema do Caldeira Advogados Associados numa VPS
#  Ubuntu 22.04 ou 24.04. Rodar como root. Idempotente: pode rodar de novo.
#
#    sudo bash instalar_vps.sh git@github.com:ORGANIZACAO/REPOSITORIO.git
#    sudo bash instalar_vps.sh git@github.com:ORGANIZACAO/REPOSITORIO.git --ativar-rotinas
#
#  1. pacotes (Python, git, LibreOffice headless para PDF, fontes, OCR)
#  2. fuso America/Porto_Velho
#  3. usuario dedicado "caldeira" (sem senha e sem sudo)
#  4. deploy key SSH (somente leitura) para clonar o repositorio privado
#  5. codigo em /opt/caldeira/app + .venv + dependencias
#  6. config/.env a partir do modelo, permissao 600 (preencher a mao)
#  7. logs/, SAIDA/ e rotacao de logs
#  8. rotinas no systemd (.service + .timer). Os timers so ligam com --ativar-rotinas
#
#  Passo a passo completo: docs/DEPLOY_VPS.md
# =============================================================================
set -euo pipefail

REPO="${1:-}"
ATIVAR=0
for a in "$@"; do if [ "$a" = "--ativar-rotinas" ]; then ATIVAR=1; fi; done
USUARIO=caldeira
BASE=/opt/caldeira
APP=$BASE/app
CHAVE=$BASE/.ssh/deploy_key
FUSO=America/Porto_Velho
MODULOS="CONTRATACAO EXTRAJUDICIAL JUDICIAL CONTROLADORIA GESTAO COMERCIAL FINANCEIRO"

msg() { echo; echo ">> $*"; }
como_app() { sudo -u "$USUARIO" -H "$@"; }

[ "$(id -u)" -eq 0 ] || { echo "Rodar como root: sudo bash $0 ..."; exit 1; }
if [ -z "$REPO" ] || [[ "$REPO" == --* ]]; then
  echo "Uso: sudo bash $0 git@github.com:ORGANIZACAO/REPOSITORIO.git [--ativar-rotinas]"
  exit 1
fi

msg "1/8 Pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git openssh-client ca-certificates tzdata \
  logrotate sudo fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea \
  tesseract-ocr tesseract-ocr-por
# LibreOffice sem interface grafica: converte .docx em PDF (docx_caldeira.docx_para_pdf)
apt-get install -y --no-install-recommends libreoffice-writer-nogui \
  || apt-get install -y --no-install-recommends libreoffice-writer

msg "2/8 Fuso horario $FUSO"
timedatectl set-timezone "$FUSO" 2>/dev/null || ln -sf "/usr/share/zoneinfo/$FUSO" /etc/localtime
date

msg "3/8 Usuario dedicado '$USUARIO'"
if ! id "$USUARIO" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$BASE" --shell /bin/bash "$USUARIO"
fi
install -d -m 750 -o "$USUARIO" -g "$USUARIO" "$BASE"
install -d -m 700 -o "$USUARIO" -g "$USUARIO" "$BASE/.ssh"

msg "4/8 Deploy key (somente leitura) do repositorio privado"
if [ ! -f "$CHAVE" ]; then
  como_app ssh-keygen -q -t ed25519 -N "" -C "caldeira-vps-deploy" -f "$CHAVE"
fi
como_app bash -c "ssh-keyscan -t ed25519 github.com 2>/dev/null >> '$BASE/.ssh/known_hosts'; \
  sort -u -o '$BASE/.ssh/known_hosts' '$BASE/.ssh/known_hosts'"
cat > "$BASE/.ssh/config" <<EOF
Host github.com
  IdentityFile $CHAVE
  IdentitiesOnly yes
EOF
chown "$USUARIO:$USUARIO" "$BASE/.ssh/config"
chmod 600 "$BASE/.ssh/config"

if ! como_app git ls-remote "$REPO" >/dev/null 2>&1; then
  echo
  echo "   A VPS ainda nao tem acesso ao repositorio. Cadastre a chave abaixo no GitHub como"
  echo "   Deploy key SOMENTE LEITURA: repositorio > Settings > Deploy keys > Add deploy key"
  echo "   (NAO marcar 'Allow write access')."
  echo
  cat "$CHAVE.pub"
  echo
  echo "   Depois rode este script de novo: ele continua de onde parou."
  exit 2
fi

msg "5/8 Codigo em $APP"
if [ -d "$APP/.git" ]; then
  como_app git -C "$APP" pull --ff-only
else
  como_app git clone "$REPO" "$APP"
fi
[ -x "$APP/.venv/bin/python" ] || como_app python3 -m venv "$APP/.venv"
como_app "$APP/.venv/bin/pip" install --quiet --upgrade pip wheel
como_app "$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
for m in $MODULOS; do
  if [ -f "$APP/$m/requirements.txt" ]; then
    como_app "$APP/.venv/bin/pip" install -r "$APP/$m/requirements.txt"
  fi
done

msg "6/8 config/.env (credenciais)"
if [ ! -f "$APP/config/.env" ]; then
  install -m 600 -o "$USUARIO" -g "$USUARIO" "$APP/config/.env.example" "$APP/config/.env"
  echo "   config/.env criado a partir do modelo: PRECISA SER PREENCHIDO."
else
  echo "   config/.env ja existe, nao foi mexido."
fi
chown "$USUARIO:$USUARIO" "$APP/config/.env"
chmod 600 "$APP/config/.env"

msg "7/8 Pastas de trabalho e rotacao de logs"
install -d -m 750 -o "$USUARIO" -g "$USUARIO" "$APP/logs" "$APP/SAIDA"
cat > /etc/logrotate.d/caldeira <<EOF
$APP/logs/*.log {
  weekly
  rotate 12
  compress
  missingok
  notifempty
  copytruncate
}
EOF

msg "8/8 Rotinas (systemd)"
install -m 644 "$APP"/deploy/vps/systemd/*.service "$APP"/deploy/vps/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
if [ "$ATIVAR" -eq 1 ]; then
  for t in "$APP"/deploy/vps/systemd/*.timer; do
    systemctl enable --now "$(basename "$t")" >/dev/null
  done
  echo "   Rotinas LIGADAS."
  systemctl list-timers 'caldeira-*' --no-pager || true
else
  echo "   Rotinas instaladas e DESLIGADAS. Para ligar, depois de preencher o .env:"
  echo "   sudo bash $APP/deploy/vps/instalar_vps.sh $REPO --ativar-rotinas"
fi

echo
echo "================================================================="
echo " Instalacao concluida em $APP"
echo "================================================================="
echo " 1. Preencher as credenciais:  sudo -u $USUARIO nano $APP/config/.env"
echo " 2. Conferir:  sudo -u $USUARIO -H bash -c 'cd $APP && .venv/bin/python deploy/vps/healthcheck.py --sem-aviso'"
echo " 3. Ligar as rotinas (--ativar-rotinas) e DESLIGAR as do Windows:"
echo "    deploy\\agendar_tarefas_windows.bat /remover   (na maquina do escritorio)"
echo " 4. Logs: $APP/logs/   |   Agenda: systemctl list-timers 'caldeira-*'"
echo " Rotinas que usam a pasta dos clientes precisam de PASTA_CLIENTES_RAIZ acessivel"
echo " na VPS (ex.: Google Drive montado com rclone). Ver docs/DEPLOY_VPS.md."

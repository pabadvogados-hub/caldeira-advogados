# =============================================================================
#  ALTERNATIVA OPCIONAL ao systemd (o caminho padrao e deploy/vps/instalar_vps.sh).
#  Um container com cron rodando as mesmas rotinas, no horario de Rondonia.
#  Build a partir da RAIZ do repositorio:
#     docker compose -f deploy/vps/docker-compose.yml up -d --build
#  O config/.env NAO entra na imagem (Dockerfile.dockerignore): e montado pelo compose.
# =============================================================================
FROM python:3.12-slim

ENV TZ=America/Porto_Velho \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends cron tzdata ca-certificates \
      libreoffice-writer-nogui fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea \
      tesseract-ocr tesseract-ocr-por \
 && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN for m in CONTRATACAO EXTRAJUDICIAL JUDICIAL CONTROLADORIA GESTAO COMERCIAL FINANCEIRO; do \
      if [ -f "$m/requirements.txt" ]; then pip install -r "$m/requirements.txt"; fi; \
    done \
 && mkdir -p logs SAIDA \
 && crontab deploy/vps/docker/crontab

HEALTHCHECK --interval=1h --timeout=2m CMD python deploy/vps/healthcheck.py --sem-aviso || exit 1

CMD ["cron", "-f"]

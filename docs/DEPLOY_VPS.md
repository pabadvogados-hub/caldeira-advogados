# VPS 24 horas - passo a passo

Bônus do projeto: uma VPS (servidor na nuvem) ligada 24 horas rodando as rotinas automáticas, para o
sistema não depender da máquina do escritório estar ligada. O caminho padrão é **systemd** (um `.service`
e um `.timer` por rotina); Docker é alternativa opcional (seção 9).

Arquivos: `deploy/vps/instalar_vps.sh`, `deploy/vps/atualizar.sh`, `deploy/vps/healthcheck.py`,
`deploy/vps/rodar_rotina.sh`, `deploy/vps/systemd/` e, opcional, `deploy/vps/Dockerfile` +
`deploy/vps/docker-compose.yml`.

## 0. Antes de começar: onde ficam as rotinas

As rotinas rodam em **um lugar só**. Se rodarem no Windows e na VPS ao mesmo tempo, o cliente recebe
mensagem em dobro (cada máquina tem o seu histórico de envios).

- **Tudo na VPS:** ligar as rotinas na VPS (passo 6) e rodar na máquina do escritório
  `deploy\agendar_tarefas_windows.bat /remover`.
- **Misto:** as rotinas que usam a pasta dos clientes no servidor interno continuam no Windows e as que
  só falam com APIs vão para a VPS. Veja a tabela do passo 5 e ligue na VPS só os timers escolhidos
  (`systemctl enable --now caldeira-NOME.timer`); no Windows, desabilite as mesmas tarefas no Agendador
  (pasta Caldeira > tarefa > Desabilitar).

## 1. Contratar a VPS

- Ubuntu **24.04 LTS** (ou 22.04), 2 vCPU, 4 GB de RAM, 40 GB de disco (o LibreOffice, que gera os PDFs,
  pede memória). Qualquer provedor serve.
- Acesso SSH por **chave** (não por senha). Anotar o IP.
- Nenhuma porta precisa ficar aberta além do SSH: as rotinas só fazem chamadas de saída.

Primeiro acesso, como root:
```bash
apt-get update && apt-get -y upgrade
apt-get install -y unattended-upgrades ufw
ufw allow OpenSSH && ufw --force enable
```

## 2. Repositório privado

O código fica num repositório **privado** no GitHub (sem `.env`, sem dados de cliente: o `.gitignore`
já barra). A VPS clona com uma **deploy key somente leitura**, que o instalador gera.

## 3. Rodar o instalador

Da máquina do escritório (PowerShell ou CMD, na pasta do sistema), copiar o instalador para a VPS:
```
scp deploy/vps/instalar_vps.sh root@IP_DA_VPS:/root/
```
Na VPS:
```bash
sudo bash /root/instalar_vps.sh git@github.com:ORGANIZACAO/REPOSITORIO.git
```
Na primeira vez ele instala os pacotes, acerta o fuso para **America/Porto_Velho**, cria o usuário
`caldeira` e **para mostrando uma chave pública**. Cadastre essa chave no GitHub:
repositório > Settings > Deploy keys > Add deploy key (NÃO marcar "Allow write access"). Rode o mesmo
comando de novo: ele clona em `/opt/caldeira/app`, cria o `.venv`, instala as dependências, cria o
`config/.env` a partir do modelo (permissão 600), as pastas `logs/` e `SAIDA/`, a rotação de logs e
instala as rotinas no systemd **desligadas**.

O instalador pode ser rodado quantas vezes precisar: ele continua de onde parou e não sobrescreve o `.env`.

## 4. Credenciais

Preencher direto na VPS (nunca por e-mail, WhatsApp ou git):
```bash
sudo -u caldeira nano /opt/caldeira/app/config/.env
```
Ou copiar o `.env` já preenchido da máquina do escritório:
```
scp config/.env root@IP_DA_VPS:/tmp/caldeira.env
```
```bash
sudo install -m 600 -o caldeira -g caldeira /tmp/caldeira.env /opt/caldeira/app/config/.env && rm /tmp/caldeira.env
```
Lista de variáveis: `docs/MAPA_DO_SISTEMA.md`. Para os avisos do healthcheck, preencher
`ALERTA_WHATSAPP` com o número que recebe os alertas (ele precisa ser contato no Atende Direito:
mande um "oi" desse número para o WhatsApp do escritório uma vez).

Conferir:
```bash
sudo -u caldeira -H bash -c 'cd /opt/caldeira/app && .venv/bin/python deploy/vps/healthcheck.py --sem-aviso'
```

## 5. Pasta dos clientes na VPS

A VPS não enxerga o servidor interno do escritório. As rotinas que leem ou gravam na pasta dos clientes
precisam de `PASTA_CLIENTES_RAIZ` acessível na VPS; as outras só usam APIs.

| Rotina | Precisa da pasta dos clientes? |
|---|---|
| Contratação: acompanhar | sim |
| Extrajudicial: acompanhar | sim |
| Controladoria: varredura, relatório aos clientes | conferir no módulo (usa o ADVBOX; pode gravar na pasta) |
| Financeiro: honorários novos | sim |
| Financeiro: cobrança, inadimplência, fechamento | não (Asaas e ADVBOX) |
| Comercial: Meta Ads, radar, auditoria do atendimento | não |
| Gestão: pauta, auditoria | não (ADVBOX) |
| Healthcheck | não |

Se a pasta dos clientes já está no **Google Drive** (sincronizada no escritório), dá para montar o
mesmo Drive na VPS com o `rclone`:
```bash
sudo apt-get install -y rclone fuse3
sudo -u caldeira rclone config            # criar o remoto "drive" com a conta Google do escritório
sudo mkdir -p /mnt/clientes && sudo chown caldeira:caldeira /mnt/clientes
```
Serviço para montar sempre (arquivo `/etc/systemd/system/caldeira-drive.service`):
```ini
[Unit]
Description=Caldeira - Google Drive dos clientes em /mnt/clientes
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=caldeira
ExecStart=/usr/bin/rclone mount drive:CLIENTES /mnt/clientes --vfs-cache-mode writes
ExecStop=/bin/fusermount3 -uz /mnt/clientes
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now caldeira-drive
```
E no `.env` da VPS: `PASTA_CLIENTES_RAIZ=/mnt/clientes`. Sem isso, deixe essas rotinas no Windows
(modo misto do passo 0).

## 6. Ligar as rotinas

```bash
sudo bash /opt/caldeira/app/deploy/vps/instalar_vps.sh git@github.com:ORGANIZACAO/REPOSITORIO.git --ativar-rotinas
systemctl list-timers 'caldeira-*'
```
Testar uma rotina na hora (só relatório, não manda nada a ninguém):
```bash
sudo systemctl start caldeira-financeiro-inadimplencia.service
tail -n 30 /opt/caldeira/app/logs/financeiro_inadimplencia.log
```
Depois, **na máquina do escritório**: `deploy\agendar_tarefas_windows.bat /remover` (ou desabilitar só as
que foram para a VPS, no modo misto).

Horários (fuso de Rondônia): iguais aos do Windows, ver `docs/MAPA_DO_SISTEMA.md`. O healthcheck roda de
hora em hora. Rotinas que mandam mensagem ao cliente (contratação, extrajudicial, cobrança) **não** são
recuperadas se a VPS estiver fora do ar no horário: esperam o próximo, para não sair mensagem de
madrugada. Os relatórios são recuperados quando a VPS volta.

Se uma rotina falhar, o `caldeira-alerta@.service` manda um WhatsApp para `ALERTA_WHATSAPP` (no máximo
1 aviso por rotina a cada 6 horas). Se uma integração cair (ADVBOX, Asaas, ZapSign, Atende Direito, API
do Claude, pasta dos clientes, disco), o healthcheck avisa e avisa de novo quando voltar ao normal.

## 7. Atualizar a versão

Depois de publicar mudanças no repositório:
```bash
sudo bash /opt/caldeira/app/deploy/vps/atualizar.sh
```
Faz `git pull` (só avança; nunca apaga mudança feita na VPS), reinstala dependências e rotinas e roda o
healthcheck. `config/.env`, `logs/` e `SAIDA/` não são tocados.

## 8. Dia a dia

| Para | Comando |
|---|---|
| Ver a agenda | `systemctl list-timers 'caldeira-*'` |
| Ver se a última execução deu certo | `systemctl status caldeira-financeiro-cobranca.service` |
| Ver o log de uma rotina | `tail -n 50 /opt/caldeira/app/logs/financeiro_cobranca.log` |
| Rodar uma rotina agora | `sudo systemctl start caldeira-NOME.service` |
| Rodar um comando a mão | `sudo -u caldeira -H bash -c 'cd /opt/caldeira/app && .venv/bin/python FINANCEIRO/main.py inadimplencia'` |
| Desligar uma rotina | `sudo systemctl disable --now caldeira-NOME.timer` |
| Avisos enviados | `/opt/caldeira/app/logs/healthcheck_alertas.log` |

Backup: `config/.env` e `SAIDA/` (o histórico da régua de cobrança fica em
`SAIDA/FINANCEIRO/historico_cobranca.json`; se perder, a régua pode repetir o toque do dia). Ative os
snapshots automáticos do provedor.

## 9. Alternativa: Docker (opcional)

Para quem prefere container. **Não usar junto com os timers do systemd.**
```bash
sudo apt-get install -y docker.io docker-compose-v2
cd /opt/caldeira/app
sudo docker compose -f deploy/vps/docker-compose.yml up -d --build
sudo docker compose -f deploy/vps/docker-compose.yml logs -f
```
O container roda o `cron` com a mesma agenda (`deploy/vps/docker/crontab`), no fuso de Rondônia. O
`config/.env` é montado de fora (não entra na imagem), e `logs/` e `SAIDA/` ficam na pasta do sistema.
A pasta dos clientes entra em `/clientes` (ver o volume no `docker-compose.yml`).

## 10. Segurança

- Usuário `caldeira` sem senha e sem sudo; o código roda com ele.
- `config/.env` com permissão 600; nunca vai para o git, e-mail ou WhatsApp.
- Deploy key somente leitura: a VPS não consegue alterar o repositório.
- SSH só por chave; firewall com apenas o SSH liberado; atualizações de segurança automáticas.
- Nenhuma rotina abre porta na internet.

## 11. Atendimento do lead a qualquer hora

A VPS já fica ligada 24 horas e com o sistema instalado. Hoje o atendimento do SDR (`COMERCIAL/main.py sdr`)
é sob demanda; responder o lead automaticamente a qualquer hora exige um serviço que receba as mensagens
do Atende Direito na hora (webhook). Esse serviço é o próximo passo e vai rodar nesta mesma VPS.

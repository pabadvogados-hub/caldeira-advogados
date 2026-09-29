@echo off
REM =============================================================================
REM  Instalador do sistema do Caldeira Advogados Associados - WINDOWS
REM
REM    deploy\instalar_windows.bat            instala: ambiente .venv, dependencias,
REM                                           config\.env a partir do modelo, pastas,
REM                                           e oferece um teste com caso ficticio
REM    deploy\instalar_windows.bat /checar    SO confere o que existe e o que falta
REM                                           - nao instala, nao cria e nao altera nada
REM    acrescente /sem-pausa para nao esperar uma tecla no final
REM
REM  Depois de instalar: preencher config\.env e rodar deploy\agendar_tarefas_windows.bat
REM  Guia: docs\COMECE_AQUI.md e docs\MAPA_DO_SISTEMA.md
REM =============================================================================
setlocal EnableExtensions
cd /d "%~dp0.."
set "PASTA=%cd%"
set "MODO=instalar"
set "SEMPAUSA="
if /I "%~1"=="/checar" set "MODO=checar"
if /I "%~1"=="/sem-pausa" set "SEMPAUSA=1"
if /I "%~2"=="/sem-pausa" set "SEMPAUSA=1"
set "MODULOS=CONTRATACAO EXTRAJUDICIAL JUDICIAL CONTROLADORIA GESTAO COMERCIAL MARKETING FINANCEIRO"

echo ===============================================================
echo   Caldeira Advogados Associados - instalacao [%MODO%]
echo   Pasta: %PASTA%
echo ===============================================================

where python >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale o Python 3.11 ou mais novo em
  echo https://www.python.org/downloads/ e marque "Add Python to PATH".
  goto fim
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo ERRO: Python muito antigo. Precisa da versao 3.10 ou mais nova.
  goto fim
)
for /f "delims=" %%V in ('python --version') do echo   OK    %%V

if "%MODO%"=="checar" goto checar

REM ---------------------------------------------------------------- instalar
echo.
echo [1/5] Ambiente Python isolado (.venv)...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo ERRO ao criar o .venv.
    goto fim
  )
) else (
  echo   .venv ja existe.
)
set "PY=%PASTA%\.venv\Scripts\python.exe"

echo [2/5] Dependencias...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 echo   ATENCAO: falha no pip install -r requirements.txt - ver mensagens acima.
for %%M in (%MODULOS%) do if exist "%%M\requirements.txt" (
  echo   extras de %%M
  "%PY%" -m pip install -r "%%M\requirements.txt"
)

echo [3/5] config\.env...
if not exist "config\.env" (
  copy "config\.env.example" "config\.env" >nul
  echo   config\.env criado a partir do modelo. PRECISA SER PREENCHIDO.
) else (
  echo   config\.env ja existe, nao foi mexido.
)

echo [4/5] Pastas de trabalho...
for %%D in (logs SAIDA) do if not exist "%%D" mkdir "%%D"
echo   logs\ e SAIDA\ prontas.

echo [5/5] Teste com caso ficticio - nada e enviado para ninguem.
choice /C SN /N /T 30 /D N /M "Rodar o teste agora? [S/N] (30s = N) "
if errorlevel 2 goto depois_teste
set PYTHONIOENCODING=utf-8
"%PY%" CONTRATACAO\main.py exemplo
"%PY%" FINANCEIRO\main.py cobranca --exemplo
:depois_teste

echo.
echo ===============================================================
echo   Instalacao concluida.
echo ===============================================================
echo Proximos passos:
echo   1. Preencher config\.env com as chaves - ver docs\MAPA_DO_SISTEMA.md
echo   2. Conferir:  deploy\instalar_windows.bat /checar
echo   3. Agendar as rotinas:  deploy\agendar_tarefas_windows.bat  - como administrador
echo   4. Guia da equipe: docs\COMECE_AQUI.md
goto fim

REM ---------------------------------------------------------------- checar
:checar
echo.
set "PY=python"
if exist ".venv\Scripts\python.exe" (
  set "PY=%PASTA%\.venv\Scripts\python.exe"
  echo   OK    .venv
) else (
  echo   FALTA .venv - rodar deploy\instalar_windows.bat
)
if exist "requirements.txt" (echo   OK    requirements.txt) else (echo   FALTA requirements.txt)
for %%M in (%MODULOS%) do if exist "%%M\main.py" (echo   OK    modulo %%M) else (echo   ----  modulo %%M ainda nao instalado)
"%PY%" -c "import anthropic, docx, dotenv, requests, openpyxl" >nul 2>nul
if errorlevel 1 (echo   FALTA pacotes Python - rodar deploy\instalar_windows.bat) else (echo   OK    pacotes Python principais)
if exist "config\.env" (echo   OK    config\.env) else (echo   FALTA config\.env - copiar de config\.env.example)
if exist "logs" (echo   OK    pasta logs) else (echo   FALTA pasta logs)
where soffice >nul 2>nul
if not errorlevel 1 (
  echo   OK    LibreOffice no PATH - PDF
) else if exist "C:\Program Files\LibreOffice\program\soffice.exe" (
  echo   OK    LibreOffice - PDF
) else (
  echo   AVISO sem LibreOffice no caminho padrao: o PDF usa o Word, se instalado
)
echo.
echo Credenciais do config\.env - so diz se estao preenchidas, nunca mostra o valor:
"%PY%" -c "import sys; sys.path.insert(0,'NUCLEO'); import ambiente as a; [print('  ', 'OK   ' if a.tem_credencial(v) else 'VAZIO', v) for v in ('ANTHROPIC_API_KEY','ASAAS_API_TOKEN','ADVBOX_API_TOKEN','ZAPSIGN_API_TOKEN','ATENDE_DIREITO_TOKEN','PASTA_CLIENTES_RAIZ','ALERTA_WHATSAPP')]"
echo.
echo Checagem concluida - nada foi instalado nem alterado.

:fim
if not defined SEMPAUSA pause
endlocal

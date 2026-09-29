@echo off
REM =============================================================================
REM  Roda UMA rotina e grava a saida em logs\NOME.log. Usado pelo Agendador de
REM  Tarefas (deploy\agendar_tarefas_windows.bat), mas pode ser chamado a mao:
REM
REM    deploy\rodar_rotina.bat NOME_DO_LOG MODULO\main.py argumentos...
REM    deploy\rodar_rotina.bat financeiro_cobranca FINANCEIRO\main.py cobranca --enviar
REM
REM  Se o modulo ainda nao existir nesta maquina, registra no log e sai sem erro.
REM =============================================================================
setlocal
cd /d "%~dp0.."
set "LOG=%~1"
shift
set "SCRIPT=%~1"
if not exist logs mkdir logs

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "ARGS="
:junta
if "%~1"=="" goto roda
set "ARGS=%ARGS% %1"
shift
goto junta

:roda
>> "logs\%LOG%.log" echo.
>> "logs\%LOG%.log" echo ===== %date% %time% =====
if not exist "%SCRIPT%" (
  >> "logs\%LOG%.log" echo Modulo ainda nao instalado nesta maquina: %SCRIPT% - nada feito.
  endlocal & exit /b 0
)
"%PY%" %ARGS% >> "logs\%LOG%.log" 2>&1
set RC=%errorlevel%
>> "logs\%LOG%.log" echo ----- fim, codigo %RC%
endlocal & exit /b %RC%

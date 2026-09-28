@echo off
REM Agenda o acompanhamento da fase de contratacao 3x ao dia (9h, 13h e 17h):
REM confere assinaturas no ZapSign, baixa os assinados e cobra documentos pelo WhatsApp.
REM Rodar UMA vez, como administrador, dentro da pasta do projeto.

set PASTA=%~dp0..
set PY=python

for %%H in (09 13 17) do (
  schtasks /Create /F /SC DAILY /ST %%H:00 /TN "Caldeira Contratacao %%H" ^
    /TR "cmd /c cd /d \"%PASTA%\" && %PY% CONTRATACAO\main.py acompanhar --enviar >> logs\acompanhamento.log 2>&1"
)
if not exist "%PASTA%\logs" mkdir "%PASTA%\logs"
echo Agendado. Conferir em: Agendador de Tarefas ^> "Caldeira Contratacao"
pause

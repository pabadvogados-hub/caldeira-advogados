@echo off
REM =============================================================================
REM  SUBSTITUIDO por deploy\agendar_tarefas_windows.bat, que agenda TODAS as rotinas
REM  (inclusive o acompanhamento da contratacao 3x ao dia, 9h, 13h e 17h) na pasta
REM  "Caldeira" do Agendador e apaga as tarefas antigas "Caldeira Contratacao 09/13/17".
REM  Mantido so para quem seguir o passo antigo do docs\ONBOARDING.md.
REM =============================================================================
call "%~dp0agendar_tarefas_windows.bat" %*

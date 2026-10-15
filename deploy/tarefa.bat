@echo off
rem Roda um comando do manage.py pelo Agendador de Tarefas, com a saída em logs\agendador.log.
rem Exemplo: deploy\tarefa.bat importar_estoque
setlocal
cd /d "%~dp0.."
if not defined TAREFA_LOG set "TAREFA_LOG=%CD%\logs\agendador.log"
echo === %DATE% %TIME% %* ===>> "%TAREFA_LOG%"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" manage.py %* >> "%TAREFA_LOG%" 2>&1
exit /b %ERRORLEVEL%

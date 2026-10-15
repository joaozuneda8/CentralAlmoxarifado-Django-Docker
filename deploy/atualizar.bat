@echo off
rem Atualiza o Central Almoxarifado no servidor e reinicia o serviço (rode como administrador).
rem Para antes de tudo se houver robô em andamento: o reinício o mataria no meio.
setlocal
cd /d "%~dp0.."
rem O cmd lê o bloco inteiro antes de executar, e o git pull pode trocar este arquivo no meio.
(
  ".venv\Scripts\python.exe" manage.py robos_em_andamento || goto :falha
  git pull --ff-only || goto :falha
  uv sync --frozen --no-dev || goto :falha
  ".venv\Scripts\python.exe" manage.py migrate --noinput || goto :falha
  ".venv\Scripts\python.exe" manage.py collectstatic --noinput || goto :falha
  ".venv\Scripts\python.exe" manage.py check --deploy --fail-level WARNING || goto :falha
  ".venv\Scripts\python.exe" manage.py robos_em_andamento || goto :falha
  nssm restart CentralAlmoxarifado || goto :falha
  echo Atualizado.
  exit /b 0
)
:falha
echo Atualização interrompida: corrija o erro acima e rode de novo.
exit /b 1

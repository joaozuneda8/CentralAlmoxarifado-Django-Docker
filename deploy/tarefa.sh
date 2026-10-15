#!/usr/bin/env bash
# Roda um comando do manage.py pelo agendador do compose, com a saída em dados/logs/agendador.log.
# Exemplo: deploy/tarefa.sh importar_estoque
# Sem "set -e": o código de saída do comando é lido depois e devolvido.
set -u
cd "$(dirname "$0")/.."
log="${TAREFA_LOG:-/dados/logs/agendador.log}"
echo "=== $(date '+%d/%m/%Y %H:%M:%S') $* ===" >> "$log"
PYTHONIOENCODING=utf-8 "${TAREFA_PYTHON:-python}" manage.py "$@" >> "$log" 2>&1
exit $?

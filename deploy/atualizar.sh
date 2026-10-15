#!/usr/bin/env bash
# Atualiza o Central Almoxarifado no servidor e recria os containers. Rode da pasta do sistema:
#   bash deploy/atualizar.sh
# Para antes de tudo se houver robô em andamento: recriar o web o mataria no meio.
set -eu
cd "$(dirname "$0")/.."

trap 'status=$?; if [ "$status" -ne 0 ]; then echo "Atualização interrompida: corrija o erro acima e rode de novo." >&2; fi' EXIT

# O bash lê o script aos poucos, e o git pull pode trocar este arquivo no meio: o corpo fica
# numa função, lida inteira antes de rodar.
atualizar() {
  docker compose run --rm web python manage.py robos_em_andamento
  git pull --ff-only
  docker compose build
  docker compose run --rm web python manage.py migrate --noinput
  docker compose run --rm web python manage.py check --deploy --fail-level WARNING
  docker compose run --rm web python manage.py robos_em_andamento
  docker compose up -d
  echo "Atualizado."
}

atualizar "$@"

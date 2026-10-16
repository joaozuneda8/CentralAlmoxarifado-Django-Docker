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
  # Avisa, sem parar, das variáveis do arquivo de exemplo que o arquivo real não tem.
  avisar_variaveis_novas() {
    local exemplo="$1" real="$2" faltam
    [ -f "$exemplo" ] || return 0
    faltam=$(comm -23 \
      <(sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' "$exemplo" | sort -u) \
      <(sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' "$real" 2>/dev/null | sort -u) | tr '\n' ' ')
    if [ -n "$faltam" ]; then
      echo "AVISO: o $exemplo tem variável nova que falta no $real: $faltam" >&2
      echo "       Confira o $exemplo e acrescente ao $real antes de depender delas." >&2
    fi
  }

  docker compose run --rm web python manage.py robos_em_andamento
  git pull --ff-only
  avisar_variaveis_novas .env.example .env
  avisar_variaveis_novas .env.banco.example .env.banco
  docker compose build
  docker compose run --rm web python manage.py migrate --noinput
  docker compose run --rm web python manage.py check --deploy --fail-level WARNING
  docker compose run --rm web python manage.py robos_em_andamento
  docker compose up -d
  echo "Atualizado."
}

atualizar "$@"

#!/usr/bin/env bash
# Setup do ambiente de nuvem do Claude Code (claude.ai/code) para este projeto.
# Copie este conteúdo para o "setup script" do ambiente. Roda em Ubuntu/Debian.
#
# Instala o MariaDB (os testes nunca usam SQLite), as bibliotecas que o mysqlclient compila,
# o uv e o Python 3.13; cria o banco, o usuário e o .env de desenvolvimento, e roda as
# migrations. Não instala o Chromium do Playwright: os testes nunca abrem o navegador, e a
# nuvem não alcança o SCPI. A senha abaixo vale só para o banco local descartável da nuvem.
set -euo pipefail

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

DB_SENHA="almox-nuvem-local"

$SUDO apt-get update -qq
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq \
  mariadb-server mariadb-client libmariadb-dev pkg-config build-essential

# Sem systemd no contêiner: tenta o serviço e, se não subir, o mysqld_safe em segundo plano.
$SUDO service mariadb start || $SUDO service mysql start || ($SUDO mysqld_safe >/dev/null 2>&1 &)
for _ in $(seq 1 30); do
  $SUDO mariadb -e "SELECT 1" >/dev/null 2>&1 && break
  sleep 1
done

$SUDO mariadb <<SQL
CREATE DATABASE IF NOT EXISTS almoxarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'almox'@'localhost' IDENTIFIED BY '${DB_SENHA}';
CREATE USER IF NOT EXISTS 'almox'@'127.0.0.1' IDENTIFIED BY '${DB_SENHA}';
GRANT ALL PRIVILEGES ON almoxarifado.* TO 'almox'@'localhost', 'almox'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`test\_almoxarifado\`.* TO 'almox'@'localhost', 'almox'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# O resto só faz sentido dentro do repositório (o setup pode rodar antes do clone).
if [ -f manage.py ]; then
  if [ ! -f .env ]; then
    cat > .env <<ENV
SECRET_KEY=dev-nuvem-nao-usar-em-producao
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
USAR_HTTPS=0
PROXY_HTTPS=0
DB_NAME=almoxarifado
DB_USER=almox
DB_PASSWORD=${DB_SENHA}
DB_HOST=127.0.0.1
DB_PORT=3306
SCPI_HEADLESS=1
LANCAMENTO_REAL=0
ENV
  fi
  uv python install 3.13
  uv sync
  uv run python manage.py migrate --noinput
fi

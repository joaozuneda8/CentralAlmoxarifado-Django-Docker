# Comandos e testes

A fonte de verdade do projeto é o `CLAUDE.md` (raiz do repositório); esta nota só aponta o essencial.

- Dependências e execução: `uv sync`, `uv run python manage.py runserver`.
- Testes: `uv run pytest` (usa `config.settings_test` e cria o banco `test_almoxarifado`; exige MySQL/MariaDB, nunca SQLite).
- Lint e formato: `uv run ruff check . && uv run ruff format --check .`.
- Migrations: `uv run python manage.py makemigrations --check --dry-run`.
- Nunca rodar sem pedido: `lancar_saidas` sem `--dry-run` (lança de verdade no SCPI, só com `LANCAMENTO_REAL=1`), importadores do SCPI (abrem o navegador) e `migrate` contra o banco real.
- Nomes de código, textos e commits em português (pt-BR).

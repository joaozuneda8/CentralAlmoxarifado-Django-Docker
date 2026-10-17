# Central Almoxarifado (Django)

Nova versão do sistema de requisições do almoxarifado SAEP, em Django, sem
dependência da plataforma Google. Substitui o Central Almoxarifado em Google
Apps Script.

Design: [docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md](docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md)
(spec principal; as decisões posteriores estão nas outras specs de `docs/superpowers/specs/` e
de `specs/`). Guia de desenvolvimento e arquitetura: [CLAUDE.md](CLAUDE.md). Pendências
conhecidas: issues do GitHub.

## O que tem

- **Formulários públicos** (`/`, sem login): "Limpeza, copa e escritório" e "Ferramentas, peças
  e materiais" (o pedido AB, limitado ao estoque do SCPI). Cada pedido novo avisa no Telegram
  (`TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` no `.env`).
- **Área do almoxarifado** (`/painel/`, login por matrícula): painel com filtros,
  atendimento dos pedidos (com troca e acréscimo de materiais), edição do atendimento até o robô
  lançar o lote, saída avulsa, recibo impresso do detalhe do pedido, a página Automações (as
  importações do SCPI e o lançamento) e a Curva ABC (curvas por frequência e por valor,
  reposição e pares de/para). Cada saída vira linhas que o robô do SCPI lança depois.
- **Cadastros** (`/admin/`): centros de custo, opções, itens de limpeza, pares de/para,
  parâmetros da curva e as contas de usuário.

| Endereço | O quê |
|---|---|
| `/` | escolha do formulário público |
| `/pedido/limpeza/`, `/pedido/ab/` | os dois formulários públicos |
| `/painel/entrar/` | login da área do almoxarifado |
| `/painel/` | painel de pedidos (filtros, atalhos, cartão do lançamento) |
| `/painel/pedidos/<número>/` | detalhe, com o atendimento (`atender/`) e a edição (`editar/`) |
| `/painel/saida-avulsa/` | saída avulsa |
| `/painel/automacoes/` | Automações: visão geral, robôs do SCPI e histórico |
| `/painel/catalogo/curva/` | Curva ABC |
| `/admin/` | cadastros (só equipe) |

Atrás do Apache, todos esses endereços ganham o prefixo `/almoxarifado`.

## Desenvolvimento

Pré-requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/) e um MySQL 8 ou MariaDB local.

1. Crie o banco e o usuário (num cliente `mysql`/`mariadb` como root). O usuário também
   precisa do banco `test_almoxarifado`, que o pytest cria e apaga. O `DB_HOST` padrão é
   `127.0.0.1` (TCP), por isso o usuário existe também para esse endereço. No `GRANT`, o `_`
   é curinga e por isso vai escapado:

   ```sql
   CREATE DATABASE almoxarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'almox'@'localhost' IDENTIFIED BY '<senha local>';
   CREATE USER 'almox'@'127.0.0.1' IDENTIFIED BY '<senha local>';
   GRANT ALL PRIVILEGES ON almoxarifado.* TO 'almox'@'localhost', 'almox'@'127.0.0.1';
   GRANT ALL PRIVILEGES ON `test\_almoxarifado`.* TO 'almox'@'localhost', 'almox'@'127.0.0.1';
   ```

2. Copie `.env.example` para `.env` e preencha ao menos `DB_PASSWORD`.
3. Instale e prepare:

   ```bash
   uv sync
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   uv run python manage.py runserver
   ```

4. Testes e lint:

   ```bash
   uv run python manage.py collectstatic --noinput   # o teste com a configuração de produção lê o manifesto
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run python manage.py makemigrations --check --dry-run
   ```

   Os quatro últimos precisam passar limpos antes do merge. O `collectstatic` só é preciso de
   novo depois de mexer em estáticos: sem ele, o
   `test_config.py::test_atras_do_apache_com_waitress_documentado_nao_entra_em_laco` falha com a
   entrada que falta no manifesto de `staticfiles/`.

5. Importações do SCPI (precisam de `SAEP_USER` e `SAEP_PASS` no `.env` e do Chromium do
   Playwright, instalado uma vez com `uv run playwright install chromium`):

   ```bash
   uv run python manage.py importar_cadastro
   uv run python manage.py importar_estoque
   uv run python manage.py importar_saidas_scpi --desde 01/01/2026
   uv run python manage.py atualizar_catalogo      # as três em sequência
   uv run python manage.py atualizar_catalogo --carga-inicial   # cadastro inteiro e saídas desde 01/01/2026
   ```

   Com `--arquivo <csv>`, cada comando lê um CSV já baixado do SCPI em vez de abrir o
   navegador (os de exemplo ficam em `tests/fixtures/scpi/`). O resultado de cada execução
   aparece em Automações (aba Visão geral e histórico).

6. Lançamento das saídas no SCPI (mesmos requisitos do item anterior):

   ```bash
   uv run python manage.py lancar_saidas --dry-run --limite 1   # só simula
   uv run python manage.py lancar_saidas                        # lança de verdade
   ```

   **Atenção:** `lancar_saidas` sem `--dry-run` lança de verdade no SCPI, uma requisição por
   lote de saída `PENDENTE`. Sem `LANCAMENTO_REAL=1` no `.env` (o padrão), o lançamento real
   fica bloqueado no comando, na página e no painel: só a simulação roda. Com `--dry-run`, o
   navegador abre, preenche a requisição e a descarta sem salvar, e nenhuma linha muda. O mesmo
   pode ser feito pela página Automações (aba Lançamento no SCPI), que também mostra o andamento e
   resolve os lotes que o robô deixou para conferência. O registro de cada lançamento fica em
   `logs/lancar_saidas_journal.jsonl`.

## Implantação

O sistema roda em Docker Compose (`compose.yaml`), atrás do Apache em `/almoxarifado`: o
`banco` (MariaDB), o `web` (waitress, que também dispara os robôs da página) e o `agendador`
(supercronic com `deploy/crontab`: importações e backup). No servidor, os comandos rodam no
container: `docker compose exec web python manage.py <comando>`.

- [deploy/INSTALACAO.md](deploy/INSTALACAO.md): instalação (Linux ou WSL2), `.env` de produção,
  Apache, agendador, backup e atualização (`bash deploy/atualizar.sh`), para quem administra o
  servidor.
- [deploy/VIRADA.md](deploy/VIRADA.md): roteiro da migração do Apps Script e da virada, com a
  situação de cada passo. Falta só liberar o lançamento real e conferir o primeiro.

Coisas a saber (no servidor, sempre pelo container):

- `LANCAMENTO_REAL` (no `.env`, padrão `0`) libera o lançamento real no SCPI; com `0`, só a
  simulação roda. Ele separou o Django do Apps Script no período em paralelo; o robô antigo já
  foi desativado, e a liberação é `LANCAMENTO_REAL=1` no `.env` do servidor seguido de
  `docker compose up -d` (`deploy/VIRADA.md`, seção 6). Até lá, nenhum robô lança no SCPI.
- `docker compose exec web python manage.py backup_banco` grava o dump comprimido em
  `BACKUP_DIR` e apaga os com mais de 60 dias (roda todo dia pelo agendador do compose).
- `docker compose run --rm web python manage.py robos_em_andamento` sai com erro se há robô
  rodando: recriar o `web` o mataria (o `deploy/atualizar.sh` confere antes).
- `importar_planilhas --arquivo <xlsx> [--dry-run]` (migração única das planilhas do Apps Script)
  e `importar_depara --arquivo <xlsx> [--dry-run]` (carga única dos pares de/para) já cumpriram
  seu papel: o primeiro recusa porque o banco tem pedidos feitos no Django, e o segundo, se há par
  criado ou alterado no admin depois da carga. Os pares agora são mantidos em Cadastros.

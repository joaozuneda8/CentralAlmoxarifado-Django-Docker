# Implantação em Docker

Data: 2026-10-15. Substitui a implantação no Windows (serviço NSSM, Agendador de Tarefas,
`.bat`) descrita na seção 8 da spec principal
(`2026-10-10-central-almoxarifado-django-design.md`). O código da aplicação, a migração das
planilhas e a virada (`deploy/VIRADA.md`) continuam como estão; muda o que roda o sistema.

## 1. Objetivo

O sistema passa a ser implantado só por Docker Compose: uma imagem com o Django, o waitress, o
Chromium do Playwright e o cliente do MariaDB; o banco num container MariaDB; as tarefas
agendadas num container próprio. O servidor só precisa de Docker e do Apache que já termina o
HTTPS. O caminho Windows (NSSM, Agendador, `.bat`) é removido.

### Decisões tomadas

- **Produção no lugar do Windows**: o `deploy/` passa a descrever só o Docker.
- **Banco no compose**: MariaDB 11.4 (LTS) em container, com volume próprio; o sistema deixa de
  depender do banco do ProducaoLab.
- **HTTPS no Apache que já existe**: o container do sistema só atende HTTP numa porta publicada;
  o Apache continua com o certificado e o `ProxyPass /almoxarifado`.
- **Máquina ainda indefinida**: o compose é neutro (endereço e porta publicados vêm do `.env`) e
  o guia cobre os dois casos: VM ou servidor Linux (Apache encaminha para o IP da VM) e Windows
  Server com Docker Engine no WSL2 (Apache encaminha para `127.0.0.1`).
- **Agendador no compose** (abordagem A): um container com a mesma imagem roda o supercronic
  com um `crontab` versionado. Descartadas: o cron do servidor chamando `docker compose exec`
  (horários fora do repositório, diferentes em Linux e WSL2) e uma fila de tarefas
  (Celery/Redis, subsistema novo sem ganho para três tarefas e um botão).

### Fora do escopo

- Desenvolvimento local em Docker: continua `uv` + MySQL/MariaDB local, como no CLAUDE.md.
- Testes dentro do container: a suíte segue rodando localmente.
- Proxy reverso ou certificado dentro do compose.
- Orquestradores (Kubernetes, Swarm) e registro de imagens: a imagem é construída no servidor
  (`docker compose build`).

## 2. Arquitetura

```
navegador ──HTTPS──> Apache (certificado, /almoxarifado)
                        │ HTTP
                        ▼
              ${PORTA_PUBLICADA} ──> web (waitress :8010) ──Popen──> robôs da página
                                       │
               agendador (supercronic) ┼──> manage.py importar_estoque / atualizar_catalogo / backup_banco
                                       ▼
                                 banco (MariaDB, sem porta publicada)
```

### Imagem (`Dockerfile`)

- Base `python:3.13-slim-bookworm` (o projeto exige a série 3.13), com o `uv` copiado da imagem
  oficial (`ghcr.io/astral-sh/uv`, versão fixada).
- Dependências: `uv sync --frozen --no-dev` num `.venv` dentro da imagem (`/app/.venv`, no
  `PATH`). O `mysqlclient` compila no build: a etapa de build tem `build-essential`,
  `pkg-config` e `libmariadb-dev`; a imagem final só a biblioteca de execução (`libmariadb3`).
- `mariadb-client` na imagem final, para o `backup_banco` (`MYSQLDUMP=mariadb-dump`) e a
  restauração.
- Chromium: `playwright install --with-deps chromium` com `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`.
  O Playwright já abre o Chromium com `--no-sandbox` (padrão do `chromiumSandbox`), o que
  dispensa privilégios extras no container.
- supercronic (binário fixado por versão e conferido pelo SHA-1 publicado).
- `collectstatic --noinput` no build, com uma `SECRET_KEY` descartável só para esse comando: o
  manifesto não depende do `PREFIXO_URL` (só o `STATIC_URL`, lido na partida, depende).
- Usuário sem privilégios `almox` (UID fixo 1000). O código e o `.venv` pertencem ao root e
  ficam só para leitura, como hoje com a conta `svc-almoxarifado`; o `almox` escreve só em
  `/dados` (logs, perfil do navegador, backups).
- `.dockerignore`: `.env`, `.venv`, `.git`, `logs/`, `dados/`, `.pw-profile/`, `staticfiles/`,
  `tests/`, `docs/`, `specs/`, `.specify/`, `.claude/`.
- `ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 TZ=America/Sao_Paulo`.

### Compose (`compose.yaml`)

Três serviços, todos `restart: unless-stopped`, e `env_file: .env` nos dois da aplicação.

- `banco`: `mariadb:11.4`, com `--character-set-server=utf8mb4
  --collation-server=utf8mb4_unicode_ci`. Banco, usuário e senhas vêm do `.env`
  (`MARIADB_DATABASE`=`DB_NAME`, `MARIADB_USER`=`DB_USER`, `MARIADB_PASSWORD`=`DB_PASSWORD`,
  `MARIADB_ROOT_PASSWORD` próprio). Volume nomeado `banco-dados`. **Nenhuma porta publicada.**
  Healthcheck com o `healthcheck.sh --connect --innodb_initialized` da imagem oficial.
- `web`: o waitress
  `--listen=0.0.0.0:8010 --threads=8 --url-prefix=${PREFIXO_URL} --trusted-proxy=*
  --trusted-proxy-headers="x-forwarded-proto x-forwarded-for" config.wsgi:application`,
  publicado em `${PORTA_PUBLICADA:-127.0.0.1:8010}:8010`. Depende do `banco` saudável.
  `init: true` (o tini recolhe os processos que terminam) e `shm_size: 1gb` (o Chromium usa
  `/dev/shm`). Os robôs disparados pela página continuam processos filhos do waitress
  (`scpi/disparo.py`), dentro deste container.
- `agendador`: a mesma imagem, comando `supercronic /app/deploy/crontab`, com os mesmos volumes
  e `init: true`/`shm_size` do `web`.

O compose força, por cima do `.env`: `DB_HOST=banco`, `DB_PORT=3306`, `SCPI_HEADLESS=1`,
`MYSQLDUMP=mariadb-dump`, `LOG_DIR=/dados/logs`, `BACKUP_DIR=/dados/backups`,
`SCPI_PERFIL_DIR=/dados/perfil`.

Volumes:

| Onde | O quê | Por quê |
|---|---|---|
| `./dados/logs` → `/dados/logs` | logs, CSVs enviados, journal do lançamento | o André lê do host |
| `./dados/backups` → `/dados/backups` | dumps diários (também o manual pelo `web`) | copiar para outra máquina |
| `./dados/importacao` → `/dados/importacao:ro` (só `web`) | `.xlsx` da virada | `importar_planilhas`, `importar_depara` |
| volume `perfil-navegador` → `/dados/perfil` | perfis do Chromium | comum a `web` e `agendador` |
| volume `banco-dados` | dados do MariaDB | |

As pastas `dados/logs` e `dados/backups` do host precisam ser do UID 1000 (`chown -R
1000:1000 dados/logs dados/backups`), senão o `almox` não grava; o guia manda criá-las assim
antes do primeiro `up`. `dados/` entra no `.gitignore`.

O perfil comum é seguro: cada tipo de importação e o lançamento usam subpastas próprias, e as
travas `GET_LOCK` (no banco, portanto valem entre containers) impedem duas execuções do mesmo
tipo. O journal `lancar_saidas_journal.jsonl` fica em `/dados/logs`, fora do container, e
sobrevive a uma reconstrução.

### Proxy e IPs

- O waitress confia em qualquer origem (`--trusted-proxy=*`): atrás do Docker, o Apache chega
  ao container por um IP interno que muda, e o waitress só aceita um IP fixo ou `*`. Isso só é
  seguro porque a porta publicada só é alcançável pelo Apache:
  - mesmo servidor (WSL2): `PORTA_PUBLICADA=127.0.0.1:8010`;
  - VM Linux: `PORTA_PUBLICADA=<ip da VM na rede do Apache>:8010` e o firewall liberando só o
    IP do Apache. O guia avisa que o Docker abre portas publicadas por cima do `ufw`/`firewalld`
    (a regra vai na cadeia `DOCKER-USER`), e que `0.0.0.0` exporia o sistema sem HTTPS.
- `PROXY_HTTPS=1` e `USAR_HTTPS=1` continuam obrigatórios (`check --deploy` sem avisos).

### Agendador (`deploy/crontab`)

Os horários de hoje, no fuso `America/Sao_Paulo` (`TZ` da imagem):

```
*/30 7-16 * * 1-5  estoque          (07:00 a 16:30, dias úteis)
0 17 * * 1-5       estoque          (17:00)
30 6 * * *         atualizar_catalogo
0 23 * * *         backup_banco
```

Cada linha chama `/app/deploy/tarefa.sh <comando>`, que acrescenta ao
`/dados/logs/agendador.log` o cabeçalho `=== <data e hora> <comando> ===` e a saída do
`manage.py`, e devolve o código de saída do comando (equivalente ao `tarefa.bat`).

### Mudanças no código

- `scpi/disparo.py`: fora do Windows, `subprocess.Popen(..., start_new_session=True)`, o
  paralelo do `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`: o robô não recebe o Ctrl+C nem o
  SIGHUP do grupo do waitress. Parar ou recriar o container `web` ainda mata os robôs dele; por
  isso o `atualizar.sh` confere `robos_em_andamento` antes.
- `.env.example`: entram `PORTA_PUBLICADA` e `MARIADB_ROOT_PASSWORD`; saem as variáveis que o
  compose define (`DB_HOST`, `DB_PORT`, `SCPI_HEADLESS`, `SCPI_PERFIL_DIR`,
  `PLAYWRIGHT_BROWSERS_PATH`, `LOG_DIR`, `BACKUP_DIR`, `MYSQLDUMP`), com uma nota de que o
  desenvolvimento local ainda pode defini-las. O `settings.py` não muda: todas já são lidas do
  ambiente.

## 3. Operação

### `deploy/atualizar.sh`

Bash, `set -eu`, rodado da raiz do repositório no host (Linux ou WSL2). O corpo fica numa função
chamada na última linha (o bash lê o script aos poucos e o `git pull` pode trocá-lo no meio):

1. `docker compose run --rm web python manage.py robos_em_andamento` (com `run`, e não `exec`, funciona também com o `web` parado)
2. `git pull --ff-only`
3. `docker compose build`
4. `docker compose run --rm web python manage.py migrate --noinput`
5. `docker compose run --rm web python manage.py check --deploy --fail-level WARNING`
6. `docker compose run --rm web python manage.py robos_em_andamento`
7. `docker compose up -d`

Para no primeiro erro com a mensagem "Atualização interrompida: corrija o erro acima e rode de
novo." O `collectstatic` saiu da lista porque roda no build.

### Guias

- `deploy/INSTALACAO.md`, reescrito: requisitos (Docker Engine e o plugin compose; em Linux
  pelo repositório oficial; em Windows Server 2022+ pelo WSL2 com systemd, com o aviso de que o
  Docker Desktop não é suportado em Windows Server e exige licença paga em empresa grande);
  WSL2 subindo com o servidor (tarefa de inicialização que roda `wsl -d <distro> --exec true`);
  clonar o repositório; `.env`; `docker compose up -d`; `migrate`; `createsuperuser`;
  `check --deploy`; Apache (`ProxyPass` para `127.0.0.1:8010` ou para o IP da VM); backup e
  restauração (`gunzip -c <arquivo> | docker compose exec -T banco mariadb -u root -p...`);
  atualização; conferência final (login, "Atualizar agora", "Simular", backup, `docker compose
  ps` com os três serviços saudáveis, logs em `dados/logs`).
- `deploy/VIRADA.md`: os comandos `.venv\Scripts\python.exe manage.py ...` viram
  `docker compose exec web python manage.py ...`, e os `.xlsx` ficam em `dados/importacao/`
  (no container, `/dados/importacao/`). Ordem e conteúdo não mudam.
- `README.md` e `CLAUDE.md`: os trechos sobre NSSM, `.bat`, Agendador e "no servidor os `.bat`
  chamam o Python do `.venv`" passam a descrever o compose; a seção 8 da spec principal ganha um
  apontamento para esta spec.

### Removidos

`deploy/atualizar.bat`, `deploy/tarefa.bat`, `deploy/tarefa-estoque.xml` e os testes deles.

## 4. Testes

Em `tests/test_scripts_servidor.py` (os de `robos_em_andamento` ficam):

- `crontab`: o estoque roda de 30 em 30 minutos das 07:00 às 17:00 só de segunda a sexta; o
  catálogo às 06:30 e o backup às 23:00 todos os dias; toda linha passa por `tarefa.sh`.
- `tarefa.sh`: grava o cabeçalho e devolve o código de saída do comando (roda num `bash` com um
  `manage.py` falso; pulado onde não há `bash`).
- `atualizar.sh`: `set -eu`; corpo numa função chamada na última linha; `robos_em_andamento`
  antes do `git pull` e de novo antes do `up -d`; `migrate` e `check --deploy` antes do `up`.
- `compose.yaml`: o `banco` não tem `ports`; o `web` publica `${PORTA_PUBLICADA...}`; o
  `--url-prefix` do waitress é o `PREFIXO_URL`. Os testes leem o texto (sem `pyyaml` novo).
- `Dockerfile`: Python 3.13, `--no-dev`, `collectstatic`, `USER` diferente de root.
- `scpi/disparo.py`: fora do Windows, o `Popen` recebe `start_new_session=True` (com o `Popen`
  substituído por um falso).

A suíte inteira, o `ruff` e o `makemigrations --check` continuam passando localmente.

### Conferência manual (precisa de Docker)

Esta máquina de desenvolvimento não tem Docker; a imagem só é construída onde houver. Quem
tiver Docker confere, antes da instalação no servidor:

1. `docker compose build` termina sem erro.
2. `docker compose up -d`, `migrate`, `createsuperuser`; `docker compose ps` mostra os três
   serviços, o `banco` saudável.
3. Com `DEBUG=0`, `USAR_HTTPS=0`, `PREFIXO_URL=/almoxarifado`: `http://127.0.0.1:8010/almoxarifado/`
   abre o formulário com estilo e o login entra.
4. Em Automações, "Simular" abre o SCPI sem janela e termina (com credenciais do SCPI).
5. `docker compose exec agendador /app/deploy/tarefa.sh backup_banco` gera o
   `.sql.gz` em `dados/backups`, e ele restaura num banco de teste.
6. Com um robô em andamento (uma simulação disparada pela página), o `atualizar.sh` para no
   primeiro passo, sem `git pull`.

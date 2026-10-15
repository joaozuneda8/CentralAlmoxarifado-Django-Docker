# Instalação do Central Almoxarifado no servidor

Guia para o André. O sistema roda neste servidor Windows como um serviço (waitress, por trás do
Apache) e três tarefas do Agendador. Siga as seções na ordem. Os comandos são para o `cmd.exe`
aberto **como administrador**, salvo onde disser o contrário. Texto entre `<` e `>` é para você
trocar (senhas, nomes); nunca guarde senha neste arquivo.

Nas mensagens dos `.bat` os acentos podem aparecer trocados no console. É só aparência, não
atrapalha.

## 1. Requisitos

- Windows Server com **Git**, **Python 3.13** e **uv**.
  - Python 3.13 do python.org (a série 3.13; o sistema não aceita outra), instalado **para todos
    os usuários** (opção "Install for all users", que o põe em `C:\Program Files`) e com o
    "Add python.exe to PATH" marcado. Python instalado só no seu perfil não serve: a conta do
    serviço (seção 2) não conseguiria abri-lo.
  - uv: instalador oficial, ou `winget install astral-sh.uv`.
  - Git: o instalador oficial.

  Diga ao `uv` para usar sempre esse Python e para **copiar** os arquivos das bibliotecas em vez
  de ligá-los ao cache do seu usuário. Sem isto, o Python e as bibliotecas do sistema ficariam na
  sua pasta de usuário, que a conta do serviço não lê. Rode uma vez, como administrador:

  ```bat
  setx /M UV_PYTHON_DOWNLOADS never
  setx /M UV_LINK_MODE copy
  setx /M UV_PYTHON_PREFERENCE only-system
  ```

  - `UV_PYTHON_DOWNLOADS=never`: o `uv` nunca baixa um Python próprio (ele iria para o seu
    `%APPDATA%`); usa o do python.org.
  - `UV_PYTHON_PREFERENCE=only-system`: o `uv` só considera Pythons instalados no sistema. Sem
    esta, um Python que o `uv` já tenha baixado no perfil do administrador ainda seria escolhido
    para o `.venv`, e a conta do serviço não o leria.
  - `UV_LINK_MODE=copy`: o `.venv` recebe cópias dos arquivos, que herdam a permissão da pasta do
    sistema (seção 2), e não ligações ao cache do `uv` no seu `%LOCALAPPDATA%`.

  **Feche e abra um novo `cmd.exe` como administrador** (as variáveis só valem em terminais
  novos) e confira:

  ```bat
  git --version
  uv --version
  python --version
  where python
  ```

  `python --version` tem de mostrar 3.13.x, e o primeiro caminho de `where python` tem de estar
  em `C:\Program Files`. Se não estiver, corrija o `PATH` antes de seguir.
- **NSSM** no `PATH` (`nssm version` precisa responder).
- O **MySQL/MariaDB do ProducaoLab** e o programa de dump dele: `mysqldump` (MySQL 8) ou
  `mariadb-dump` (MariaDB). Anote qual é o servidor: ele define qual cliente usar na
  restauração (seção 9).
- O **Apache** do servidor, com `mod_proxy`, `mod_proxy_http` e `mod_headers` ligados (seção 7),
  **atendendo em HTTPS, com certificado**. É pré-requisito: os formulários ficam abertos fora da
  rede da SAEP e a área interna tem login, e o `atualizar.bat` confere a configuração de
  produção, que exige HTTPS (sem ele, toda atualização para no `check --deploy`).

## 2. Conta e pasta

1. Crie uma conta local dedicada, que roda o serviço e as tarefas. Ela não precisa ser
   administradora:

   ```bat
   net user svc-almoxarifado <senha> /add /expires:never
   ```

   Dê a ela os direitos "Fazer logon como serviço" e "Fazer logon como tarefa em lote"
   (`secpol.msc` > Diretivas Locais > Atribuição de Direitos de Usuário). Sem o segundo, o
   Agendador recusa as tarefas da seção 8.
2. Clone o repositório em `C:\CentralAlmoxarifado`. **O caminho não pode ter espaços**: os `.bat`
   e o Agendador dependem disso.

   ```bat
   git clone <endereço do repositório> C:\CentralAlmoxarifado
   ```

3. Crie as pastas de trabalho e dê à conta permissão de escrita. Escolha a pasta de backup
   (aqui `C:\CentralAlmoxarifado-backups`, fora do repositório) e a do Chromium:

   ```bat
   mkdir C:\CentralAlmoxarifado\logs
   mkdir C:\CentralAlmoxarifado\.pw-profile
   mkdir C:\CentralAlmoxarifado\staticfiles
   mkdir C:\CentralAlmoxarifado-backups
   mkdir C:\CentralAlmoxarifado-navegadores
   icacls C:\CentralAlmoxarifado /inheritance:r /grant:r *S-1-5-32-544:(OI)(CI)F *S-1-5-18:(OI)(CI)F svc-almoxarifado:(OI)(CI)RX
   icacls C:\CentralAlmoxarifado-navegadores /inheritance:r /grant:r *S-1-5-32-544:(OI)(CI)F *S-1-5-18:(OI)(CI)F svc-almoxarifado:(OI)(CI)RX
   icacls C:\CentralAlmoxarifado-backups /inheritance:r /grant:r *S-1-5-32-544:(OI)(CI)F *S-1-5-18:(OI)(CI)F svc-almoxarifado:(OI)(CI)M
   icacls C:\CentralAlmoxarifado\logs /grant:r svc-almoxarifado:(OI)(CI)M
   icacls C:\CentralAlmoxarifado\.pw-profile /grant:r svc-almoxarifado:(OI)(CI)M
   ```

   A conta só lê e executa o código, o `.venv` e o Chromium: se alguém conseguir rodar código
   pelo site, não consegue alterar o sistema. Ela escreve só em `logs\` (logs, CSVs enviados,
   journal do robô), em `.pw-profile\` (perfil do navegador dos robôs) e na pasta de backup. O
   `staticfiles\` é preenchido pelo `collectstatic`, que roda como administrador (seção 5 e
   `atualizar.bat`).

   O `/inheritance:r` corta a permissão que as pastas herdariam de `C:\`: lá, todo usuário
   autenticado ganha "Modificar" em tudo o que é criado (no Windows Server, criar arquivos), o
   que anularia o "só leitura" da conta, e qualquer usuário leria o backup do banco. Só ficam os
   administradores, o SYSTEM e a conta do serviço; os SIDs valem em qualquer idioma do Windows
   (seção 4). Por isso, depois disso, essas pastas (e os logs) só abrem num `cmd.exe` **como
   administrador**; sem elevação, o Windows nega o acesso (o Explorer oferece incluir o seu
   usuário na pasta, o que não é preciso).

   O `/grant:r` substitui a permissão que a conta já tinha em cada pasta, então os comandos podem
   ser repetidos num servidor já instalado. Não tire as permissões da conta recursivamente
   (`/remove /T`): o `.env` tem uma permissão própria, dada na seção 4, e o serviço pararia de
   subir.

   O primeiro `icacls` vale para tudo o que for criado depois dentro de `C:\CentralAlmoxarifado`,
   inclusive o `.venv` do `uv sync`, porque os arquivos são copiados (`UV_LINK_MODE=copy`, seção
   1) e herdam a permissão da pasta. Se você já tinha rodado o `uv sync` antes de ajustar as
   variáveis da seção 1, apague a pasta `.venv` e rode o `uv sync` de novo.

## 3. Banco

Num cliente `mysql` (ou `mariadb`) como root, no servidor de banco. Use uma senha forte e anote
(vai no `.env`, seção 4). Este é o SQL do README, sem o `GRANT` do `test_almoxarifado`, que só
serve para os testes:

```sql
CREATE DATABASE almoxarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'almox'@'localhost' IDENTIFIED BY '<senha forte>';
CREATE USER 'almox'@'127.0.0.1' IDENTIFIED BY '<senha forte>';
GRANT ALL PRIVILEGES ON almoxarifado.* TO 'almox'@'localhost', 'almox'@'127.0.0.1';
```

Se o banco ficar em outra máquina, crie também o usuário para o endereço do servidor do sistema
(`'almox'@'<ip deste servidor>'`) e use esse banco no `DB_HOST` do `.env`.

## 4. `.env` de produção

```bat
copy C:\CentralAlmoxarifado\.env.example C:\CentralAlmoxarifado\.env
notepad C:\CentralAlmoxarifado\.env
```

Valores de produção, variável por variável (as não citadas ficam como estão):

| Variável | Valor |
|---|---|
| `SECRET_KEY` | uma chave gerada, só deste servidor (comando abaixo) |
| `DEBUG` | `0` |
| `ALLOWED_HOSTS` | o nome pelo qual o site é acessado, sem esquema, ex.: `servidor.saep.local` |
| `CSRF_TRUSTED_ORIGINS` | o mesmo nome **com** esquema, ex.: `https://servidor.saep.local` |
| `USAR_HTTPS` | `1` (sempre: o `check --deploy` da seção 5 exige HTTPS) |
| `PROXY_HTTPS` | `1` (sempre, atrás do Apache; seção 7) |
| `PREFIXO_URL` | `/almoxarifado` (o mesmo do `--url-prefix` da seção 6); vazio se o site ficar na raiz |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `almoxarifado`, `almox` e a senha da seção 3 |
| `DB_HOST`, `DB_PORT` | `127.0.0.1` e `3306`, ou os do banco do ProducaoLab |
| `SAEP_USER`, `SAEP_PASS` | usuário e senha do SCPI usados pelos robôs |
| `SCPI_HEADLESS` | `1` (rodando como serviço não há janela) |
| `LANCAMENTO_REAL` | `0` até a virada (`deploy\VIRADA.md`): com `0`, só a simulação roda |
| `PLAYWRIGHT_BROWSERS_PATH` | `C:\CentralAlmoxarifado-navegadores` |
| `BACKUP_DIR` | `C:\CentralAlmoxarifado-backups` |
| `MYSQLDUMP` | `mysqldump` (MySQL 8) ou `mariadb-dump` (MariaDB); o caminho completo se não estiver no `PATH` |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | bot e chat que recebem o aviso de novo pedido; deixe **vazios** até a virada (`deploy\VIRADA.md`), senão um pedido de teste avisa o grupo de verdade |

Gerar a `SECRET_KEY` (rode depois do `uv sync` da seção 5, ou com qualquer Python):

```bat
C:\CentralAlmoxarifado\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Cada linha do `.env` é `NOME=valor`, sem aspas e sem espaços em volta do `=`. O arquivo tem
senhas: só a conta do serviço, os administradores e o SYSTEM devem lê-lo. O `icacls` abaixo usa os
SIDs (`*S-1-5-32-544` é o grupo Administradores e `*S-1-5-18` é o SYSTEM), que valem em qualquer
idioma do Windows; o nome "Administrators" não existe num Windows em português.

```bat
icacls C:\CentralAlmoxarifado\.env /inheritance:r /grant:r svc-almoxarifado:R *S-1-5-32-544:F *S-1-5-18:F
```

## 5. Instalação

```bat
cd /d C:\CentralAlmoxarifado
uv sync --frozen --no-dev
set PLAYWRIGHT_BROWSERS_PATH=C:\CentralAlmoxarifado-navegadores
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py collectstatic --noinput
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe manage.py check --deploy --fail-level WARNING
```

- O `set PLAYWRIGHT_BROWSERS_PATH` tem de ser o mesmo valor do `.env`: ele diz onde o Chromium
  fica, e o serviço e as tarefas o leem do `.env`.
- O `migrate` também cria a pasta `logs\`.
- O `createsuperuser` pede a matrícula (é o nome de usuário) e a senha do primeiro acesso.
- O último comando precisa terminar **sem avisos** (`System check identified no issues`). Se
  listar algum, corrija o `.env` antes de seguir; um aviso quase sempre é HTTPS, `SECRET_KEY` ou
  `ALLOWED_HOSTS`.

## 6. Serviço (NSSM)

```bat
nssm install CentralAlmoxarifado "C:\CentralAlmoxarifado\.venv\Scripts\python.exe"
nssm set CentralAlmoxarifado AppDirectory C:\CentralAlmoxarifado
nssm set CentralAlmoxarifado AppParameters "-m waitress --listen=127.0.0.1:8010 --threads=8 --url-prefix=/almoxarifado --trusted-proxy=127.0.0.1 --trusted-proxy-headers=\"x-forwarded-proto x-forwarded-for\" config.wsgi:application"
nssm set CentralAlmoxarifado ObjectName .\svc-almoxarifado <senha>
nssm set CentralAlmoxarifado AppStdout C:\CentralAlmoxarifado\logs\servico.log
nssm set CentralAlmoxarifado AppStderr C:\CentralAlmoxarifado\logs\servico.log
nssm set CentralAlmoxarifado AppKillProcessTree 0
nssm set CentralAlmoxarifado Start SERVICE_AUTO_START
nssm start CentralAlmoxarifado
```

- `AppKillProcessTree 0`: parar ou reiniciar o serviço não mata o robô que a página disparou
  (um processo filho), que termina o lançamento sozinho. Por isso o `atualizar.bat` confere
  antes se há robô em andamento.
- O `--url-prefix=/almoxarifado` da linha acima é o padrão (seção 7) e tem de bater com o
  `PREFIXO_URL` do `.env`. Se o site ficar na raiz, tire o `--url-prefix` e deixe o
  `PREFIXO_URL` vazio.
- Para conferir o que ficou gravado: `nssm get CentralAlmoxarifado AppParameters`.
- Depois de mudar o `.env`, reinicie: `nssm restart CentralAlmoxarifado`.

## 7. Apache

O padrão é o sistema em `/almoxarifado` do servidor, com o prefixo informado ao waitress (seção 6).
Endereços resultantes:

| O quê | Endereço |
|---|---|
| Formulários dos funcionários | `https://servidor/almoxarifado/` |
| Área do almoxarifado (login) | `https://servidor/almoxarifado/painel/` |
| Cadastros (admin) | `https://servidor/almoxarifado/admin/` |

No `httpd.conf` (ou no `VirtualHost` do site), dentro do bloco HTTPS:

```apache
ProxyPreserveHost On
RequestHeader set X-Forwarded-Proto "https"
ProxyPass /almoxarifado http://127.0.0.1:8010/almoxarifado
ProxyPassReverse /almoxarifado http://127.0.0.1:8010/almoxarifado
```

Depois, teste a configuração e recarregue o Apache (`httpd -t` e `httpd -k restart`, ou o
serviço do Apache nos Serviços do Windows).

Se um dia o site ganhar um nome próprio na rede, sem o prefixo: tire o `--url-prefix` do serviço,
deixe o `PREFIXO_URL` vazio e use `ProxyPass / http://127.0.0.1:8010/` (e `ProxyPassReverse /
http://127.0.0.1:8010/`).

Nos dois casos:

- `ProxyPreserveHost On`: o link "Abrir painel" do aviso no Telegram usa o host da requisição.
- `RequestHeader set X-Forwarded-Proto "https"` e, no `.env`, `USAR_HTTPS=1` e `PROXY_HTTPS=1`:
  sempre os três, o Apache é HTTPS (seção 1).
- O waitress precisa das opções `--trusted-proxy...` da seção 6. Sem
  `x-forwarded-proto`, o redirecionamento para HTTPS entra em laço; sem `x-forwarded-for`, todo
  pedido parece vir do Apache e **todos os funcionários dividem o mesmo limite por IP** (três
  pedidos em 10 minutos para o prédio inteiro).

## 8. Agendador de Tarefas

Crie as tarefas **só depois do `migrate` da seção 5**: é ele que cria a pasta `logs\`, e o
`tarefa.bat` grava em `logs\agendador.log`.

Três tarefas, rodando como a conta do serviço, com "executar estando o usuário conectado ou
não" (é o que o `/RU ... /RP *` faz; ele pede a senha da conta uma vez por tarefa):

```bat
schtasks /Create /TN "Central Almoxarifado\Estoque" /XML C:\CentralAlmoxarifado\deploy\tarefa-estoque.xml /RU .\svc-almoxarifado /RP *
schtasks /Create /TN "Central Almoxarifado\Catalogo" /TR "C:\CentralAlmoxarifado\deploy\tarefa.bat atualizar_catalogo" /SC DAILY /ST 06:30 /RU .\svc-almoxarifado /RP *
schtasks /Create /TN "Central Almoxarifado\Backup" /TR "C:\CentralAlmoxarifado\deploy\tarefa.bat backup_banco" /SC DAILY /ST 23:00 /RU .\svc-almoxarifado /RP *
```

- Estoque: de segunda a sexta, a cada 30 minutos entre 07:00 e 17:01. O horário está em
  `deploy\tarefa-estoque.xml` e não no comando porque o `/D` do `schtasks` usa os nomes dos dias
  no idioma do Windows (`MON,TUE,...` é recusado num Windows em português).
- Catálogo: todo dia às 06:30 (cadastro, estoque e saídas do SCPI, em sequência).
- Backup: todo dia às 23:00.

O resultado das importações aparece em Automações › Visão geral; a saída de cada tarefa, em
`logs\agendador.log`. Para ver as tarefas: `schtasks /Query /TN "Central Almoxarifado\Estoque"`.

## 9. Backup e restauração

- O comando `backup_banco` (a tarefa "Backup") grava em `BACKUP_DIR` um arquivo
  `almoxarifado-AAAAMMDD-HHMMSS.sql.gz` por dia e apaga os com mais de **60 dias**.
- Essa pasta está no mesmo servidor: copie-a de vez em quando para outra máquina.

Para restaurar, descompacte o arquivo escolhido (o primeiro comando abaixo, que usa o Python do
`.venv`) e carregue o resultado no banco (o segundo):

```bat
cd /d C:\CentralAlmoxarifado
.venv\Scripts\python.exe -c "import gzip,shutil,sys; shutil.copyfileobj(gzip.open(sys.argv[1]), open(sys.argv[2], 'wb'))" <arquivo>.sql.gz restaurar.sql
mysql -u almox -p almoxarifado < restaurar.sql
```

(no `cmd.exe`, não no PowerShell: o `<` não funciona lá). **Use o cliente da mesma família do
servidor**: `mariadb` no lugar de `mysql` se o servidor for MariaDB. O dump do MariaDB começa
com uma linha (`/*M!999999\- enable the sandbox mode */`) que só o cliente do MariaDB entende; o
`MYSQLDUMP` do `.env` segue a mesma regra (`mariadb-dump` para MariaDB, `mysqldump` para MySQL
8). Para restaurar sobre um sistema que já tem dados, esvazie o banco antes (`DROP DATABASE` e
`CREATE DATABASE` da seção 3) e pare o serviço durante a restauração.

**Teste a restauração uma vez depois de instalar**, num banco vazio de teste (por exemplo
`almoxarifado_restauro`, que você apaga em seguida), para saber que o backup serve antes de
precisar dele. Rode a criação do banco e a restauração **como root** (`mysql -u root -p
almoxarifado_restauro < restaurar.sql`): o usuário `almox` só tem direito em `almoxarifado.*` e
não cria nem carrega outro banco.

## 10. Atualização

Rode como administrador:

```bat
C:\CentralAlmoxarifado\deploy\atualizar.bat
```

Rode-o **fora das janelas das tarefas agendadas** (estoque a cada 30 minutos em dias úteis,
catálogo às 06:30, backup às 23:00): ele reinicia o serviço e, se uma tarefa estiver rodando,
ela e a atualização brigam pelo banco e pelo `.venv`.

Ele confere se há robô em andamento (e para, sem mexer em nada, se houver), puxa o código novo,
atualiza as dependências, roda `migrate`, `collectstatic` e `check --deploy`, confere os robôs de
novo e reinicia o serviço. Para no primeiro erro; corrija o que ele mostrou e rode de novo.

- Se o `uv sync` falhar por **arquivo em uso** (o serviço em execução mantém aberto algum
  `.pyd` ou DLL), pare o serviço e rode de novo (o `atualizar.bat` o reinicia no fim):

  ```bat
  nssm stop CentralAlmoxarifado
  C:\CentralAlmoxarifado\deploy\atualizar.bat
  ```

- Se o `git pull` reclamar de `dubious ownership` (pasta clonada por outra conta), rode uma vez
  `git config --global --add safe.directory C:/CentralAlmoxarifado`.

## 11. Conferência depois de instalar

Marque cada item:

- [ ] O login abre em `https://servidor/almoxarifado/painel/` e entra com o superusuário da seção
      5 (os formulários abrem em `https://servidor/almoxarifado/`, a página já com estilo).
- [ ] Em Automações › Visão geral, "Atualizar agora" termina sem erro.
- [ ] Em Automações › Lançamento no SCPI, "Simular" abre o SCPI (sem janela) e termina.
- [ ] `C:\CentralAlmoxarifado\deploy\tarefa.bat backup_banco` gera o arquivo em `BACKUP_DIR`.
- [ ] `schtasks /Query /TN "Central Almoxarifado\Estoque"` (e `Catalogo`, `Backup`) mostram as
      três tarefas.
- [ ] A conta do serviço consegue rodar o sistema. Abra um terminal **como ela** (pede a senha da
      conta; troque `<computador>` pelo nome do servidor, o que `echo %COMPUTERNAME%` mostra):

      ```bat
      runas /user:<computador>\svc-almoxarifado "cmd /k cd /d C:\CentralAlmoxarifado && .venv\Scripts\python.exe manage.py check"
      ```

      Na janela que abrir, o resultado esperado é `System check identified no issues`. Se aparecer
      "Acesso negado" ou erro ao abrir o Python, a permissão da seção 2 ou o Python da seção 1
      não está certo; o serviço e as tarefas falhariam do mesmo jeito.

      Para o `runas` abrir a janela, a conta precisa do direito "Permitir logon local"
      (`secpol.msc` > Atribuição de Direitos de Usuário), só para este teste; remova depois, se
      não o tinha. Se o servidor negar esse direito, confira pelo log do serviço: reinicie o
      serviço e veja se `logs\servico.log` e `logs\almoxarifado.log` não mostram erro de
      permissão ou de Python.
- [ ] Os registros estão em `C:\CentralAlmoxarifado\logs\` (`almoxarifado.log`, `servico.log`,
      `agendador.log`).

Se algo falhar, o primeiro lugar a olhar é `logs\servico.log` e `logs\almoxarifado.log`.

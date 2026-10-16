# Instalação do Central Almoxarifado no servidor

Guia para o André. O sistema roda em três containers do Docker Compose (`compose.yaml`):

| Serviço | O que faz |
|---|---|
| `banco` | MariaDB 11.4 com os dados do sistema (volume `banco-dados`, sem porta aberta) |
| `web` | o site (waitress), que também dispara os robôs do SCPI pelos botões da página |
| `agendador` | as tarefas de horário fixo (`deploy/crontab`): estoque, catálogo e backup |

O HTTPS continua no **Apache que já existe**: ele guarda o certificado e encaminha
`/almoxarifado` para o container `web`. Siga as seções na ordem. Os comandos são para um terminal
Linux (no caso do Windows Server, o terminal do Ubuntu no WSL2, seção 2). Texto entre `<` e `>` é
para você trocar (senhas, nomes, endereços); nunca guarde senha neste arquivo.

## 1. Onde o sistema roda

São dois casos possíveis; escolha um antes de começar.

- **A. Uma VM ou servidor Linux** (Ubuntu 24.04 ou Debian 12, x86-64). É o ambiente natural do
  Docker. O Apache, em outra máquina, encaminha para o IP desta (seção 6).
- **B. O Windows Server do Apache, com o Docker dentro do WSL2** (Windows Server 2022 ou mais
  novo). O Apache encaminha para `127.0.0.1`. Funciona, mas tem mais peças: o WSL2 precisa
  subir sozinho com o servidor (seção 2).

O **Docker Desktop não serve** para o caso B: não é suportado em Windows Server e exige licença
paga em órgão ou empresa grande. Use o Docker Engine dentro do WSL2, como abaixo.

Nos dois casos o Apache tem de ter `mod_proxy`, `mod_proxy_http` e `mod_headers` ligados e estar
**atendendo em HTTPS, com certificado**: os formulários ficam abertos fora da rede da SAEP e a
área interna tem login, e o `check --deploy` (seção 5) exige HTTPS.

## 2. Docker

### Caso A (Linux)

Instale o Docker Engine e o plugin compose pelo repositório oficial do Docker, seguindo
<https://docs.docker.com/engine/install/ubuntu/> (ou `/debian/`). Confira:

```bash
docker --version
docker compose version
git --version
```

Para rodar o `docker` sem `sudo`, ponha seu usuário no grupo `docker` (`sudo usermod -aG docker
$USER`, depois saia e entre de novo). Esse grupo equivale a root na máquina: só para quem
administra o servidor.

### Caso B (Windows Server com WSL2)

1. Se o Windows Server for uma máquina virtual, o host precisa expor a virtualização aninhada à
   VM (no Hyper-V: `Set-VMProcessor -VMName <nome da VM> -ExposeVirtualizationExtensions $true`,
   com a VM desligada); sem ela o WSL2 não inicia.
2. No PowerShell **como administrador**, instale o WSL2 com o Ubuntu e reinicie se pedir:

   ```powershell
   wsl --install -d Ubuntu-24.04
   wsl --update
   wsl --version
   ```

   O `wsl --version` precisa responder (versão do WSL 2.0 ou mais nova); o systemd do próximo
   passo exige essa versão.

3. No Ubuntu (menu Iniciar › Ubuntu), ligue o systemd, que mantém o Docker rodando:

   ```bash
   printf '[boot]\nsystemd=true\n' | sudo tee /etc/wsl.conf
   ```

   No PowerShell, `wsl --shutdown` e abra o Ubuntu de novo.
4. Dentro do Ubuntu, instale o Docker Engine como no caso A.
5. Faça o WSL2 subir com o servidor e continuar de pé sem ninguém conectado. No PowerShell
   **como administrador**, crie uma tarefa de inicialização que mantém a distribuição aberta
   (ela pede a senha da sua conta do Windows):

   ```powershell
   $acao = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu-24.04 --exec sleep infinity"
   $gatilho = New-ScheduledTaskTrigger -AtStartup
   $config = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
   Register-ScheduledTask -TaskName "Central Almoxarifado WSL" -Action $acao -Trigger $gatilho -Settings $config -User "$env:USERDOMAIN\$env:USERNAME" -Password (Read-Host "Senha") -Force
   ```

   Sem isso, o Windows desliga o WSL2 quando ninguém o usa, e o sistema sai do ar.

   A tarefa guarda a senha da conta: **quando a senha dessa conta mudar, a tarefa para de
   funcionar** e o sistema não sobe mais depois de um reinício. Registre a tarefa de novo (rode o
   `Register-ScheduledTask` acima com a senha nova) sempre que a senha mudar.
6. Reinicie o servidor uma vez e confira, no PowerShell, que o sistema subiu sozinho (depois da
   seção 5): `curl.exe -I http://127.0.0.1:8010/almoxarifado/` responde.

Tudo o que vem depois é no terminal do Ubuntu. Guarde o sistema dentro do Linux (`/srv`), nunca
em `/mnt/c`: lá os arquivos ficam lentos e perdem as permissões.

## 3. Pasta

```bash
sudo mkdir -p /srv/almoxarifado
sudo chown "$USER" /srv/almoxarifado
git clone <endereço do repositório> /srv/almoxarifado
cd /srv/almoxarifado
mkdir -p dados/logs dados/backups dados/importacao
sudo chown -R 1000:1000 dados/logs dados/backups
```

- `dados/logs`: logs do sistema, das tarefas e dos robôs, os CSVs enviados pela página e o
  journal do lançamento.
- `dados/backups`: os backups diários do banco (seção 8).
- `dados/importacao`: os `.xlsx` da migração (`deploy/VIRADA.md`); o sistema só os lê.

O `chown -R 1000:1000` dá as pastas ao usuário do container (`almox`, UID 1000), o único que
grava nelas; sem ele, o sistema não sobe (não consegue abrir o log). O código no container é só
leitura: se alguém conseguir rodar código pelo site, não consegue alterar o sistema.

## 4. `.env` de produção

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Valores de produção, variável por variável (as não citadas ficam como estão; as do bloco "Só no
desenvolvimento local", no fim do arquivo, o compose ignora):

| Variável | Valor |
|---|---|
| `SECRET_KEY` | uma chave gerada, só deste servidor: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DEBUG` | `0` |
| `ALLOWED_HOSTS` | o nome pelo qual o site é acessado, sem esquema, ex.: `servidor.saep.local` |
| `CSRF_TRUSTED_ORIGINS` | o mesmo nome **com** esquema, ex.: `https://servidor.saep.local` |
| `USAR_HTTPS` | `1` (sempre: o `check --deploy` da seção 5 exige HTTPS) |
| `PROXY_HTTPS` | `1` (sempre, atrás do Apache; seção 6) |
| `PREFIXO_URL` | `/almoxarifado`; vazio se o site ficar na raiz |
| `PORTA_PUBLICADA` | caso B: `127.0.0.1:8010`; caso A: `<ip desta máquina na rede do Apache>:8010` (seção 6) |
| `DB_NAME`, `DB_USER` | `almoxarifado` e `almox` |
| `DB_PASSWORD` | uma senha forte para o usuário do banco |
| `SAEP_USER`, `SAEP_PASS` | usuário e senha do SCPI usados pelos robôs |
| `LANCAMENTO_REAL` | `0` até a virada (`deploy/VIRADA.md`): com `0`, só a simulação roda |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | deixe **vazios** até a virada (`deploy/VIRADA.md`), senão um pedido de teste avisa o grupo de verdade |

Cada linha é `NOME=valor`, sem espaços em volta do `=`. O compose trata `$` como variável:
**senha com `$` vai entre aspas simples** (`DB_PASSWORD='abc$123'`), senão muda em silêncio e o
banco recusa a conexão. O banco é criado com `DB_NAME`, `DB_USER`, `DB_PASSWORD` e
`MARIADB_ROOT_PASSWORD` (do `.env.banco`) na primeira subida; trocá-los depois nos arquivos **não** muda o banco (seria
preciso trocar a senha dentro do MariaDB também).

A senha do root do banco fica num arquivo à parte, que só o container do banco lê (o `.env` vai
inteiro ao `web`, que fica exposto à internet, e ela não deve estar lá):

```bash
cp .env.banco.example .env.banco
chmod 600 .env.banco
nano .env.banco
```

Preencha `MARIADB_ROOT_PASSWORD` com outra senha forte, diferente da `DB_PASSWORD` (usada na
restauração, seção 8). A mesma regra do `$` vale aqui.

O `chmod 600` deixa o `.env` e o `.env.banco` legíveis só por você: eles têm as senhas.

## 5. Primeira subida

```bash
cd /srv/almoxarifado
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py check --deploy --fail-level WARNING
docker compose up -d
docker compose ps
```

- O `build` demora alguns minutos na primeira vez (baixa o Python, o Chromium e o MariaDB).
- O `run --rm` sobe o `banco` se preciso e espera ele ficar pronto.
- O `createsuperuser` pede a matrícula (é o nome de usuário) e a senha do primeiro acesso.
- O `check --deploy` precisa terminar **sem avisos** (`System check identified no issues`). Se
  listar algum, corrija o `.env`; um aviso quase sempre é HTTPS, `SECRET_KEY` ou `ALLOWED_HOSTS`.
- O `ps` mostra os três serviços `running`, o `banco` como `healthy`. Eles voltam sozinhos
  depois de um reinício do servidor ou do Docker (`restart: unless-stopped`).

Depois de mudar o `.env`, rode `docker compose up -d`: ele recria os containers com os valores
novos (o `docker compose restart` **não** relê o `.env`). Recriar o `web` mata o robô que estiver
rodando; confira antes com `docker compose run --rm web python manage.py robos_em_andamento`.

## 6. Apache

O padrão é o sistema em `/almoxarifado` do servidor. Endereços resultantes:

| O quê | Endereço |
|---|---|
| Formulários dos funcionários | `https://servidor/almoxarifado/` |
| Área do almoxarifado (login) | `https://servidor/almoxarifado/painel/` |
| Cadastros (admin) | `https://servidor/almoxarifado/admin/` |

No `httpd.conf` (ou no `VirtualHost` do site), dentro do bloco HTTPS, com `<destino>` igual ao
`PORTA_PUBLICADA` do `.env` (`127.0.0.1:8010` no caso B, `<ip da VM>:8010` no caso A):

```apache
ProxyPreserveHost On
RequestHeader set X-Forwarded-Proto "https"
ProxyPass /almoxarifado http://<destino>/almoxarifado
ProxyPassReverse /almoxarifado http://<destino>/almoxarifado
```

Depois, teste a configuração e recarregue o Apache (`httpd -t` e `httpd -k restart`, ou o
serviço do Apache nos Serviços do Windows).

- `ProxyPreserveHost On`: o link "Abrir painel" do aviso no Telegram usa o host da requisição.
- `RequestHeader set X-Forwarded-Proto "https"` e, no `.env`, `USAR_HTTPS=1` e `PROXY_HTTPS=1`:
  sempre os três. Sem o cabeçalho, o redirecionamento para HTTPS entra em laço.
- Se o site ficar na raiz, sem o prefixo: `PREFIXO_URL` vazio no `.env` e `ProxyPass /
  http://<destino>/` (e `ProxyPassReverse / http://<destino>/`).

**Só o Apache pode alcançar o `PORTA_PUBLICADA`.** O Apache chega ao container por um endereço
interno do Docker que muda, então o sistema confia no `X-Forwarded-For` de qualquer origem (é
por ele que conta o limite de pedidos por IP dos formulários). Quem alcançasse a porta direto
falsificaria o próprio IP e ainda passaria por fora do HTTPS.

- Caso B: `127.0.0.1:8010` só é alcançável dentro do servidor. Nada a fazer.
- Caso A: use o IP da VM na rede do Apache (nunca `0.0.0.0`) e libere a porta só para o IP do
  Apache. **O Docker abre as portas publicadas por cima do `ufw` e do `firewalld`**: a regra
  tem de ir na cadeia `DOCKER-USER`:

  ```bash
  sudo iptables -I DOCKER-USER -p tcp --dport 8010 ! -s <ip do Apache> -j DROP
  ```

  A regra some quando a máquina reinicia. Para reaplicá-la sempre depois do Docker, crie uma
  unidade do systemd (troque `<ip do Apache>`):

  ```bash
  sudo tee /etc/systemd/system/almoxarifado-firewall.service <<'FIM'
  [Unit]
  Description=Central Almoxarifado: porta 8010 só para o Apache
  After=docker.service
  Requires=docker.service

  [Service]
  Type=oneshot
  RemainAfterExit=yes
  ExecStart=/bin/sh -c 'iptables -C DOCKER-USER -p tcp --dport 8010 ! -s <ip do Apache> -j DROP || iptables -I DOCKER-USER -p tcp --dport 8010 ! -s <ip do Apache> -j DROP'

  [Install]
  WantedBy=multi-user.target
  FIM
  sudo systemctl daemon-reload
  sudo systemctl enable --now almoxarifado-firewall
  ```

  Não instale o pacote que salva as regras do iptables: no Ubuntu ele remove o `ufw` (e as regras que você já tinha)
  e grava também as cadeias do próprio Docker, que voltariam desatualizadas no boot.

  Confira de outra máquina da rede, que não seja a do Apache: `curl http://<ip da VM>:8010/`
  não pode responder.

## 7. Agendador

O serviço `agendador` roda o `deploy/crontab`, no horário de Brasília:

- Estoque: de segunda a sexta, de 30 em 30 minutos das 07:00 às 17:00.
- Catálogo: todo dia às 06:30 (cadastro, estoque e saídas do SCPI, em sequência).
- Backup: todo dia às 23:00.

O resultado das importações aparece em Automações › Visão geral; a saída de cada tarefa, em
`dados/logs/agendador.log`. O próprio agendador escreve em `docker compose logs agendador`.

Para rodar uma tarefa fora de hora (ex.: o backup), com a saída no mesmo log:

```bash
docker compose exec agendador /app/deploy/tarefa.sh backup_banco
```

## 8. Backup e restauração

- O comando `backup_banco` (a tarefa das 23:00) grava em `dados/backups` um arquivo
  `almoxarifado-AAAAMMDD-HHMMSS.sql.gz` por dia e apaga os com mais de **60 dias**.
- Essa pasta está no mesmo servidor: copie-a de vez em quando para outra máquina.

Para restaurar, pare o site e o agendador, carregue o arquivo escolhido e suba de novo. O
`MARIADB_ROOT_PASSWORD` já está dentro do container do banco, então nenhuma senha é digitada:

```bash
cd /srv/almoxarifado
docker compose stop web agendador
docker compose exec -T banco sh -c 'exec mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -e "DROP DATABASE almoxarifado; CREATE DATABASE almoxarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"'
gunzip -c dados/backups/<arquivo>.sql.gz | docker compose exec -T banco sh -c 'exec mariadb -u root -p"$MARIADB_ROOT_PASSWORD" almoxarifado'
docker compose up -d
```

(o `DROP` só se o banco já tiver dados; o usuário `almox` continua com acesso ao banco recriado,
porque a permissão é pelo nome.)

**Teste a restauração uma vez depois de instalar**, num banco de teste, para saber que o backup
serve antes de precisar dele (o sistema continua no ar):

```bash
docker compose exec agendador /app/deploy/tarefa.sh backup_banco
docker compose exec -T banco sh -c 'exec mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -e "CREATE DATABASE almoxarifado_restauro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"'
gunzip -c dados/backups/<arquivo mais novo>.sql.gz | docker compose exec -T banco sh -c 'exec mariadb -u root -p"$MARIADB_ROOT_PASSWORD" almoxarifado_restauro'
docker compose exec -T banco sh -c 'exec mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT COUNT(*) FROM almoxarifado_restauro.pedidos_pedido; DROP DATABASE almoxarifado_restauro"'
```

## 9. Atualização

```bash
cd /srv/almoxarifado
bash deploy/atualizar.sh
```

Rode-o **fora dos horários do agendador** (estoque de 30 em 30 minutos em dias úteis, catálogo às
06:30, backup às 23:00): ele recria os containers, e uma tarefa no meio seria interrompida.

Ele confere se há robô em andamento (e para, sem mexer em nada, se houver), puxa o código novo,
reconstrói a imagem, roda `migrate` e `check --deploy`, confere os robôs de novo e recria os
containers. Para no primeiro erro com "Atualização interrompida"; corrija o que ele mostrou e
rode de novo.

- Se o `git pull` reclamar de `dubious ownership`, rode uma vez
  `git config --global --add safe.directory /srv/almoxarifado`.
- Imagens antigas ocupam disco; de vez em quando, `docker image prune`.

## 10. Conferência depois de instalar

Marque cada item:

- [ ] `docker compose ps` mostra `banco` (`healthy`), `web` e `agendador` rodando.
- [ ] O login abre em `https://servidor/almoxarifado/painel/` e entra com o superusuário da seção
      5 (os formulários abrem em `https://servidor/almoxarifado/`, a página já com estilo).
- [ ] Em Automações › Visão geral, "Atualizar agora" termina sem erro.
- [ ] Em Automações › Lançamento no SCPI, "Simular" abre o SCPI (sem janela) e termina.
- [ ] `docker compose exec agendador /app/deploy/tarefa.sh backup_banco` gera o arquivo em
      `dados/backups`, e o teste de restauração da seção 8 conta os pedidos.
- [ ] Caso A: de uma máquina que não é a do Apache, `curl http://<ip da VM>:8010/` não responde.
- [ ] Caso B: depois de reiniciar o servidor, o site volta sozinho (seção 2, passo 5).
- [ ] Os registros estão em `dados/logs/` (`almoxarifado.log`, `agendador.log` e os dos robôs).

Se algo falhar, o primeiro lugar a olhar é `docker compose logs web` (ou `agendador`, `banco`) e
`dados/logs/almoxarifado.log`.

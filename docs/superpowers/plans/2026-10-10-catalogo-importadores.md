# Subprojeto 2 — Catálogo e importadores: plano de implementação

> **Situação:** executado. As caixas abaixo não foram marcadas durante a execução; o que vale
> hoje está no código e no `CLAUDE.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O catálogo de materiais passa a ser alimentado pelo SCPI sem o Google: três comandos
(`importar_cadastro`, `importar_estoque` e `importar_saidas_scpi`) baixam os relatórios com o
Playwright e gravam no banco. Cada execução fica registrada em `Importacao`. Uma página
"Catálogo" mostra a saúde do catálogo e tem o botão "Atualizar agora".

**Architecture:**
- Novo app `scpi`, com o código copiado do `extrair-relatorio`:
  - `browser.py`, `relatorios.py` (navegação do Playwright) e `normalizadores.py`;
  - `leitura.py`: CSV para linhas tipadas, puro;
  - `gravacao.py`: linhas para o banco;
  - `execucao.py`: trava e registro em `Importacao`;
  - os comandos `manage.py`.
- Separar baixar de gravar deixa tudo testável sem Playwright. Os comandos aceitam
  `--arquivo` com um CSV já baixado, e os testes usam CSVs anonimizados de `tests/fixtures/scpi/`.
- `catalogo` ganha `SaidaSCPI` e `Importacao`, a montagem dos catálogos dos formulários
  (limpeza, AB, avulsa), a saúde do catálogo e a página que mostra os dois.

**Tech Stack:** Python 3.13, Django 6.x, uv, mysqlclient, Playwright (Chromium),
concurrent-log-handler, pytest + pytest-django, ruff.

**Spec:** `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`, seções 2, 3
(`catalogo`), 4 ("Catálogos dos formulários"), 5 (fluxo 8), 6, 7 e 9 (item 2).

**Código de referência (fora do repositório):**
- `joaorighetto/extrair-relatorio`, commit `cce15aa3706be09bf1cdb2b6c8768b2ab9a4a622`. Para
  clonar:
  `GH_TOKEN=$(gh auth token --user joaorighetto) gh repo clone joaorighetto/extrair-relatorio <pasta> -- --depth 1`.
  Daqui em diante, `ER:` é um caminho nesse clone.
- `../CentralAlmoxarifado/apps-script/Catalogo.gs`: regras dos catálogos e textos da saúde.

## Decisões deste plano

Pontos que a spec deixa em aberto:

1. **Cadastro completo.** O "Relatório de Produtos / Serviços" (Tipos = Produtos) é pedido com
   o período de cadastro de `01/01/2000` até hoje. É a mesma fonte da planilha "todos os itens
   cadastrados", hoje lida pelo Apps Script, em que os itens antigos têm `DTAINSERE` = 01/01/2014.
2. **Proteção contra cadastro truncado.**
   - Se o CSV deixar de fora mais de 20% dos materiais hoje visíveis, a importação aborta e nada
     é alterado.
   - `--forcar` passa por cima. Sem isso, um download cortado esconderia o catálogo inteiro.
3. **Intervalo das saídas.**
   - Começa 7 dias antes do fim do período da última importação bem-sucedida e vai até hoje.
   - A sobreposição existe porque o robô lança saídas com a data efetiva, que pode ser anterior
     à última importação. A chave única (`id_requi`, `cadpro`) evita duplicar.
   - Na primeira execução, o início é 1º de janeiro do ano corrente.
   - `--desde` e `--ate` sobrescrevem o intervalo.
4. **Uma importação de cada tipo por vez**, com `GET_LOCK` do MySQL/MariaDB. A trava é liberada
   sozinha se o processo morrer. Cada tipo usa a própria pasta de perfil do Chromium
   (`SCPI_PERFIL_DIR/<tipo>`), para tipos diferentes rodarem juntos.
5. **Exercício no login do SCPI** = ano corrente. O original fixava `"2026"`.
6. **"Atualizar agora"** inicia `manage.py atualizar_catalogo` em processo separado: cadastro,
   depois estoque, depois saídas. Fica bloqueado enquanto houver uma `Importacao` em andamento
   há menos de 1 h. Passado esse tempo, a importação aparece como "interrompida".
7. **Log com vários processos.**
   - O `RotatingFileHandler` vira `ConcurrentRotatingFileHandler`, do pacote
     `concurrent-log-handler`.
   - No Windows, o rename da rotação falha quando outro processo (waitress, comandos) mantém o
     arquivo aberto.
   - Resolve uma pendência do subprojeto 1.
8. **Catálogos dos formulários entram aqui**, em `catalogo/catalogos.py`. A saúde depende
   deles, e o subprojeto 3 só os consome.

**Pontos a confirmar no SCPI real** (Tarefa 13, manual, com credenciais):
- se o relatório de cadastro desde 2000 traz todos os produtos;
- se o `ID_REQUI` continua único quando o exercício muda;
- se o perfil do Chromium aceita `SCPI_HEADLESS=1`, necessário para rodar como serviço.

## Global Constraints

- `requires-python = ">=3.13,<3.14"`; Django `>=6.0,<7`. Dependências só via `uv add`, com `uv.lock` versionado. Comandos `uv` que instalam rodam no PowerShell.
- Banco: MySQL 8 ou MariaDB com `mysqlclient`, `utf8mb4`, `STRICT_TRANS_TABLES`. Testes contra MySQL/MariaDB, nunca SQLite.
- Enquanto não houver dados reais, mudança de modelo **regenera** a migration existente do app: apagar `catalogo/migrations/0001_initial.py`, rodar `makemigrations catalogo` e depois `migrate catalogo zero` + `migrate` no banco local. Nada de migrations de conversão de dados.
- Textos de interface, mensagens, nomes de código e commits em português (pt-BR).
- Estado nunca só por cor (badge com texto); códigos (CADPRO, requisição) em `.mono`.
- Requisição que grava: POST com `{% csrf_token %}`.
- Testes nunca abrem o Playwright nem acessam o SCPI.
- O código vindo do `extrair-relatorio` mantém a navegação (seletores, esperas, intercepção) **sem mudança**. Só trocam a origem das credenciais e da URL (settings), o ano do exercício, a pasta do perfil e o destino do screenshot de depuração.
- Commits: `git -c user.name="João" -c user.email="jm_zr@icloud.com" commit ...`, num branch `catalogo-importadores` criado a partir do `main`. Toda mensagem termina com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `ruff check .` e `ruff format --check .` limpos ao fim de cada tarefa.

## Review Focus

1. **CSV de cadastro truncado ou vazio.** Download cortado, ou relatório sem linhas: a
   importação aborta sem esconder nada (Tarefa 6).
2. **Duas importações ao mesmo tempo.**
   - Casos: agendador e botão juntos, ou dois cliques.
   - A segunda execução recusa sem tocar nos dados nem no navegador (Tarefa 5).
   - O botão não inicia nada enquanto houver uma em andamento (Tarefa 9).
3. **Saída com data anterior à última importação** (data efetiva retroativa): entra na
   importação seguinte (Tarefa 8).
4. **Formatos do CSV do SCPI.**
   - Registros quebrados em várias linhas;
   - números pt-BR com milhar (`1.234,5`);
   - valor vazio;
   - texto maior que o campo, que no `STRICT_TRANS_TABLES` derrubaria a transação.
   - Tudo isso é lido ou cortado com aviso, nunca com erro 500 (Tarefas 3, 4, 6 e 8).
5. **Importação que morreu no meio** (processo derrubado; fica "em andamento" para sempre).
   - Depois de 1 h, aparece como "interrompida" e libera o botão.
   - Os dados anteriores continuam intactos (Tarefas 5, 9 e 11).

---

### Tarefa 1: Dependências, app `scpi` e log entre processos

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (via `uv add playwright concurrent-log-handler`)
- Modify: `config/settings.py`: `"scpi"` em `INSTALLED_APPS`, depois de `"catalogo"`; settings
  `SCPI_*`; handler do log
- Modify: `.env.example`: `SCPI_URL`, `SCPI_HEADLESS`, `SCPI_PERFIL_DIR`, com comentários
- Create: `scpi/__init__.py`, `scpi/apps.py` (`ScpiConfig`, `verbose_name = "SCPI"`),
  `scpi/management/__init__.py`, `scpi/management/commands/__init__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `settings.SCPI_URL: str`, padrão `"https://transparencia.saep.sp.gov.br:8445/scpi9/"`.
  - `settings.SCPI_HEADLESS: bool`, via `ler_bool`, padrão `False`.
  - `settings.SCPI_PERFIL_DIR: Path`, padrão `BASE_DIR / ".pw-profile"`.

- [ ] **Step 1: Testes que falham** (`tests/test_config.py`)

```python
def test_log_aguenta_varios_processos():
    handler = settings.LOGGING["handlers"]["arquivo"]
    assert handler["class"] == "concurrent_log_handler.ConcurrentRotatingFileHandler"
    assert handler["maxBytes"] == 5 * 1024 * 1024 and handler["backupCount"] == 10

def test_padroes_do_scpi():
    assert settings.SCPI_URL == "https://transparencia.saep.sp.gov.br:8445/scpi9/"
    assert settings.SCPI_HEADLESS is False
    assert settings.SCPI_PERFIL_DIR == settings.BASE_DIR / ".pw-profile"
    assert "scpi" in settings.INSTALLED_APPS
```

Para não depender do `.env` local, siga o padrão que o arquivo já usa para os testes de
settings: subprocesso ou `importlib.reload`, com as variáveis `SCPI_*` removidas do ambiente.

- [ ] **Step 2:** `uv run pytest tests/test_config.py -k "processos or scpi"`. Esperado: FAIL.
- [ ] **Step 3:** No PowerShell, rode `uv add playwright concurrent-log-handler`. Depois
  implemente os settings e o app. Na pasta do perfil, um comentário explica que cada tipo de
  importação usa uma subpasta própria.
- [ ] **Step 4:** Rode a suíte inteira e `uv run python manage.py check`. Esperado: tudo PASS.
- [ ] **Step 5: Commit**: `Dependências do SCPI e log seguro com vários processos`

---

### Tarefa 2: Modelos `SaidaSCPI` e `Importacao`

**Files:**
- Modify: `catalogo/models.py`, `catalogo/admin.py`
- Regenerate: `catalogo/migrations/0001_initial.py`
- Test: `tests/test_modelos_importacao.py`

**Interfaces:**
- Produces:
  - **`SaidaSCPI`:**
    - campos: `id_requi` (Char 20), `cadpro` (Char 30, `db_index`), `data` (Date),
      `qtd` (Decimal 14,4), `valor` (Decimal 16,5);
    - `UniqueConstraint(fields=["id_requi", "cadpro"], name="saida_scpi_unica")`;
    - `ordering = ["-data", "id_requi"]`; verbose "saída do SCPI" / "saídas do SCPI".
  - **`Importacao`:**
    - `Tipo` (TextChoices): `CADASTRO "Cadastro"`, `ESTOQUE "Estoque"`, `SAIDAS "Saídas do SCPI"`.
    - `Situacao`: `ANDAMENTO "Em andamento"`, `SUCESSO "Concluída"`, `FALHA "Falhou"`.
    - `tipo`: Char 20, com choices.
    - `inicio`: `default=timezone.now`.
    - `fim`: DateTime, null.
    - `situacao`: default `ANDAMENTO`.
    - `linhas`: PositiveInteger, default 0.
    - `avisos`: `JSONField(default=list, blank=True)`, lista de textos.
    - `erro`: Text, blank.
    - `periodo_de` e `periodo_ate`: Date, null.
    - `ordering = ["-inicio"]`; verbose "importação" / "importações".
  - `LIMITE_ANDAMENTO = timedelta(hours=1)`, constante do módulo.
  - `Importacao.em_andamento(agora: datetime | None = None) -> QuerySet` (classmethod): situação
    `ANDAMENTO` com `inicio >= agora - LIMITE_ANDAMENTO`.
  - Propriedade `Importacao.interrompida -> bool`: `ANDAMENTO` com `inicio` anterior ao limite.
  - Admin das duas: só leitura, como o `MaterialAdmin`.
    - `SaidaSCPI`: `list_display` id_requi, cadpro, data, qtd, valor; busca por cadpro e
      id_requi; `date_hierarchy = "data"`.
    - `Importacao`: `list_display` tipo, inicio, fim, situacao, linhas; filtros por tipo e
      situação.

- [ ] **Step 1: Testes que falham**

```python
def test_saida_scpi_unica_por_requisicao_e_material():
    SaidaSCPI.objects.create(id_requi="2", cadpro="013.005.007", data=date(2026, 1, 12), qtd=1, valor=Decimal("3.1"))
    with pytest.raises(IntegrityError), transaction.atomic():
        SaidaSCPI.objects.create(id_requi="2", cadpro="013.005.007", data=date(2026, 1, 12), qtd=2, valor=0)

def test_valor_guarda_cinco_casas():
    s = SaidaSCPI.objects.create(id_requi="9", cadpro="1", data=date(2026, 1, 1), qtd=1, valor=Decimal("2.52976"))
    s.refresh_from_db(); assert s.valor == Decimal("2.52976")

def test_importacao_nasce_em_andamento_com_avisos_vazios():
    i = Importacao.objects.create(tipo=Importacao.Tipo.ESTOQUE)
    assert i.situacao == Importacao.Situacao.ANDAMENTO and i.avisos == [] and i.fim is None

def test_em_andamento_ignora_a_interrompida_ha_mais_de_uma_hora():
    agora = timezone.now()
    recente = Importacao.objects.create(tipo="ESTOQUE", inicio=agora - timedelta(minutes=59))
    velha = Importacao.objects.create(tipo="CADASTRO", inicio=agora - timedelta(minutes=61))
    assert list(Importacao.em_andamento(agora)) == [recente]
    assert velha.interrompida and not recente.interrompida

@pytest.mark.parametrize("modelo", ["saidascpi", "importacao"])
def test_admin_so_leitura(admin_client, modelo):
    assert admin_client.get(f"/admin/catalogo/{modelo}/").status_code == 200
    assert admin_client.get(f"/admin/catalogo/{modelo}/add/").status_code == 403
```

- [ ] **Step 2:** `uv run pytest tests/test_modelos_importacao.py`. Esperado: FAIL (import).
- [ ] **Step 3:** Implemente os modelos e o admin. Depois regenere a 0001 e recrie o banco
  local, como em Global Constraints.
- [ ] **Step 4:** Rode a suíte inteira e `makemigrations --check --dry-run`. Esperado: PASS e
  "No changes detected".
- [ ] **Step 5: Commit**: `Modelos das saídas do SCPI e do registro de importações`

---

### Tarefa 3: Código do SCPI copiado (browser, relatórios, normalizadores)

**Files:**
- Create: `scpi/browser.py` (de `ER:saep/browser.py`)
- Create: `scpi/relatorios.py`, com as funções `run()` de `ER:exportar_produtos_cadastro.py`,
  `ER:exportar_estoque.py` e `ER:exportar_saidas.py`
- Create: `scpi/normalizadores.py` (de `ER:saep/normalizers/produtos.py` e `saidas.py`)
- Create: `scpi/leitura.py`, só com a exceção `ErroImportacao(Exception)`; o resto vem na
  Tarefa 4
- Modify: `THIRD-PARTY-NOTICES.md` não muda: o `extrair-relatorio` é código próprio. Cite a
  origem e o commit na docstring de cada módulo copiado.
- Test: `tests/test_scpi_normalizadores.py`

**Interfaces:**
- Produces:
  - **`normalizadores.py`:** recebem o texto inteiro do CSV e devolvem os registros, já
    recolados numa linha cada. Mesmo algoritmo dos originais; só não leem nem gravam arquivo.
    - `registros_produtos(texto: str) -> list[str]`: início de registro em
      `^\d{3}\.\d{3}(\.[\w-]{1,3})?;`, cabeçalho iniciado por `CADPRO`.
    - `registros_saidas(texto: str) -> list[str]`: início em `^\d{2}/\d{2}/\d{4}`, cabeçalho
      iniciado por `GRUPO`.
  - **`browser.py`:**
    - `abrir_sessao(playwright, perfil: Path) -> tuple[context, page]`:
      - antes de abrir o navegador, levanta
        `ErroImportacao("Defina SAEP_USER e SAEP_PASS no .env.")` se uma das duas faltar;
      - usa `settings.SCPI_URL` e `headless=settings.SCPI_HEADLESS`;
      - o exercício é `str(timezone.localdate().year)`.
    - `frame_compras(page)`, sem mudança.
    - `interceptar_csv(page, frame, nome: str) -> bytes`: o screenshot de depuração vai para
      `settings.LOG_DIR / f"scpi-{nome}-{AAAAmmdd_HHMMSS}.png"`; sem CSV, levanta
      `ErroImportacao`.
  - **`relatorios.py`:** abrem e fecham o próprio contexto, com o perfil em
    `settings.SCPI_PERFIL_DIR / "<tipo>"` (cadastro, estoque, saidas). O contexto é fechado num
    `finally`.
    - `baixar_cadastro(de: date, ate: date) -> bytes`
    - `baixar_estoque() -> bytes`
    - `baixar_saidas(de: date, ate: date) -> bytes`
  - `INICIO_CADASTRO = date(2000, 1, 1)`, em `relatorios.py`.
  - Importe `playwright.sync_api` dentro das funções, não no topo do módulo.

- [ ] **Step 1: Testes que falham**

```python
def test_registro_de_produto_quebrado_em_linhas_e_recolado():
    texto = "CADPRO;DISC1;DISCR1\r\n001.001.001;DETERGENTE;Detergente neutro,\r\nfrasco de 500 ml\r\n800.004;LEGADO;\r\n"
    assert registros_produtos(texto) == [
        "CADPRO;DISC1;DISCR1",
        "001.001.001;DETERGENTE;Detergente neutro, frasco de 500 ml",
        "800.004;LEGADO;",
    ]

def test_codigo_legado_com_hifen_inicia_registro():
    assert registros_produtos("CADPRO;X\n000.009.0-1;A\n")[1] == "000.009.0-1;A"

def test_registro_de_saida_recolado_e_cabecalho_preservado():
    texto = "GRUPO;ID_REQUI;OBS\n12/01/2026;2;linha um\nlinha dois\n13/01/2026;3;\n"
    assert registros_saidas(texto) == ["GRUPO;ID_REQUI;OBS", "12/01/2026;2;linha um linha dois", "13/01/2026;3;"]

def test_sessao_sem_credenciais_nao_abre_o_navegador(settings):
    settings.SAEP_USER = ""; settings.SAEP_PASS = ""
    with pytest.raises(ErroImportacao, match="SAEP_USER e SAEP_PASS"):
        abrir_sessao(None, Path("x"))
```

- [ ] **Step 2:** `uv run pytest tests/test_scpi_normalizadores.py`. Esperado: FAIL.
- [ ] **Step 3:** Copie e adapte o código. A navegação de cada `run()` passa sem mudança para a
  função correspondente em `relatorios.py`. As datas de cadastro e de saídas são formatadas com
  `%d/%m/%Y`, como no original.
- [ ] **Step 4:** `uv run pytest tests/test_scpi_normalizadores.py` + ruff. Esperado: PASS.
- [ ] **Step 5: Commit**: `Navegação e normalizadores do SCPI copiados do extrair-relatorio`

---

### Tarefa 4: Leitura dos CSVs do SCPI

**Files:**
- Modify: `scpi/leitura.py`
- Create: `tests/fixtures/scpi/cadastro.csv`, `estoque.csv` e `saidas.csv`, gravados com BOM,
  UTF-8 e fim de linha CRLF (conteúdo abaixo)
- Test: `tests/test_scpi_leitura.py`

**Interfaces:**
- Consumes: `registros_produtos`, `registros_saidas` (Tarefa 3).
- Produces (puro, sem ORM):
  - **Dataclasses (frozen):**
    - `Leitura(linhas: list, avisos: list[str])`
    - `LinhaCadastro(codigo, nome, unidade, grupo, subgrupo: str, oculto: bool)`
    - `LinhaEstoque(codigo: str, qtd: Decimal)`
    - `LinhaSaidaSCPI(id_requi, cadpro: str, data: date, qtd: Decimal, valor: Decimal)`
  - **Funções de leitura:**
    - `ler_cadastro(conteudo: bytes) -> Leitura`: colunas `CADPRO`, `DISC1`, `UNID1`,
      `NOMEGRUPO`, `NOMESUBGRUPO`, `NOCULTAR`.
    - `ler_estoque(conteudo: bytes) -> Leitura`: colunas `CADPRO`, `QUAN3`.
    - `ler_saidas(conteudo: bytes) -> Leitura`: colunas `ID_REQUI`, `CADPRO`, `DTLAN`, `QUAN2`,
      `VATO2`.
  - **Conversões pt-BR:**
    - `decimal_br(texto: str) -> Decimal`: ponto e vírgula juntos tiram o ponto e trocam a
      vírgula; só vírgula vira ponto. Vazio ou inválido levanta `ValueError`.
    - `data_br(texto: str) -> date`: `dd/mm/aaaa`, ignorando a hora se houver.
- Regras:
  - **Decodificação e colunas:**
    - decodifica `utf-8-sig`; falha vira `ErroImportacao("<Rótulo>: o arquivo não está em UTF-8.")`;
    - o cabeçalho é o primeiro registro que começa pelo nome esperado (`CADPRO` ou `GRUPO`);
    - colunas localizadas pelo nome, nunca pela posição;
    - registros lidos com `csv.reader(..., delimiter=";")`;
    - linha mais curta que o cabeçalho completa com `""`;
    - todos os textos com `strip()`.
  - **Erros e avisos:**
    - cabeçalho ou colunas ausentes:
      `ErroImportacao("<Rótulo>: cabeçalho(s) ausente(s): A, B")`, com os rótulos `Cadastro`,
      `Estoque` e `Saídas do SCPI`;
    - cadastro: linha sem código ou sem nome é ignorada; ao final, um aviso
      `"Linhas sem código ou nome ignoradas: N."`;
    - cadastro: `oculto = norm_u(NOCULTAR) == "SIM"`;
    - estoque: quantidade inválida gera o aviso
      `"Quantidade inválida ignorada: <código> ('<texto>')."`;
    - saídas: data, quantidade ou campos-chave inválidos geram um aviso por linha, com o mesmo
      formato e a requisição;
    - saídas: `VATO2` vazio vira `Decimal(0)`.

Conteúdo das fixtures (o cabeçalho de cadastro e estoque é o real do SCPI):

`cadastro.csv`
```
CADPRO;DISC1;UNID1;QUAN3;VAUN1;PRECOMEDIO;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1;QUANMIN;QUANMAX;CODREDUZ;CODBARRA;NOCULTAR;USUARIO;DTAINSERE;USUALT;DTAALT;LOCALFISICO
001.001.001;DETERGENTE NEUTRO 500 ML;UN;12;2,5;2,5;001;001;MATERIAL DE LIMPEZA;PRODUTOS DE LIMPEZA;Detergente neutro,
frasco de 500 ml;0;0;101;1001001;Não;USUARIO TESTE;01/01/2014;;;
001.001.002;SACO PARA LIXO 100 L;PCT;0;0;0;001;002;MATERIAL DE LIMPEZA;SACOS;;0;0;102;1001002;Sim;;01/01/2014;;;
013.005.007;LUVA NITRÍLICA;PAR;40;3,1;3,1;013;005;MATERIAL DE SEGURANÇA E EPI;PROTEÇÃO DAS MÃOS;;0;0;103;13005007;Não;;01/01/2014;;;
013.005.007;LUVA NITRÍLICA (REPETIDA);PAR;0;0;0;013;005;MATERIAL DE SEGURANÇA E EPI;PROTEÇÃO DAS MÃOS;;0;0;104;13005007;Não;;01/01/2014;;;
800.004;MATERIAL LEGADO;UN;0;0;0;800;0;GERAL;GERAL;;0;0;105;800004;Não;;01/01/2014;;;
016.002.094;;UN;0;0;0;016;002;MATERIAL PARA REDES DE ÁGUA;CONEXÕES;;0;0;106;16002094;Não;;01/01/2014;;;
```

`estoque.csv`: mesmo cabeçalho, com estas linhas:
- `001.001.001` com `QUAN3` = `12`;
- `013.005.007` com `QUAN3` = `1.234,5`;
- `999.999.999` (sem cadastro) com `QUAN3` = `5`;
- `001.001.002` com `QUAN3` = `abc`.

Os demais campos podem repetir os do cadastro.

`saidas.csv`
```
GRUPO;GRUPO_1;ID_REQUI;REQUI;CODIF;NOME;DTLAN;DATAE;DTEMISSAONF;DTPAG;ENTR;SAID;COMP;OBS_CABECALHO;CADPRO;DISC1;UNID1;DISCR1;NOME_GRUPO;NOME_SUBGRUPO;QUAN2;VAUN2;VATO2;COD;DESTI;CODCCUSTO;CCUSTO
12/01/2026;;2;000001/26;;;12/01/2026;;;12/01/2026;;S;P;;013.005.007;LUVA NITRÍLICA;PAR;Luva nitrílica
para limpeza pesada;MATERIAL DE SEGURANÇA E EPI;PROTEÇÃO DAS MÃOS;2;3,1;6,2;14;SANEAMENTO;14;ABASTECIMENTO DE ÁGUA
12/01/2026;;2;000001/26;;;12/01/2026;;;12/01/2026;;S;P;;001.001.001;DETERGENTE NEUTRO 500 ML;UN;;MATERIAL DE LIMPEZA;PRODUTOS DE LIMPEZA;1;2,5;2,5;14;SANEAMENTO;14;ABASTECIMENTO DE ÁGUA
13/01/2026;;3;000002/26;;;13/01/2026;;;13/01/2026;;S;P;;013.005.007;LUVA NITRÍLICA;PAR;;MATERIAL DE SEGURANÇA E EPI;PROTEÇÃO DAS MÃOS;1;3,1;3,1;20;OFICINA;20;OFICINA
13/01/2026;;3;000002/26;;;13/01/2026;;;13/01/2026;;S;P;;013.005.007;LUVA NITRÍLICA;PAR;;MATERIAL DE SEGURANÇA E EPI;PROTEÇÃO DAS MÃOS;1;3,1;3,1;20;OFICINA;20;OFICINA
14/01/2026;;4;000003/26;;;14/01/2026;;;14/01/2026;;S;P;;999.999.999;MATERIAL SEM CADASTRO;UN;;GERAL;GERAL;1;;;20;OFICINA;20;OFICINA
```

- [ ] **Step 1: Testes que falham**

```python
FIX = Path(__file__).parent / "fixtures" / "scpi"

def test_ler_cadastro():
    leitura = ler_cadastro((FIX / "cadastro.csv").read_bytes())
    codigos = [l.codigo for l in leitura.linhas]
    assert codigos == ["001.001.001", "001.001.002", "013.005.007", "013.005.007", "800.004"]
    assert leitura.linhas[0].nome == "DETERGENTE NEUTRO 500 ML" and not leitura.linhas[0].oculto
    assert leitura.linhas[1].oculto and leitura.linhas[0].grupo == "MATERIAL DE LIMPEZA"
    assert leitura.avisos == ["Linhas sem código ou nome ignoradas: 1."]

def test_ler_estoque_com_milhar_e_quantidade_invalida():
    leitura = ler_estoque((FIX / "estoque.csv").read_bytes())
    assert {l.codigo: l.qtd for l in leitura.linhas} == {
        "001.001.001": Decimal("12"), "013.005.007": Decimal("1234.5"), "999.999.999": Decimal("5")}
    assert leitura.avisos == ["Quantidade inválida ignorada: 001.001.002 ('abc')."]

def test_ler_saidas():
    leitura = ler_saidas((FIX / "saidas.csv").read_bytes())
    primeira = leitura.linhas[0]
    assert (primeira.id_requi, primeira.cadpro, primeira.data, primeira.qtd, primeira.valor) == (
        "2", "013.005.007", date(2026, 1, 12), Decimal("2"), Decimal("6.2"))
    assert len(leitura.linhas) == 5 and leitura.linhas[-1].valor == Decimal(0)

@pytest.mark.parametrize(("texto", "valor"), [("8,9948", "8.9948"), ("1.234,5", "1234.5"), ("172", "172"), ("-3", "-3")])
def test_decimal_br(texto, valor):
    assert decimal_br(texto) == Decimal(valor)

@pytest.mark.parametrize("texto", ["", "abc", "1,2,3"])
def test_decimal_br_recusa(texto):
    with pytest.raises(ValueError):
        decimal_br(texto)

def test_cabecalho_ausente():
    with pytest.raises(ErroImportacao, match=r"^Estoque: cabeçalho\(s\) ausente\(s\): QUAN3$"):
        ler_estoque("CADPRO;DISC1\r\n001.001.001;X\r\n".encode())

def test_arquivo_vazio_e_cabecalho_ausente():
    with pytest.raises(ErroImportacao, match="Cadastro: cabeçalho"):
        ler_cadastro(b"")

def test_arquivo_fora_do_utf8():
    with pytest.raises(ErroImportacao, match="não está em UTF-8"):
        ler_cadastro("CADPRO;DISC1\n001.001.001;AÇÚCAR\n".encode("cp1252"))
```

- [ ] **Step 2:** `uv run pytest tests/test_scpi_leitura.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente em `scpi/leitura.py`.
- [ ] **Step 4:** `uv run pytest tests/test_scpi_leitura.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Leitura dos CSVs do SCPI (cadastro, estoque e saídas)`

---

### Tarefa 5: Execução de uma importação (trava e registro)

**Files:**
- Create: `scpi/execucao.py`
- Test: `tests/test_scpi_execucao.py`

**Interfaces:**
- Consumes: `Importacao` (Tarefa 2), `ErroImportacao` (Tarefa 3).
- Produces:
  - `Resultado(linhas: int, avisos: list[str])`, dataclass.
  - `ImportacaoEmAndamento(Exception)`.
  - `trava(nome: str) -> ContextManager[bool]`:
    - `SELECT GET_LOCK(%s, 0)` na conexão `default`;
    - entrega `True` se obteve;
    - `RELEASE_LOCK` no fim, só se obteve.
  - `executar(tipo, obter_csv: Callable[[], bytes], gravar: Callable[[bytes], Resultado], periodo: tuple[date | None, date | None] = (None, None)) -> Importacao`:
    - com `trava(f"almoxarifado:importar:{tipo}")`; sem a trava, levanta
      `ImportacaoEmAndamento` e não cria registro;
    - cria a `Importacao` em andamento, com o período;
    - `obter_csv()` roda fora de transação e `gravar(conteudo)` dentro de
      `transaction.atomic()`;
    - sucesso: `SUCESSO`, `linhas`, `avisos` e `fim`;
    - `ErroImportacao`: `FALHA`, com `erro=str(exc)`;
    - qualquer outra `Exception`: `FALHA`, com `erro=f"Falha inesperada: {exc}"` e
      `logger.exception`;
    - grava `fim` em todos os casos e devolve a `Importacao`.
  - Logger: `logging.getLogger("scpi")`.

- [ ] **Step 1: Testes que falham**

```python
def test_sucesso_registra_linhas_e_avisos():
    imp = executar("ESTOQUE", lambda: b"x", lambda c: Resultado(3, ["um aviso"]))
    imp.refresh_from_db()
    assert (imp.situacao, imp.linhas, imp.avisos) == ("SUCESSO", 3, ["um aviso"]) and imp.fim

def test_falha_desfaz_o_que_foi_gravado_e_registra_o_erro():
    def gravar(c):
        Material.objects.create(codigo="1", nome="X")
        raise ErroImportacao("Estoque: o CSV não tem nenhum material; nada foi alterado.")
    imp = executar("ESTOQUE", lambda: b"x", gravar)
    assert imp.situacao == "FALHA" and imp.erro.startswith("Estoque: o CSV")
    assert not Material.objects.exists()

def test_falha_ao_baixar_tambem_e_registrada():
    def baixar(): raise RuntimeError("Nenhum CSV interceptado")
    imp = executar("SAIDAS", baixar, lambda c: Resultado(0, []))
    assert imp.situacao == "FALHA" and imp.erro == "Falha inesperada: Nenhum CSV interceptado"

def test_segunda_importacao_do_mesmo_tipo_e_recusada():
    outra = connections.create_connection("default")
    with outra.cursor() as c:
        c.execute("SELECT GET_LOCK('almoxarifado:importar:ESTOQUE', 0)")
    try:
        with pytest.raises(ImportacaoEmAndamento):
            executar("ESTOQUE", lambda: pytest.fail("não deveria baixar"), lambda c: Resultado(0, []))
        assert not Importacao.objects.exists()
        executar("CADASTRO", lambda: b"x", lambda c: Resultado(0, []))  # outro tipo segue
    finally:
        outra.close()

def test_trava_e_liberada_ao_terminar():
    executar("ESTOQUE", lambda: b"x", lambda c: Resultado(0, []))
    with trava("almoxarifado:importar:ESTOQUE") as obtida:
        assert obtida
```

- [ ] **Step 2:** `uv run pytest tests/test_scpi_execucao.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente `scpi/execucao.py`.
- [ ] **Step 4:** `uv run pytest tests/test_scpi_execucao.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Execução das importações com trava por tipo e registro em Importacao`

---

### Tarefa 6: `importar_cadastro`

**Files:**
- Create: `scpi/gravacao.py`, com `gravar_cadastro`
- Create: `scpi/management/commands/importar_cadastro.py`
- Test: `tests/test_importar_cadastro.py`

**Interfaces:**
- Consumes: `ler_cadastro`, `Leitura` (Tarefa 4); `executar`, `Resultado`,
  `ImportacaoEmAndamento` (Tarefa 5); `relatorios.baixar_cadastro`, `INICIO_CADASTRO`
  (Tarefa 3).
- Produces:
  - `LIMITE_SUMIDOS = 0.2`.
  - `gravar_cadastro(leitura: Leitura, forcar: bool = False) -> Resultado`:
    - **Validação:**
      - leitura sem linhas: `ErroImportacao("Cadastro: o CSV não tem nenhum material; nada foi alterado.")`;
      - se `sumidos > LIMITE_SUMIDOS * visíveis` e não `forcar`:
        `ErroImportacao(f"Cadastro: o CSV não traz {sumidos} dos {visiveis} materiais visíveis (mais de 20%). Nada foi alterado; confira o relatório do SCPI ou rode com --forcar.")`.
        Aqui, `visíveis` são os materiais não ocultos do banco e `sumidos` os visíveis que não
        estão no CSV.
    - **Gravação:**
      - código repetido no CSV: `duplicado=True`, vale a primeira linha, com o aviso
        `"Códigos repetidos no cadastro (bloqueados): a, b."`;
      - códigos que voltam a aparecer sem repetição ficam com `duplicado=False`;
      - insere os novos e atualiza nome, unidade, grupo, subgrupo, `oculto` e `duplicado` dos
        existentes;
      - materiais fora do CSV ficam `oculto=True`, nunca são apagados;
      - `estoque` e `estoque_em` não mudam;
      - texto maior que o `max_length` do campo é cortado, com o aviso
        `"Texto cortado em <campo> (<max> caracteres): <código>."`;
      - usa `bulk_create` e `bulk_update` (cerca de 12 mil materiais).
    - `Resultado.linhas` = número de códigos distintos gravados. Os avisos da leitura vêm
      primeiro.
  - **Comando `importar_cadastro`:**
    - opções: `--arquivo CAMINHO` (lê o CSV do disco em vez de baixar), `--forcar`;
    - sem `--arquivo`, baixa com `baixar_cadastro(INICIO_CADASTRO, timezone.localdate())`;
    - sucesso: escreve `"Cadastro: N materiais gravados."` e cada aviso numa linha;
    - `FALHA`: levanta `CommandError(imp.erro)`;
    - `ImportacaoEmAndamento`: levanta `CommandError("Importação de cadastro já em andamento.")`.

- [ ] **Step 1: Testes que falham** (`call_command("importar_cadastro", arquivo=FIX / "cadastro.csv")`)

```python
def test_importa_o_cadastro():
    importar()
    assert Material.objects.count() == 4
    m = Material.objects.get(codigo="001.001.001")
    assert (m.nome, m.unidade, m.grupo, m.subgrupo, m.oculto) == (
        "DETERGENTE NEUTRO 500 ML", "UN", "MATERIAL DE LIMPEZA", "PRODUTOS DE LIMPEZA", False)
    assert Material.objects.get(codigo="001.001.002").oculto
    luva = Material.objects.get(codigo="013.005.007")
    assert luva.duplicado and luva.nome == "LUVA NITRÍLICA"
    imp = Importacao.objects.get()
    assert (imp.tipo, imp.situacao, imp.linhas) == ("CADASTRO", "SUCESSO", 4)
    assert "Códigos repetidos no cadastro (bloqueados): 013.005.007." in imp.avisos

def test_material_que_sumiu_fica_oculto_e_mantem_o_estoque():
    sumido = Material.objects.create(codigo="555.000.001", nome="ANTIGO", estoque=7)
    importar(forcar=True)  # 1 de 1 visível sumiria: acima do limite de 20%
    sumido.refresh_from_db(); assert sumido.oculto and sumido.estoque == 7

def test_reaparecer_desoculta_e_deixa_de_ser_duplicado():
    Material.objects.create(codigo="800.004", nome="X", oculto=True, duplicado=True)
    importar()
    m = Material.objects.get(codigo="800.004")
    assert (m.nome, m.oculto, m.duplicado) == ("MATERIAL LEGADO", False, False)

def test_cadastro_truncado_aborta_sem_esconder_nada():
    for n in range(10):
        Material.objects.create(codigo=f"900.000.{n:03}", nome=f"M{n}")
    with pytest.raises(CommandError, match=r"não traz 10 dos 10 materiais visíveis"):
        importar()
    assert not Material.objects.filter(oculto=True).exists()
    assert Importacao.objects.get().situacao == "FALHA"

def test_forcar_aceita_o_cadastro_menor():
    Material.objects.create(codigo="900.000.001", nome="M")
    importar(forcar=True)
    assert Material.objects.get(codigo="900.000.001").oculto

def test_cadastro_vazio_aborta(tmp_path):
    vazio = tmp_path / "vazio.csv"; vazio.write_bytes((FIX / "cadastro.csv").read_bytes().splitlines(keepends=True)[0])
    with pytest.raises(CommandError, match="não tem nenhum material"):
        call_command("importar_cadastro", arquivo=vazio)

def test_nome_longo_e_cortado_com_aviso(tmp_path):
    ...  # CSV com DISC1 de 300 caracteres → nome com 255 e aviso "Texto cortado em nome (255 caracteres): <código>."

def test_sem_arquivo_baixa_do_scpi(monkeypatch):
    chamadas = []
    monkeypatch.setattr(relatorios, "baixar_cadastro", lambda de, ate: chamadas.append((de, ate)) or (FIX / "cadastro.csv").read_bytes())
    call_command("importar_cadastro")
    assert chamadas == [(date(2000, 1, 1), timezone.localdate())]
```

- [ ] **Step 2:** `uv run pytest tests/test_importar_cadastro.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente `gravar_cadastro` e o comando. O comando chama
  `relatorios.baixar_cadastro` pelo módulo, como `relatorios.baixar_cadastro(...)`, para o
  monkeypatch funcionar.
- [ ] **Step 4:** `uv run pytest tests/test_importar_cadastro.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Comando importar_cadastro`

---

### Tarefa 7: `importar_estoque`

**Files:**
- Modify: `scpi/gravacao.py`, com `gravar_estoque`
- Create: `scpi/management/commands/importar_estoque.py`
- Test: `tests/test_importar_estoque.py`

**Interfaces:**
- Consumes: `ler_estoque` (Tarefa 4), `executar` (Tarefa 5), `relatorios.baixar_estoque`
  (Tarefa 3).
- Produces:
  - `gravar_estoque(leitura: Leitura, em: datetime) -> Resultado`:
    - **Validação:** leitura sem linhas aborta com
      `ErroImportacao("Estoque: o CSV não tem nenhum material; nada foi alterado.")`.
    - **Gravação:**
      - todo `Material` passa a ter `estoque=0` e `estoque_em=em`;
      - os códigos do CSV recebem o saldo;
      - código repetido no CSV: vale a última linha, com o aviso
        `"Códigos repetidos no estoque (vale a última linha): a."`;
      - código sem cadastro gera o aviso
        `"Códigos com saldo sem cadastro (ignorados): 999.999.999."`, listando no máximo 8 e
        depois `" e mais N"`, como no `Catalogo.gs`;
      - `Resultado.linhas` = materiais com saldo gravado.
  - **Comando `importar_estoque`:**
    - opção `--arquivo`; usa `em=timezone.now()`;
    - escreve `"Estoque: N materiais com saldo."` e os avisos;
    - erros como na Tarefa 6.
  - O formatador de lista com "e mais N" fica em `scpi/gravacao.py`, como
    `lista_curta(itens: list[str], limite: int = 8) -> str`. A Tarefa 11 também usa.

- [ ] **Step 1: Testes que falham**

```python
def test_importa_saldos_e_zera_ausentes():
    for codigo in ["001.001.001", "001.001.002", "013.005.007", "800.004"]:
        Material.objects.create(codigo=codigo, nome=codigo, estoque=99)
    call_command("importar_estoque", arquivo=FIX / "estoque.csv")
    saldos = dict(Material.objects.values_list("codigo", "estoque"))
    assert saldos == {"001.001.001": Decimal("12"), "001.001.002": 0, "013.005.007": Decimal("1234.5"), "800.004": 0}
    assert not Material.objects.filter(estoque_em__isnull=True).exists()
    imp = Importacao.objects.get()
    assert imp.linhas == 2 and imp.avisos == [
        "Quantidade inválida ignorada: 001.001.002 ('abc').",
        "Códigos com saldo sem cadastro (ignorados): 999.999.999.",
    ]

def test_estoque_vazio_aborta_sem_alterar_saldos(tmp_path):
    Material.objects.create(codigo="001.001.001", nome="X", estoque=5)
    vazio = tmp_path / "v.csv"; vazio.write_bytes(b"\xef\xbb\xbfCADPRO;QUAN3\r\n")
    with pytest.raises(CommandError, match="não tem nenhum material"):
        call_command("importar_estoque", arquivo=vazio)
    m = Material.objects.get(); assert m.estoque == 5 and m.estoque_em is None

def test_lista_curta():
    assert lista_curta([str(n) for n in range(10)]) == "0, 1, 2, 3, 4, 5, 6, 7 e mais 2"
```

- [ ] **Step 2:** `uv run pytest tests/test_importar_estoque.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente `gravar_estoque` com `Material.objects.update(...)` mais
  `bulk_update` dos que têm saldo. Use `lista_curta` nos avisos da Tarefa 6 também.
- [ ] **Step 4:** `uv run pytest tests/test_importar_estoque.py tests/test_importar_cadastro.py`.
  Esperado: PASS.
- [ ] **Step 5: Commit**: `Comando importar_estoque`

---

### Tarefa 8: `importar_saidas_scpi` (intervalo incremental)

**Files:**
- Modify: `scpi/gravacao.py`, com `gravar_saidas` e `periodo_saidas`
- Create: `scpi/management/commands/importar_saidas_scpi.py`
- Test: `tests/test_importar_saidas.py`

**Interfaces:**
- Consumes: `ler_saidas` (Tarefa 4), `executar` (Tarefa 5), `relatorios.baixar_saidas`
  (Tarefa 3).
- Produces:
  - `SOBREPOSICAO_SAIDAS = timedelta(days=7)`.
  - `periodo_saidas(hoje: date, desde: date | None = None, ate: date | None = None) -> tuple[date, date]`:
    - fim = `ate or hoje`;
    - início = `desde`; senão, o `periodo_ate` da última importação `SAIDAS` com sucesso menos
      `SOBREPOSICAO_SAIDAS`; senão, `date(hoje.year, 1, 1)`;
    - início depois do fim:
      `ErroImportacao("Saídas do SCPI: o início do período (dd/mm/aaaa) é depois do fim (dd/mm/aaaa).")`.
  - `gravar_saidas(leitura: Leitura) -> Resultado`:
    - `bulk_create(..., ignore_conflicts=True)`;
    - chave repetida dentro do CSV gera o aviso `"Linhas repetidas no CSV ignoradas: N."`;
    - `Resultado.linhas` = linhas novas, contadas antes e depois;
    - zero linhas não é erro.
  - **Comando `importar_saidas_scpi`:**
    - opções `--desde` e `--ate` (`dd/mm/aaaa`) e `--arquivo`;
    - o período vai para `executar(..., periodo=(de, ate))`, inclusive com `--arquivo`;
    - escreve `"Saídas do SCPI (dd/mm/aaaa a dd/mm/aaaa): N linhas novas."`.

- [ ] **Step 1: Testes que falham**

```python
def test_importa_saidas_sem_duplicar():
    call_command("importar_saidas_scpi", arquivo=FIX / "saidas.csv", desde="01/01/2026", ate="31/01/2026")
    assert SaidaSCPI.objects.count() == 4
    imp = Importacao.objects.get()
    assert (imp.linhas, imp.periodo_de, imp.periodo_ate) == (4, date(2026, 1, 1), date(2026, 1, 31))
    assert imp.avisos == ["Linhas repetidas no CSV ignoradas: 1."]
    call_command("importar_saidas_scpi", arquivo=FIX / "saidas.csv", desde="01/01/2026", ate="31/01/2026")
    assert SaidaSCPI.objects.count() == 4 and Importacao.objects.first().linhas == 0

def test_primeiro_periodo_comeca_em_janeiro():
    assert periodo_saidas(date(2026, 10, 10)) == (date(2026, 1, 1), date(2026, 10, 10))

def test_periodo_seguinte_sobrepoe_sete_dias_ao_ultimo_sucesso():
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2026, 10, 9))
    Importacao.objects.create(tipo="SAIDAS", situacao="FALHA", periodo_ate=date(2026, 10, 10))
    assert periodo_saidas(date(2026, 10, 10)) == (date(2026, 10, 2), date(2026, 10, 10))

def test_saida_retroativa_entra_na_importacao_seguinte(monkeypatch):
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2026, 1, 13))
    pedidos = []
    monkeypatch.setattr(relatorios, "baixar_saidas", lambda de, ate: pedidos.append(de) or (FIX / "saidas.csv").read_bytes())
    monkeypatch.setattr(timezone, "localdate", lambda: date(2026, 1, 14))
    call_command("importar_saidas_scpi")
    assert pedidos == [date(2026, 1, 6)]  # cobre o dia 12, antes do fim da anterior
    assert SaidaSCPI.objects.filter(data=date(2026, 1, 12)).count() == 2

def test_inicio_depois_do_fim_e_recusado():
    with pytest.raises(CommandError, match="é depois do fim"):
        call_command("importar_saidas_scpi", desde="10/10/2026", ate="01/10/2026", arquivo=FIX / "saidas.csv")
```

- [ ] **Step 2:** `uv run pytest tests/test_importar_saidas.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente. Chame o `timezone.localdate()` pelo módulo `django.utils.timezone`
  para o monkeypatch funcionar.
- [ ] **Step 4:** `uv run pytest tests/test_importar_saidas.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Comando importar_saidas_scpi com período incremental`

---

### Tarefa 9: `atualizar_catalogo` e disparo em segundo plano

**Files:**
- Create: `scpi/management/commands/atualizar_catalogo.py`
- Create: `scpi/disparo.py`
- Test: `tests/test_atualizar_catalogo.py`

**Interfaces:**
- Consumes: os três comandos (Tarefas 6 a 8); `Importacao.em_andamento` (Tarefa 2).
- Produces:
  - **Comando `atualizar_catalogo`:**
    - chama, nesta ordem, `importar_cadastro`, `importar_estoque` e `importar_saidas_scpi`,
      via `call_command`;
    - se um falhar com `CommandError`, escreve a mensagem no stderr e segue para o próximo;
    - no fim, se houve falha:
      `CommandError("Falharam: <nomes dos comandos separados por vírgula>.")`.
  - `iniciar_atualizacao() -> bool`:
    - se `Importacao.em_andamento().exists()`, devolve `False` e não inicia nada;
    - senão, roda
      `subprocess.Popen([sys.executable, str(settings.BASE_DIR / "manage.py"), "atualizar_catalogo"], cwd=settings.BASE_DIR, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True, creationflags=...)`
      e devolve `True`;
    - no Windows, `creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS`
      (0 nos outros sistemas), para o processo sobreviver à requisição;
    - dois cliques quase juntos podem iniciar dois processos: a trava por tipo (Tarefa 5) faz o
      segundo recusar cada importação. Registre isso num comentário.

- [ ] **Step 1: Testes que falham**

```python
def test_atualizar_roda_os_tres_e_segue_depois_de_uma_falha(monkeypatch):
    feitos = []
    def falso(nome, *a, **k):
        feitos.append(nome)
        if nome == "importar_cadastro":
            raise CommandError("Cadastro: o CSV não tem nenhum material; nada foi alterado.")
    monkeypatch.setattr("scpi.management.commands.atualizar_catalogo.call_command", falso)
    with pytest.raises(CommandError, match=r"^Falharam: importar_cadastro\.$"):
        call_command("atualizar_catalogo")
    assert feitos == ["importar_cadastro", "importar_estoque", "importar_saidas_scpi"]

def test_disparo_inicia_processo_separado(monkeypatch):
    chamadas = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: chamadas.append((args, kw)))
    assert iniciar_atualizacao() is True
    args, kw = chamadas[0]
    assert args[1:] == [str(settings.BASE_DIR / "manage.py"), "atualizar_catalogo"]
    assert kw["cwd"] == settings.BASE_DIR

def test_disparo_recusa_com_importacao_em_andamento(monkeypatch):
    Importacao.objects.create(tipo="ESTOQUE")
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("não deveria iniciar"))
    assert iniciar_atualizacao() is False

def test_importacao_interrompida_nao_bloqueia_o_disparo(monkeypatch):
    Importacao.objects.create(tipo="ESTOQUE", inicio=timezone.now() - timedelta(hours=2))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    assert iniciar_atualizacao() is True
```

- [ ] **Step 2:** `uv run pytest tests/test_atualizar_catalogo.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente. `disparo.py` chama `subprocess.Popen` pelo módulo.
- [ ] **Step 4:** `uv run pytest tests/test_atualizar_catalogo.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Comando atualizar_catalogo e disparo em segundo plano`

---

### Tarefa 10: Catálogos dos formulários

**Files:**
- Modify: `pedidos/regras.py`, com `estoque_inteiro`
- Create: `catalogo/catalogos.py`
- Test: `tests/test_regras_normalizacao.py` (`estoque_inteiro`), `tests/test_catalogos.py`

**Interfaces:**
- Consumes: `Material`, `ItemLimpeza`, `Opcao`, `SaidaSCPI`; `norm_u`.
- Produces:
  - `estoque_inteiro(valor: object) -> int`, em `pedidos/regras.py`:
    - tradução de `estoqueInteiro_` (Util.gs);
    - aceita `Decimal`, número ou texto com vírgula;
    - devolve o `floor` se o valor for ≥ 1, senão 0; inválido vira 0.
  - `ItemCatalogo` (dataclass, frozen), em `catalogo/catalogos.py`: `codigo`, `nome`,
    `unidade`, `categoria`, `grupo`, `subgrupo: str`, `estoque: Decimal`, `disponivel: int`,
    `duplicado: bool`.
  - `GRUPOS_OCULTOS_PADRAO = ("GERAL", "MATERIAL DE EXPEDIENTE ( ESCRITORIO)", "MATERIAL DE CONSUMO")`.
    - `grupos_ocultos_ab() -> set[str]`: valores de `Opcao` `GRUPO_OCULTO_AB`, ou o padrão se a
      lista estiver vazia;
    - cada valor normalizado com `norm_u(...).replace(" ", "")`, como no `Catalogo.gs`.
  - `catalogo_limpeza() -> list[ItemCatalogo]`:
    - `ItemLimpeza` com material não oculto, na ordem do modelo;
    - nome e unidade exibidos têm prioridade;
    - `duplicado` vem do material.
  - `CatalogoAB(itens: list[ItemCatalogo], codigos: int, na_limpeza: int, ocultos: int, sem_cadastro: list[str])`,
    dataclass.
  - `catalogo_ab() -> CatalogoAB | None`:
    - devolve `None` se nenhum material tiver `estoque_em` (saldo nunca importado);
    - os códigos de `SaidaSCPI` entram por número de ocorrências decrescente, com o código
      crescente como desempate (`codigos` = quantos);
    - para cada código, nesta ordem:
      1. sem material: vai para `sem_cadastro`;
      2. em `ItemLimpeza`: soma em `na_limpeza`;
      3. oculto, ou grupo em `grupos_ocultos_ab()`: soma em `ocultos`;
      4. senão: vira item, com `disponivel = estoque_inteiro(estoque)` e `categoria=""`;
    - duas consultas no máximo para os materiais, sem N+1.
  - `materiais_avulsa() -> QuerySet[Material]`: `Material` com `oculto=False`, na ordem do modelo.

- [ ] **Step 1: Testes que falham**

```python
@pytest.mark.parametrize(("valor", "esperado"), [
    ("2,5", 2), (-3, 0), ("x", 0), (Decimal("12.0000"), 12), (Decimal("0.9"), 0), (None, 0), ("", 0), (10, 10)])
def test_estoque_inteiro(valor, esperado):
    assert estoque_inteiro(valor) == esperado
```

```python
def saidas(cadpro, n):
    for i in range(n):
        SaidaSCPI.objects.create(id_requi=f"{cadpro}-{i}", cadpro=cadpro, data=date(2026, 1, 1), qtd=1, valor=0)

def test_ab_ordena_por_ocorrencias_e_exclui_limpeza_ocultos_e_grupos_ocultos():
    agora = timezone.now()
    m = lambda c, **kw: Material.objects.create(codigo=c, nome=c, estoque_em=agora, **kw)
    m("A", estoque=Decimal("2.5")); m("B", estoque=10); m("L"); m("O", oculto=True); m("G", grupo="Material  de Consumo")
    Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Limpeza")
    ItemLimpeza.objects.create(material=Material.objects.get(codigo="L"), categoria="Limpeza")
    for codigo, n in [("A", 2), ("B", 3), ("L", 5), ("O", 1), ("G", 1), ("Z", 4)]:
        saidas(codigo, n)
    ab = catalogo_ab()
    assert [(i.codigo, i.disponivel) for i in ab.itens] == [("B", 10), ("A", 2)]
    assert (ab.codigos, ab.na_limpeza, ab.ocultos, ab.sem_cadastro) == (6, 1, 2, ["Z"])

def test_ab_indisponivel_sem_saldo_importado():
    Material.objects.create(codigo="A", nome="A"); saidas("A", 1)
    assert catalogo_ab() is None

def test_grupos_ocultos_da_lista_substituem_o_padrao():
    Opcao.objects.create(lista="GRUPO_OCULTO_AB", valor="Ferramentas")
    assert grupos_ocultos_ab() == {"FERRAMENTAS"}

def test_limpeza_usa_nome_exibido_e_esconde_oculto():
    ...  # item com nome_exibido "Detergente" → nome "Detergente"; item cujo material está oculto não aparece

def test_avulsa_so_nao_ocultos():
    ...
```

- [ ] **Step 2:** `uv run pytest tests/test_catalogos.py tests/test_regras_normalizacao.py`.
  Esperado: FAIL.
- [ ] **Step 3:** Implemente. A contagem usa
  `SaidaSCPI.objects.values("cadpro").annotate(n=Count("id")).order_by("-n", "cadpro")`.
- [ ] **Step 4:** Rode os mesmos testes. Esperado: PASS. Para conferir as consultas, use
  `django_assert_max_num_queries(4)` em `catalogo_ab()`.
- [ ] **Step 5: Commit**: `Catálogos dos formulários: limpeza, AB por ocorrências e avulsa`

---

### Tarefa 11: Saúde do catálogo

**Files:**
- Create: `catalogo/saude.py`
- Test: `tests/test_saude.py`

**Interfaces:**
- Consumes: `Importacao` (Tarefa 2); `catalogo_limpeza`, `catalogo_ab` (Tarefa 10);
  `lista_curta` (Tarefa 7); `CentroCusto`.
- Produces:
  - `ItemSaude(nivel: str, texto: str)` (dataclass), com `nivel` em `"ok"`, `"aviso"` ou
    `"erro"`.
  - `saude_do_catalogo(agora: datetime | None = None) -> list[ItemSaude]`, nesta ordem e com
    estes textos (datas em `dd/mm/aaaa HH:MM`, no horário local):

| Situação | Nível | Texto |
|---|---|---|
| Tipo sem nenhuma importação | erro | `"<Tipo>: nenhuma importação ainda."` |
| Última importação do tipo falhou | erro | `"<Tipo>: a última importação falhou em <fim>: <erro> Os dados anteriores continuam valendo."` |
| Última está interrompida | aviso | `"<Tipo>: a importação iniciada em <inicio> não terminou (interrompida)."` |
| Última em andamento | ok | `"<Tipo>: importação em andamento desde <inicio>."` |
| Última concluída sem avisos | ok | `"<Tipo>: atualizado em <fim>."` |
| Última concluída com avisos | aviso | `"<Tipo>: atualizado em <fim>, com avisos: <avisos separados por espaço>"` |
| Cadastro existe | ok | `"Cadastro: N materiais; M ocultos no SCPI ficam fora de todos os formulários."` |
| Há duplicados | aviso | `"Códigos repetidos no cadastro (bloqueados): <lista_curta>."` |
| `catalogo_ab()` é None | erro | `"Sem saldo importado: o formulário AB fica indisponível até a próxima importação de estoque."` |
| Saldo mais antigo que 24 h (máx. `estoque_em`) | aviso | `"O saldo de estoque não é atualizado desde <data> (mais de 24 h)."` |
| Formulário de limpeza | ok | `"Formulário de limpeza: N itens."` |
| Itens de limpeza com material oculto | aviso | `"Itens da lista de limpeza ocultos no SCPI (não aparecem): <lista_curta>."` |
| AB disponível | ok | `"Formulário AB: N itens de M códigos com saída no SCPI (X também na lista de limpeza, que prevalece; Y ocultos ou em grupo oculto)."` |
| AB com códigos sem cadastro | aviso | `"Códigos com saída no SCPI sem cadastro (não aparecem): <lista_curta>."` |
| Nenhum `CentroCusto` | aviso | `"Nenhum centro de custo cadastrado: não é possível confirmar atendimentos nem registrar saídas."` |

  As três primeiras linhas de importação seguem a ordem Cadastro, Estoque, Saídas do SCPI e
  usam `get_tipo_display()`.

- [ ] **Step 1: Testes que falham.** Um teste por linha da tabela, conferindo `nivel` e
  `texto` exatos. Os mais importantes:

```python
def test_falha_recente_aparece_como_erro_mesmo_com_sucesso_antes():
    ok = Importacao.objects.create(tipo="ESTOQUE", situacao="SUCESSO", fim=timezone.now())
    Importacao.objects.create(tipo="ESTOQUE", situacao="FALHA", erro="Estoque: o CSV não tem nenhum material; nada foi alterado.",
                              inicio=ok.inicio + timedelta(minutes=5), fim=ok.inicio + timedelta(minutes=6))
    item = itens_de("Estoque:")[0]
    assert item.nivel == "erro" and "a última importação falhou em" in item.texto and "continuam valendo" in item.texto

def test_importacao_interrompida_vira_aviso():
    Importacao.objects.create(tipo="CADASTRO", inicio=timezone.now() - timedelta(hours=2))
    assert itens_de("Cadastro: a importação iniciada")[0].nivel == "aviso"

def test_saldo_velho_gera_aviso():
    Material.objects.create(codigo="A", nome="A", estoque_em=timezone.now() - timedelta(hours=25))
    assert any(i.nivel == "aviso" and "mais de 24 h" in i.texto for i in saude_do_catalogo())

def test_banco_vazio_nao_quebra():
    textos = [i.texto for i in saude_do_catalogo()]
    assert "Cadastro: nenhuma importação ainda." in textos
    assert "Sem saldo importado: o formulário AB fica indisponível até a próxima importação de estoque." in textos
```

  (`itens_de(prefixo)` é um auxiliar do teste: filtra `saude_do_catalogo()` pelo começo do
  texto.)
- [ ] **Step 2:** `uv run pytest tests/test_saude.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente.
- [ ] **Step 4:** `uv run pytest tests/test_saude.py`. Esperado: PASS.
- [ ] **Step 5: Commit**: `Saúde do catálogo`

---

### Tarefa 12: Página "Catálogo" com saúde, importações e "Atualizar agora"

**Files:**
- Create: `catalogo/views.py`, `catalogo/urls.py` (`app_name = "catalogo"`)
- Create: `catalogo/templates/catalogo/situacao.html` (página),
  `catalogo/templates/catalogo/_situacao.html` (saúde e tabela) e
  `catalogo/templates/catalogo/_saude.html` (lista da saúde, reutilizada pelo painel no
  subprojeto 3)
- Modify: `config/urls.py`: `path("almoxarifado/catalogo/", include("catalogo.urls"))`, antes
  de `almoxarifado/`
- Modify: `interface/navegacao.py`: `ItemMenu("Catálogo", "catalogo:situacao")` entre Painel e
  Cadastros
- Modify: `CLAUDE.md` (app `scpi`, comandos de importação, `playwright install chromium`,
  decisões 2 a 4 e 7) e `README.md` (seção Desenvolvimento: `uv run playwright install chromium`
  e os comandos)
- Test: `tests/test_pagina_catalogo.py`; ajuste `tests/test_interface.py` se ele fixa os itens
  do menu

**Interfaces:**
- Consumes: `saude_do_catalogo` (Tarefa 11), `iniciar_atualizacao` (Tarefa 9), `Importacao`
  (Tarefa 2).
- Produces:
  - **Rotas:**
    - `catalogo:situacao`: GET `/almoxarifado/catalogo/`, com `login_required`;
    - `catalogo:atualizar`: POST `/almoxarifado/catalogo/atualizar/`, com `login_required` e
      `require_POST`.
  - **Contexto de `situacao`:**
    - `saude` (lista de `ItemSaude`);
    - `importacoes`: as últimas 20 `Importacao`;
    - `em_andamento: bool`.
    - Com o cabeçalho `HX-Request`, renderiza só `_situacao.html`.
  - **`atualizar`:**
    - `True` gera `messages.success("Atualização iniciada. Cadastro, estoque e saídas são importados em sequência; acompanhe abaixo.")`;
    - `False` gera `messages.warning("Já há uma importação em andamento. Aguarde terminar.")`;
    - nos dois casos, redireciona para `catalogo:situacao`.
- Apresentação, com classes do `components.css`:
  - **Saúde:** lista com `.badge` com texto (`OK`, `Aviso`, `Erro` →
    `.badge-success/-warning/-danger`).
  - **Tabela:**
    - `.table-wrapper` > `.table`;
    - colunas Tipo, Início, Fim, Situação (badge com texto; "Interrompida" quando
      `interrompida`), Período, Linhas, Avisos/erro;
    - período em `dd/mm/aaaa a dd/mm/aaaa` ou "—";
    - estado vazio: "Nenhuma importação ainda.".
  - **Botão:**
    - `<form method="post">` com `{% csrf_token %}` e `.btn.btn-primary` "Atualizar agora", no
      bloco `tools`;
    - com `em_andamento`, o botão fica `disabled` e ao lado aparece o texto "Importação em
      andamento".
  - **Atualização automática:**
    - com `em_andamento`, o `<section id="situacao-catalogo">` recebe
      `hx-get="{% url 'catalogo:situacao' %}"`, `hx-trigger="every 5s"` e `hx-swap="outerHTML"`;
    - parado, não há polling.

- [ ] **Step 1: Testes que falham**

```python
def test_pagina_exige_login(client):
    r = client.get(reverse("catalogo:situacao"))
    assert r.status_code == 302 and r.url.startswith(reverse("login"))

def test_pagina_mostra_saude_e_importacoes(client, usuario_logado):
    Importacao.objects.create(tipo="ESTOQUE", situacao="FALHA", erro="Estoque: falhou.", fim=timezone.now())
    r = client.get(reverse("catalogo:situacao"))
    assert r.status_code == 200
    assert "Cadastro: nenhuma importação ainda." in r.text and ">Erro<" in r.text
    assert "Estoque: falhou." in r.text and "Atualizar agora" in r.text
    assert f'href="{reverse("catalogo:situacao")}" aria-current="page">Catálogo</a>' in r.text
    assert "every 5s" not in r.text

def test_em_andamento_desabilita_o_botao_e_atualiza_sozinho(client, usuario_logado):
    Importacao.objects.create(tipo="SAIDAS")
    r = client.get(reverse("catalogo:situacao"))
    assert "Importação em andamento" in r.text and "every 5s" in r.text and "disabled" in r.text

def test_htmx_recebe_so_o_trecho(client, usuario_logado):
    r = client.get(reverse("catalogo:situacao"), HTTP_HX_REQUEST="true")
    assert 'id="situacao-catalogo"' in r.text and 'class="side' not in r.text

def test_atualizar_so_por_post(client, usuario_logado):
    assert client.get(reverse("catalogo:atualizar")).status_code == 405

def test_atualizar_inicia_e_avisa(client, usuario_logado, monkeypatch):
    monkeypatch.setattr("catalogo.views.iniciar_atualizacao", lambda: True)
    r = client.post(reverse("catalogo:atualizar"), follow=True)
    assert "Atualização iniciada." in r.text

def test_atualizar_recusa_quando_ja_em_andamento(client, usuario_logado, monkeypatch):
    monkeypatch.setattr("catalogo.views.iniciar_atualizacao", lambda: False)
    r = client.post(reverse("catalogo:atualizar"), follow=True)
    assert "Já há uma importação em andamento." in r.text
```

  (`usuario_logado` é uma fixture local: `create_user` mais `client.force_login`.)
- [ ] **Step 2:** `uv run pytest tests/test_pagina_catalogo.py`. Esperado: FAIL.
- [ ] **Step 3:** Implemente as views, os templates, as rotas e o menu. Depois atualize o
  `CLAUDE.md` e o `README.md`.
- [ ] **Step 4:** Rode a suíte inteira. Esperado: PASS. Abra `/almoxarifado/catalogo/` no
  runserver e confira, nos temas claro e escuro e com 375 px de largura: badges com texto,
  tabela com rolagem lateral e o botão.
- [ ] **Step 5: Commit**: `Página do catálogo com saúde, importações e "Atualizar agora"`

---

### Tarefa 13: Verificação final

- [ ] **Step 1:** Rode tudo:
  - `uv run pytest`
  - `uv run ruff check . && uv run ruff format --check .`
  - `uv run python manage.py makemigrations --check --dry-run`
  - `DEBUG=0 SECRET_KEY=x ALLOWED_HOSTS=x uv run python manage.py check --deploy` (ou o teste
    que já cobre isso)

  Esperado: tudo verde, "No changes detected" e nenhum aviso.
- [ ] **Step 2:** Rode `uv run playwright install chromium` no PowerShell.
- [ ] **Step 3 (manual, com o usuário):** com `SAEP_USER` e `SAEP_PASS` no `.env`:
  1. Rode, nesta ordem: `importar_cadastro`, `importar_estoque` e
     `importar_saidas_scpi --desde 01/01/2026`.
  2. Confira na página "Catálogo" as contagens: cadastro com cerca de 11,7 mil materiais,
     estoque com cerca de 1,4 mil saldos e cerca de 5 mil saídas.
  3. Responda aos "Pontos a confirmar no SCPI real".
  4. Se um seletor falhar, o screenshot fica em `logs/scpi-*.png`.
- [ ] **Step 4:** Faça a revisão final do branch, conforme o modo de execução escolhido.
- [ ] **Step 5:** Faça o push e abra o PR só com a autorização do usuário.

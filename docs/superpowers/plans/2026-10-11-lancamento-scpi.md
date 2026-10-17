# Subprojeto 4 — Lançamento no SCPI: plano de implementação

> **Situação:** executado. As caixas abaixo não foram marcadas durante a execução; o que vale
> hoje está no código e no `CLAUDE.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** As linhas de saída `PENDENTE` chegam ao SCPI pelo robô `lancar_saidas`, que roda
sobre o banco. O almoxarifado dispara o robô por botão (real ou simulação), acompanha o
andamento na página "Lançamentos SCPI" e resolve as travas (`VERIFICAR`, `EM_LANCAMENTO`
órfã, `ERRO`) sem sair do sistema.

**Architecture:**
- `pedidos.ExecucaoRobo`: registro de cada execução do robô (modo, quem iniciou, situação,
  resumo e log).
- `scpi/requisicoes.py` (puro, sem ORM nem Playwright): agrupa as linhas pendentes por lote,
  aplica as travas e valida cada requisição.
- `scpi/lancamento.py`: orquestra uma execução sobre o banco. Fala com o SCPI só por um
  protocolo (`SCPI`), então os testes usam um SCPI simulado.
- `scpi/lancador.py`: a navegação do `lancar_saidas.py` original (Playwright), que implementa
  o protocolo. Não é coberta pelos testes, como `relatorios.py`.
- Comando `lancar_saidas` (fino) e `scpi.disparo.iniciar_lancamento` (processo separado).
- `pedidos.servicos.resolver_lote` (travas) e a página `pedidos/views/lancamentos.py`, com
  cartão no painel.

**Tech Stack:** Python 3.13, Django 6.x, Playwright (já instalado), HTMX 4.0.0
(vendorizado), mysqlclient, pytest + pytest-django, ruff.

**Spec:** `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`, seções 2
(interface: item "Lançamentos SCPI"), 3 (`ExecucaoRobo`, `LinhaSaida.status`), 5 (fluxos 6 e
7), 6 (robô interrompido), 7 (testes do robô) e 9 (item 4).

**Código de referência (fora do repositório):**
- `ER:` = `joaorighetto/extrair-relatorio`, commit `cce15aa3706be09bf1cdb2b6c8768b2ab9a4a622`.
  Para ler: `GH_TOKEN=$(gh auth token --user joaorighetto) gh repo clone
  joaorighetto/extrair-relatorio <pasta-temporária> -- --depth 1`. O arquivo que interessa é
  `ER:lancar_saidas.py` (1163 linhas).
- `AS:` = `../CentralAlmoxarifado/`. `AS:tests/lancar_saidas_lote_test.py` traz os casos do
  agrupamento por lote, adaptados na Tarefa 2.

## Decisões deste plano

Pontos que a spec deixa em aberto ou que mudam com o banco:

1. **Agrupamento só por lote.** Cada `Atendimento` grava as linhas com o mesmo cabeçalho e
   `lote` = número do pedido; então lote = requisição no SCPI. O cabeçalho (data, recebedor,
   centro de custo, tipo e placa) diferente dentro do mesmo lote é erro de validação, não
   motivo para dividir.
2. **Só `PENDENTE` vai ao SCPI.** O original relançava sozinho linhas com "ERRO"; aqui `ERRO`
   espera alguém liberar (spec, fluxo 7). Um lote com qualquer linha `EM_LANCAMENTO`,
   `VERIFICAR` ou `ERRO` fica inteiro de fora, contado como "travado". Assim uma requisição
   nunca sai dividida.
3. **Trava entre processos com `GET_LOCK('almoxarifado:lancar_saidas')`**, a mesma
   `scpi.execucao.trava` das importações, no lugar do `.lancar_saidas.lock` do original. Cai
   sozinha se o processo morrer; o arquivo exigia apagar à mão. O botão também consulta
   `ExecucaoRobo` no banco (spec, fluxo 6).
4. **A trava `EM_LANCAMENTO` é condicional e confirmada antes do Salvar.**
   - A spec (fluxo 6) diz "antes de abrir o formulário". O original grava a trava depois de
     preencher e conferir, logo antes do clique, e este plano segue o original. Uma falha no
     preenchimento não lançou nada; travar antes deixaria um `EM_LANCAMENTO` órfão para
     conferir à toa.
   - A gravação trava as linhas do lote (`select_for_update`). Ela só acontece se todas ainda
     estão `PENDENTE`; senão o lote é descartado sem salvar.
   - A transação fecha antes do clique.
5. **Os resultados (`LANCADA`, `ERRO`, `VERIFICAR`) gravam valores absolutos** pelo `id` das
   linhas, como o original gravava na planilha.
6. **O journal continua**, em `LOG_DIR/lancar_saidas_journal.jsonl`: último recurso se o
   banco cair entre o Salvar e a gravação do número.
7. **`ExecucaoRobo` sem o campo `tipo`.** As importações já têm o registro delas
   (`catalogo.Importacao`, subprojeto 2). Ganha `simulacao` e `erro`. Situações:
   - `ANDAMENTO` ("Em andamento");
   - `SUCESSO` ("Concluída");
   - `ATENCAO` ("Concluída com pendências"): houve erro ou "verificar";
   - `FALHA` ("Falhou").
   O limite de 1 h é o `catalogo.models.LIMITE_ANDAMENTO`.
8. **A simulação nunca vira lançamento real.** `--dry-run` ou `ExecucaoRobo.simulacao`, um
   dos dois basta. O que valer fica gravado na execução.
9. **Sem `--desde`.** O original filtrava "a partir de hoje" para fugir do histórico da
   planilha. Aqui `PENDENTE` já é explícito, e o robô lança com a data efetiva. `--limite N`
   continua, para os primeiros testes reais.
10. **Resolução de travas por lote, na página "Lançamentos SCPI"**, com três ações:
    - "Informar requisição" (→ `LANCADA`, número `000000/00`);
    - "Liberar para relançar" (→ `PENDENTE`);
    - "Não lançar" (→ `NAO_LANCAR`).
    Regras:
    - valem só para as linhas do lote em `VERIFICAR`, `EM_LANCAMENTO` ou `ERRO`;
    - ficam recusadas enquanto houver execução em andamento;
    - liberar um lote com linha `VERIFICAR`/`EM_LANCAMENTO` exige marcar "Conferi no SCPI: a
      requisição não foi gravada".
    A linha não é editada: ela espelha o atendimento e o recibo. "Corrigir" um `ERRO` é
    corrigir a causa e liberar. As causas são o cadastro de centros de custo (o robô relê a
    cada execução), o saldo ou a placa no SCPI.
11. **Admin: casos raros.** O superusuário edita `status`, `requisicao_scpi`, `lancado_em` e
    `mensagem` de uma `LinhaSaida`; o resto continua só leitura. `ExecucaoRobo` é só leitura.
12. **`mensagem` da linha guarda o último acontecimento.** Ela é sobrescrita pelo robô e, na
    resolução, recebe quem resolveu, quando e o estado anterior.
13. **Botões no painel e na página.** O cartão "Lançamentos no SCPI" do painel mostra os lotes
    aguardando e os travados, com o botão "Lançar no SCPI". A página "Lançamentos SCPI" (menu
    lateral) tem também "Simular", o andamento e as travas.

## Global Constraints

- `requires-python = ">=3.13,<3.14"`; Django `>=6.0,<7`. Nenhuma dependência nova (o
  Playwright já está no projeto).
- Testes contra MySQL/MariaDB, nunca SQLite. Os testes nunca abrem o navegador nem o SCPI.
- `pedidos` já tem `0001_initial.py`: mudança de modelo regenera essa migration (apagar,
  `makemigrations pedidos`, `migrate pedidos zero` + `migrate`). Nada de migration de
  conversão.
- Textos de interface, mensagens, nomes de código e commits em português (pt-BR).
- Estado nunca só por cor (selo sempre com texto); lote, código, placa e requisição em `.mono`.
- Toda requisição que grava é POST com `{% csrf_token %}`; logout continua num único formulário
  por página. Scripts só no `<head>` com `defer`.
- A navegação copiada de `ER:lancar_saidas.py` (seletores, esperas, JS, ordem dos campos) não
  muda. Só trocam o que a Tarefa 4 lista.
- O robô nunca clica em Salvar sem antes confirmar `EM_LANCAMENTO` no banco. Qualquer falha
  depois do clique é `VERIFICAR`, nunca `PENDENTE` nem `ERRO`. O sistema nunca destrava
  sozinho.
- Commits num branch `lancamento-scpi` criado a partir do `main`, com
  `git -c user.name="João" -c user.email="jm_zr@icloud.com" commit ...`. Toda mensagem termina
  com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Ao fim de cada tarefa: `uv run ruff format -q .`, `uv run ruff check .`,
  `uv run ruff format --check .` e `uv run python manage.py makemigrations --check --dry-run`
  limpos, e `uv run pytest -q` verde.

## Review Focus

1. **Falha entre o clique em Salvar e a gravação do resultado.** Pode ser exceção qualquer no
   Salvar, número que não aparece ou banco fora do ar ao gravar `LANCADA`. As linhas ficam
   `VERIFICAR` ou `EM_LANCAMENTO`, nunca voltam a `PENDENTE`. O número vai para o journal
   (Tarefa 3).
2. **Simulação que lançaria de verdade.** Botão "Simular", `--dry-run` ou execução gravada
   como simulação: o Salvar nunca é chamado e nenhuma linha muda de status (Tarefas 3 e 5).
3. **Linha alterada enquanto o robô roda** (admin, ou um lote liberado e travado de novo).
   - Se no momento da trava alguma linha do lote não está mais `PENDENTE`, o lote não vai ao
     SCPI.
   - A página recusa resolver travas durante uma execução (Tarefas 3 e 6).
4. **Dois cliques ou dois processos.** Só um robô roda. O segundo grava a execução como
   `FALHA` ("Outro lançamento já está em andamento.") sem tocar em linha nenhuma (Tarefas 3
   e 5).
5. **Resolução descuidada ou forjada.**
   - Liberar um `VERIFICAR` sem marcar a conferência é recusado.
   - Número de requisição fora do formato, ação desconhecida ou lote inexistente voltam com
     mensagem, nunca erro 500.
   - Linhas `PENDENTE`/`LANCADA` do lote nunca mudam (Tarefas 6 e 7).

---

### Task 1: `ExecucaoRobo` e admin

**Files:**
- Modify: `pedidos/models.py` (novo modelo no fim), `pedidos/admin.py`
- Regenerate: `pedidos/migrations/0001_initial.py`
- Test: `tests/test_modelos_execucao.py`

**Interfaces:**
- Consumes: `catalogo.models.LIMITE_ANDAMENTO` (1 h).
- Produces:
  - `ExecucaoRobo` com os campos:
    - `simulacao` (`BooleanField("simulação", default=False)`);
    - `iniciada_por` (FK usuário, `null=True`, `blank=True`, `PROTECT`,
      `related_name="execucoes_robo"`);
    - `inicio` (`default=timezone.now`), `fim` (null);
    - `situacao` (`Situacao`: `ANDAMENTO`, `SUCESSO`, `ATENCAO`, `FALHA`, rótulos da Decisão 7;
      default `ANDAMENTO`);
    - `resumo` (`JSONField(default=dict, blank=True)`), `log` (`TextField(blank=True)`),
      `erro` (`TextField(blank=True)`).
  - Meta: `ordering=["-inicio"]`, `verbose_name="execução do robô"`,
    `verbose_name_plural="execuções do robô"`.
  - `__str__`: `"Simulação #<id>"` ou `"Lançamento #<id>"`.
  - `ExecucaoRobo.em_andamento(agora=None) -> QuerySet` e a propriedade `interrompida`, iguais
    às de `Importacao`.

- [ ] **Step 1: Write the failing tests**

```python
def test_em_andamento_ignora_interrompida_e_terminada():
    agora = timezone.now()
    viva = ExecucaoRobo.objects.create()
    ExecucaoRobo.objects.create(inicio=agora - timedelta(hours=2))  # interrompida
    ExecucaoRobo.objects.create(situacao="SUCESSO", fim=agora)
    assert list(ExecucaoRobo.em_andamento(agora)) == [viva]

def test_interrompida_so_quando_andamento_passa_de_uma_hora():
    velha = ExecucaoRobo(inicio=timezone.now() - timedelta(hours=1, minutes=1))
    assert velha.interrompida
    assert not ExecucaoRobo(inicio=velha.inicio, situacao="FALHA").interrompida

def test_str_diz_o_modo():
    e = ExecucaoRobo.objects.create(simulacao=True)
    assert str(e) == f"Simulação #{e.pk}"

def test_execucao_e_so_leitura_no_admin(admin_client):
    e = ExecucaoRobo.objects.create()
    url = reverse("admin:pedidos_execucaorobo_change", args=[e.pk])
    assert admin_client.post(url, {"situacao": "SUCESSO"}).status_code == 403

def test_superusuario_corrige_status_da_linha_no_admin(admin_client):
    pedido = criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    linha = pedido.atendimento.linhas.get()
    url = reverse("admin:pedidos_linhasaida_change", args=[linha.pk])
    r = admin_client.post(url, {"status": "LANCADA", "requisicao_scpi": "003354/26",
                                "lancado_em_0": "11/10/2026", "lancado_em_1": "10:00:00",
                                "mensagem": "conferido"})
    assert r.status_code == 302
    linha.refresh_from_db()
    assert (linha.status, linha.requisicao_scpi, linha.codigo) == ("LANCADA", "003354/26", "023.001.002")

def test_equipe_sem_superusuario_nao_edita_linha(client):
    equipe = get_user_model().objects.create_user("00010", password="x", is_staff=True)
    equipe.user_permissions.add(*Permission.objects.filter(codename__in=["view_linhasaida", "change_linhasaida"]))
    client.force_login(equipe)
    linha = criar_pedido(atendido=True, linhas=[("ERRO", "")]).atendimento.linhas.get()
    url = reverse("admin:pedidos_linhasaida_change", args=[linha.pk])
    assert client.post(url, {"status": "PENDENTE"}).status_code == 403
```

(`criar_pedido` vem de `tests/cenario.py`. Se o formato do campo de data e hora no admin
divergir, ajuste o POST ao widget real; a asserção não muda.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_modelos_execucao.py -q`
Expected: FAIL (`ImportError: cannot import name 'ExecucaoRobo'`)

- [ ] **Step 3: Implement**
  - Escreva o modelo. Regenere a migration: apague `pedidos/migrations/0001_initial.py`, rode
    `makemigrations pedidos` e depois `migrate pedidos zero` + `migrate`.
  - No admin:
    - `ExecucaoRobo` registrada com `SoLeituraAdmin`
      (`list_display = ["inicio", "simulacao", "situacao", "iniciada_por", "fim"]`);
    - `LinhaSaidaAdmin` passa a herdar `admin.ModelAdmin`, sem adicionar nem apagar;
    - `has_change_permission` = `request.user.is_superuser`;
    - `readonly_fields` = todos os campos menos `status`, `requisicao_scpi`, `lancado_em` e
      `mensagem`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_modelos_execucao.py tests/test_modelos_pedidos.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `ExecucaoRobo e correção de linhas de saída pelo admin`

---

### Task 2: Requisições pendentes (puro)

**Files:**
- Create: `scpi/requisicoes.py`
- Test: `tests/test_scpi_requisicoes.py`

**Interfaces:**
- Consumes:
  - de `pedidos.regras`: `resolver_centro_custo(cc_nome, placa, centros) -> CentroResolvido`,
    `Centro`, `norm_u`, `norm_placa`, `TIPOS_SAIDA_PADRAO` e as constantes de status;
  - linhas com os atributos de `LinhaSaida` (`id`, `lote`, `status`, `data: date`,
    `qtd: Decimal`, `codigo`, `recebedor`, `centro_custo`, `tipo_saida`, `placa`). Os testes
    passam `LinhaSaida(...)` não salvas.
- Produces (usados nas Tarefas 3 e 4):
  - exceções `ErroValidacao`, `ErroSCPI` (falha antes do Salvar), `ResultadoIncerto` (depois
    do Salvar) e `FalhaCritica` (resultado que não foi gravado no banco). Docstrings do
    original, sem "planilha".
  - `RE_CADPRO = re.compile(r"^\d{3}\.\d{3}\.\d{3}$")` e
    `RE_REQUI = re.compile(r"\b(\d{6}/\d{2})\b")`.
  - `ESTADOS_TRAVA = (EM_LANCAMENTO, VERIFICAR, ERRO)`.
  - `@dataclass Item(cadpro: str, qtd: str, placa: str)`: `qtd` no formato do SCPI.
  - `@dataclass Requisicao(lote: str, linhas: list, data: str = "", tipo_saida: str = "",
    cod_ccusto: str = "", recebedor: str = "", itens: list[Item] = [], erro: str = "")`:
    - `data` em dd/mm/aaaa;
    - `ids` (property) é a lista dos `id` das linhas;
    - `__str__` → `"<lote> | <data> | <recebedor> | c.custo <cod> | <n> item(ns)"`.
  - `@dataclass Selecao(requisicoes: list[Requisicao], travados: list[str])`.
  - `qtd_scpi(qtd: Decimal) -> str`: `format(qtd.normalize(), "f").replace(".", ",")`.
  - `validar(req: Requisicao, centros: list[Centro]) -> None`: preenche os campos ou levanta
    `ErroValidacao("; ".join(erros))`. Os textos:
    - `"linhas do lote com data, recebedor, centro de custo, tipo ou placa diferentes"`;
    - `"recebedor vazio"`;
    - o `erro` de `resolver_centro_custo`;
    - `"'Tipo Saída' inválido '<x>' (aceitos: BALCÃO, ENTREGA, …)"`, com a comparação por
      `norm_u` e o valor gravado com a grafia da lista;
    - `"código '<c>' fora do padrão 000.000.000"`;
    - `"código <c> repetido na mesma requisição"`;
    - `"quantidade de <c> deve ser > 0"`.
  - `selecionar(linhas, centros) -> Selecao`:
    - agrupa as `PENDENTE` por `lote`, na ordem da primeira linha;
    - ignora os outros status;
    - tira os lotes com alguma linha em `ESTADOS_TRAVA` (vão para `travados`, sem repetir);
    - chama `validar` em cada um e guarda o texto do `ErroValidacao` em `req.erro`.

- [ ] **Step 1: Write the failing tests** (adaptam `AS:tests/lancar_saidas_lote_test.py`)

```python
CENTROS = [Centro("ETA II", "90104"), Centro("OFICINA MECÂNICA", "20"),
           Centro("PICKUP 01", "31", "ABC1D23"), Centro("RETRO A", "41", "XYZ9K99"),
           Centro("RETRO B", "42", "XYZ9K99")]

def L(codigo, lote="P-000001", status="PENDENTE", **extra):
    campos = dict(id=next(_ids), lote=lote, status=status, data=date(2026, 10, 9),
                  qtd=Decimal("1"), codigo=codigo, recebedor="JOÃO", centro_custo="ETA II",
                  tipo_saida="BALCÃO", placa="")
    campos.update(extra)
    return LinhaSaida(**campos)

def test_um_lote_vira_uma_requisicao_com_cabecalho_resolvido():
    sel = selecionar([L("001.001.001"), L("001.001.002", qtd=Decimal("1.500"))], CENTROS)
    (req,) = sel.requisicoes
    assert (req.lote, req.data, req.cod_ccusto, req.tipo_saida, req.recebedor, req.erro) == \
        ("P-000001", "09/10/2026", "90104", "BALCÃO", "JOÃO", "")
    assert [(i.cadpro, i.qtd) for i in req.itens] == [("001.001.001", "1"), ("001.001.002", "1,5")]

def test_lotes_diferentes_separam_mesmo_com_codigo_repetido():
    sel = selecionar([L("001.002.004", "P-000005"), L("002.001.003", "P-000005"),
                      L("001.002.004", "AV-000008")], CENTROS)
    assert [r.lote for r in sel.requisicoes] == ["P-000005", "AV-000008"]
    assert all(r.erro == "" for r in sel.requisicoes)

def test_mesmo_lote_com_codigo_repetido_e_recusado():
    (req,) = selecionar([L("001.002.004"), L("001.002.004")], CENTROS).requisicoes
    assert "código 001.002.004 repetido na mesma requisição" in req.erro

@pytest.mark.parametrize("trava", ["VERIFICAR", "EM_LANCAMENTO", "ERRO"])
def test_trava_bloqueia_so_o_proprio_lote(trava):
    sel = selecionar([L("001.001.001", "P-000001", trava), L("001.001.002", "P-000001"),
                      L("001.001.003", "P-000002")], CENTROS)
    assert [r.lote for r in sel.requisicoes] == ["P-000002"]
    assert sel.travados == ["P-000001"]

def test_lancadas_e_nao_lancar_ficam_de_fora_sem_travar():
    sel = selecionar([L("001.001.001", status="LANCADA"), L("001.001.002", status="NAO_LANCAR"),
                      L("001.001.003")], CENTROS)
    assert [len(r.itens) for r in sel.requisicoes] == [1] and sel.travados == []

def test_placa_com_centro_proprio_decide_o_centro():
    (req,) = selecionar([L("001.001.001", placa="ABC1D23", centro_custo="ETA II")], CENTROS).requisicoes
    assert req.cod_ccusto == "31" and req.itens[0].placa == "ABC1D23"

def test_placa_sem_centro_e_centro_vazio_cai_na_oficina():
    (req,) = selecionar([L("001.001.001", placa="ZZZ0Z00", centro_custo="")], CENTROS).requisicoes
    assert req.cod_ccusto == "20"

def test_placa_ambigua_e_centro_inexistente_sao_erros():
    (a,) = selecionar([L("001.001.001", placa="XYZ9K99")], CENTROS).requisicoes
    (b,) = selecionar([L("001.001.001", centro_custo="ETA IX")], CENTROS).requisicoes
    assert "placa 'XYZ9K99' cadastrada em mais de um centro de custo" in a.erro
    assert "centro de custo 'ETA IX' não existe no cadastro de centros de custo" in b.erro

def test_tipo_fora_da_lista_do_scpi_e_erro_e_grafia_vem_da_lista():
    (a,) = selecionar([L("001.001.001", tipo_saida="EMPRESTIMO")], CENTROS).requisicoes
    (b,) = selecionar([L("001.001.001", tipo_saida="balcao")], CENTROS).requisicoes
    assert a.erro.startswith("'Tipo Saída' inválido 'EMPRESTIMO' (aceitos: BALCÃO,")
    assert b.tipo_saida == "BALCÃO"

def test_cabecalho_diferente_no_mesmo_lote_e_erro():
    (req,) = selecionar([L("001.001.001"), L("001.001.002", recebedor="MARIA")], CENTROS).requisicoes
    assert "linhas do lote com data, recebedor, centro de custo, tipo ou placa diferentes" in req.erro

def test_codigo_fora_do_padrao_e_quantidade_zero():
    (req,) = selecionar([L("1.2.3"), L("001.001.002", qtd=Decimal("0"))], CENTROS).requisicoes
    assert "código '1.2.3' fora do padrão 000.000.000" in req.erro
    assert "quantidade de 001.001.002 deve ser > 0" in req.erro

def test_qtd_no_formato_do_scpi():
    assert [qtd_scpi(Decimal(v)) for v in ("10.000", "0.330", "1234.5")] == ["10", "0,33", "1234,5"]
```

(`_ids = itertools.count(1)` no topo do arquivo; sem banco: o módulo não usa
`pytestmark`.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_scpi_requisicoes.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'scpi.requisicoes'`)

- [ ] **Step 3: Implement `scpi/requisicoes.py`**
  - A docstring do módulo diz de onde vem: `selecionar_pendentes`, `validar`, `chave_grupo` e
    as exceções de `ER:lancar_saidas.py`, sobre o banco e agrupados por lote.
  - O centro é resolvido com a primeira linha do lote. As outras precisam ter o mesmo
    cabeçalho `(data, norm_u(recebedor), norm_u(centro_custo), norm_u(tipo_saida),
    norm_placa(placa))`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_scpi_requisicoes.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Seleção e validação das requisições a lançar, agrupadas por lote`

---

### Task 3: Execução do lançamento sobre o banco

**Files:**
- Create: `scpi/lancamento.py`
- Test: `tests/test_lancamento.py`, `tests/scpi_simulado.py` (SCPI simulado, sem pytest,
  reaproveitado na Tarefa 5)

**Interfaces:**
- Consumes:
  - Tarefa 2;
  - `ExecucaoRobo` (Tarefa 1) e `LinhaSaida`;
  - `pedidos.servicos.centros() -> list[Centro]`;
  - `scpi.execucao.trava(nome)` (context manager que entrega se a trava foi obtida).
- Produces:
  - `class SCPI(Protocol)`, com os métodos:
    - `preencher(req: Requisicao) -> None`: levanta `ErroSCPI`;
    - `salvar() -> str`: o nº da requisição; levanta `ResultadoIncerto`;
    - `depois_de_salvar() -> None`;
    - `encerrar_simulacao() -> None`: pausa para a conferência visual e descarta o
      formulário;
    - `descartar(lote: str) -> None`: print da tela e volta ao estado limpo, depois de
      `ErroSCPI`;
    - `reiniciar() -> None`.
  - `AbrirSCPI = Callable[[], AbstractContextManager[SCPI]]`.
  - `@dataclass Resumo(requisicoes=0, processadas=0, lancadas=0, simuladas=0, falhas=0,
    verificar=0, ignoradas=0)`: todas as contagens são em lotes.
  - `class LancamentoEmAndamento(Exception)`.
  - `executar_lancamento(execucao: ExecucaoRobo, abrir_scpi: AbrirSCPI, *,
    limite: int | None = None) -> ExecucaoRobo`. Faz, nesta ordem:
    1. tenta a trava `almoxarifado:lancar_saidas`. Ocupada: a execução vai a `FALHA` com
       `erro="Outro lançamento já está em andamento."` e `fim`, e levanta
       `LancamentoEmAndamento`;
    2. instala o `RegistroNaExecucao` no logger `scpi.lancamento` e chama `lancar`;
    3. ao terminar, grava `situacao` (`SUCESSO` sem falhas nem verificar, `ATENCAO` com
       alguma), `resumo=asdict(resumo)` e `fim`;
    4. `FalhaCritica` ou qualquer exceção: `FALHA`, `erro=str(exc)` (inesperada:
       `"Falha inesperada: <exc>"`) e `fim`, e relança.
  - `lancar(execucao, abrir_scpi, *, limite=None) -> Resumo`: o algoritmo abaixo.
  - `RegistroNaExecucao(execucao)`: `logging.Handler` que acrescenta
    `"HH:MM:SS mensagem\n"` ao `log` da execução com
    `update(log=Concat("log", Value(...)))`.
  - `logger = logging.getLogger("scpi.lancamento")`, também usado pela Tarefa 4.
  - `JOURNAL = "lancar_saidas_journal.jsonl"`, em `settings.LOG_DIR` (lido na hora). Cada
    linha é o JSON
    `{"ts", "evento", "execucao", "lote", "linhas": [ids], **extra}`, com `ensure_ascii=False`.

Algoritmo de `lancar` (a ordem das gravações é o que garante "nunca lançar duas vezes"):

```
modo = simulação se execucao.simulacao
linhas = LinhaSaida com status em (PENDENTE, *ESTADOS_TRAVA), order_by("id")
sel = selecionar(linhas, centros())
para cada lote travado: log "⚠ lote X travado — conferir no SCPI"; ignoradas += 1
para cada req com erro: log "✘ req — validação: erro"; falhas += 1;
    se não simulação: _gravar(req, ERRO, mensagem=erro[:500], critico=False)
validas = [r sem erro]; com limite: ignoradas += excedentes; validas = validas[:limite]
resumo.requisicoes = len(validas); grava o resumo na execução a cada lote processado
se não houver validas: log "Nada a lançar."; devolve (o navegador nem abre)
with abrir_scpi() as scpi:
  para cada req:
    log "→ (i/n) req"
    try: scpi.preencher(req)
    except Exception (ErroSCPI ou outra): falhas += 1; log; se não simulação: ERRO (não crítico);
        scpi.descartar(req.lote); continue
    se simulação: scpi.encerrar_simulacao(); simuladas += 1; continue
    se não _travar(req): log "lote mudou durante a execução; não lançado"; ignoradas += 1;
        scpi.descartar(req.lote); continue
    journal("em_lancamento")
    try: numero = scpi.salvar()
    except Exception: verificar += 1; journal("incerto", erro=...);
        _gravar(req, VERIFICAR, mensagem="Resultado incerto: <exc>"[:500], critico=True);
        scpi.reiniciar(); continue
    journal("lancada", requisicao=numero)
    _gravar(req, LANCADA, requisicao_scpi=numero, lancado_em=now, mensagem="", critico=True)
    lancadas += 1; log "✔ lançada no SCPI: requisição <numero>"
    try: scpi.depois_de_salvar()
    except Exception: log aviso; scpi.reiniciar()
```

- `_travar(req, execucao) -> bool`: dentro de `transaction.atomic()`, faz
  `select_for_update()` das linhas `req.ids`.
  - Se alguma não está `PENDENTE`, devolve `False` sem mudar nada.
  - Senão grava `EM_LANCAMENTO` com
    `mensagem="Em lançamento desde dd/mm/aaaa HH:MM (execução #id)."`.
  - Falha de banco aqui vira `FalhaCritica`.
- `_gravar(req, status, *, critico, **campos)`:
  - faz `LinhaSaida.objects.filter(pk__in=req.ids).update(status=..., **campos)`;
  - exceção: `journal("falha_banco", valores=..., erro=repr(exc))`;
  - com `critico`, levanta `FalhaCritica("não foi possível gravar <status> para <req>: <exc>.
    Registro salvo em lancar_saidas_journal.jsonl — confira no SCPI e resolva o lote à
    mão.")`;
  - sem `critico`, só registra no log.

- [ ] **Step 1: Write the SCPI simulado and the failing tests**

`tests/scpi_simulado.py`: classe `SCPISimulado`, com:
- `falhas_preencher: dict[str, Exception]` e `falhas_salvar: dict[str, Exception]`, por lote;
- `ao_salvar: Callable | None`, chamado dentro de `salvar` antes de devolver;
- `chamadas: list[tuple[str, str]]`, com `("preencher", lote)`, `("salvar", lote)`,
  `("descartar", lote)`, `("simulacao", lote)`, `("reiniciar", "")` e
  `("depois_de_salvar", lote)`;
- `abertas: int`;
- `abrir()`: `@contextmanager` que soma `abertas` e entrega `self`.

`salvar` devolve `"000001/26"`, `"000002/26"`… em sequência.

Em `tests/test_lancamento.py` (`pytestmark = pytest.mark.django_db`; fixture `cenario` com
`montar_cenario()`; dois lotes criados com `confirmar_atendimento`/`registrar_saida_avulsa`
pelos ajudantes de `tests/cenario.py`: `P-` com 2 linhas e `AV-` com 1; fixture `journal` que
aponta `settings.LOG_DIR` para `tmp_path`):

```python
def test_lanca_um_lote_por_requisicao_e_grava_o_numero(dois_lotes, scpi):
    execucao = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert execucao.situacao == "SUCESSO" and execucao.fim is not None
    assert execucao.resumo == {"requisicoes": 2, "processadas": 2, "lancadas": 2, "simuladas": 0,
                               "falhas": 0, "verificar": 0, "ignoradas": 0}
    p, av = dois_lotes
    assert set(LinhaSaida.objects.filter(lote=p).values_list("status", "requisicao_scpi")) == {("LANCADA", "000001/26")}
    assert LinhaSaida.objects.get(lote=av).requisicao_scpi == "000002/26"
    assert not LinhaSaida.objects.filter(lancado_em__isnull=True).exists()
    assert "lançada no SCPI: requisição 000001/26" in execucao.log

@pytest.mark.django_db(transaction=True)
def test_trava_esta_confirmada_no_banco_antes_do_salvar(dois_lotes, scpi):
    vistos = []
    def olhar():
        outra = connections.create_connection("default")
        with outra.cursor() as c:
            c.execute("SELECT DISTINCT status FROM pedidos_linhasaida WHERE lote=%s", [dois_lotes[0]])
            vistos.append([r[0] for r in c.fetchall()])
        outra.close()
    scpi.ao_salvar = olhar
    executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir, limite=1)
    assert vistos == [["EM_LANCAMENTO"]]

def test_erro_antes_do_salvar_vira_erro_e_o_proximo_segue(dois_lotes, scpi):
    p, av = dois_lotes
    scpi.falhas_preencher[p] = ErroSCPI("item 1/2 (023.001.002): saldo insuficiente")
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert e.situacao == "ATENCAO" and e.resumo["falhas"] == 1 and e.resumo["lancadas"] == 1
    assert set(LinhaSaida.objects.filter(lote=p).values_list("status", "mensagem")) == \
        {("ERRO", "item 1/2 (023.001.002): saldo insuficiente")}
    assert ("descartar", p) in scpi.chamadas and ("salvar", p) not in scpi.chamadas

def test_qualquer_falha_no_salvar_vira_verificar_nunca_pendente(dois_lotes, scpi):
    p, _ = dois_lotes
    scpi.falhas_salvar[p] = RuntimeError("Timeout 10000ms exceeded")
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert set(LinhaSaida.objects.filter(lote=p).values_list("status", flat=True)) == {"VERIFICAR"}
    assert "Timeout 10000ms exceeded" in LinhaSaida.objects.filter(lote=p).first().mensagem
    assert e.resumo["verificar"] == 1 and ("reiniciar", "") in scpi.chamadas

def test_lote_travado_ou_com_erro_nao_vai_ao_scpi(dois_lotes, scpi):
    p, av = dois_lotes
    LinhaSaida.objects.filter(lote=p).filter(seq=1).update(status="VERIFICAR")
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert ("preencher", p) not in scpi.chamadas and ("preencher", av) in scpi.chamadas
    assert LinhaSaida.objects.get(lote=p, seq=2).status == "PENDENTE"
    assert e.resumo["ignoradas"] == 1 and "P-" in e.log and "travado" in e.log

def test_simulacao_nao_salva_nem_muda_status(dois_lotes, scpi):
    e = executar_lancamento(ExecucaoRobo.objects.create(simulacao=True), scpi.abrir)
    assert not any(c[0] == "salvar" for c in scpi.chamadas)
    assert [c for c in scpi.chamadas if c[0] == "simulacao"] == [("simulacao", lote) for lote in dois_lotes]
    assert set(LinhaSaida.objects.values_list("status", flat=True)) == {"PENDENTE"}
    assert e.resumo["simuladas"] == 2 and e.situacao == "SUCESSO"

def test_invalido_vira_erro_sem_abrir_o_navegador(dois_lotes, scpi):
    CentroCusto.objects.filter(descricao="ETA II").delete()
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert scpi.abertas == 0 and e.resumo["falhas"] == 2
    assert all("centro de custo 'ETA II' não existe" in m
               for m in LinhaSaida.objects.values_list("mensagem", flat=True))

def test_linha_alterada_durante_a_execucao_nao_e_lancada(dois_lotes, scpi):
    p, _ = dois_lotes
    original = scpi.preencher
    def mudar(req):
        original(req)
        if req.lote == p:
            LinhaSaida.objects.filter(lote=p, seq=2).update(status="NAO_LANCAR")
    scpi.preencher = mudar
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir)
    assert ("salvar", p) not in scpi.chamadas and ("descartar", p) in scpi.chamadas
    assert list(LinhaSaida.objects.filter(lote=p).order_by("seq").values_list("status", flat=True)) == ["PENDENTE", "NAO_LANCAR"]
    assert e.resumo["ignoradas"] == 1

def test_limite_processa_so_os_primeiros(dois_lotes, scpi):
    e = executar_lancamento(ExecucaoRobo.objects.create(), scpi.abrir, limite=1)
    assert e.resumo["lancadas"] == 1 and e.resumo["ignoradas"] == 1

def test_banco_fora_ao_gravar_lancada_interrompe_e_guarda_no_journal(dois_lotes, scpi, journal, monkeypatch):
    p, _ = dois_lotes
    original = lancamento._gravar
    def quebrar(req, status, **kw):
        if status == "LANCADA":
            raise DatabaseError("MySQL server has gone away")
        return original(req, status, **kw)
    monkeypatch.setattr(lancamento, "_gravar", quebrar)
    execucao = ExecucaoRobo.objects.create()
    with pytest.raises(FalhaCritica):
        executar_lancamento(execucao, scpi.abrir)
    execucao.refresh_from_db()
    assert execucao.situacao == "FALHA" and "gone away" in execucao.erro
    assert set(LinhaSaida.objects.filter(lote=p).values_list("status", flat=True)) == {"EM_LANCAMENTO"}
    eventos = [json.loads(linha) for linha in (journal / "lancar_saidas_journal.jsonl").read_text("utf-8").splitlines()]
    assert {"evento": "lancada", "lote": p, "requisicao": "000001/26"}.items() <= eventos[-1].items()

def test_navegador_que_nao_abre_deixa_tudo_pendente(dois_lotes):
    @contextmanager
    def quebrado():
        raise ErroImportacao("Defina SAEP_USER e SAEP_PASS no .env.")
        yield
    e = ExecucaoRobo.objects.create()
    with pytest.raises(ErroImportacao):
        executar_lancamento(e, quebrado)
    e.refresh_from_db()
    assert e.situacao == "FALHA" and "SAEP_USER" in e.erro
    assert set(LinhaSaida.objects.values_list("status", flat=True)) == {"PENDENTE"}

def test_trava_ocupada_recusa_sem_tocar_em_nada(dois_lotes, scpi):
    outra = connections.create_connection("default")
    with outra.cursor() as c:
        c.execute("SELECT GET_LOCK('almoxarifado:lancar_saidas', 0)")
    try:
        e = ExecucaoRobo.objects.create()
        with pytest.raises(LancamentoEmAndamento):
            executar_lancamento(e, scpi.abrir)
        e.refresh_from_db()
        assert (e.situacao, e.erro) == ("FALHA", "Outro lançamento já está em andamento.")
        assert scpi.abertas == 0
    finally:
        outra.close()
```

Nestes testes, `_gravar` precisa ser chamada pelo nome do módulo (`lancamento._gravar`) para
o `monkeypatch` valer.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_lancamento.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'scpi.lancamento'`)

- [ ] **Step 3: Implement `scpi/lancamento.py`** conforme as interfaces e o algoritmo acima.
  - O `RegistroNaExecucao` sai do logger no `finally` de `executar_lancamento`.
  - `resumo.processadas` soma 1 a cada lote do laço, qualquer que seja o resultado.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_lancamento.py tests/test_scpi_execucao.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Lançamento sobre o banco: trava antes do Salvar, resultado por lote e journal`

---

### Task 4: Navegação no SCPI (Playwright)

**Files:**
- Create: `scpi/lancador.py`
- Test: `tests/test_scpi_lancador.py`

**Interfaces:**
- Consumes:
  - `scpi.browser.abrir_sessao(playwright, perfil)` e `frame_compras(page)`;
  - Tarefa 2 (exceções, `Requisicao`, `Item`, `RE_CADPRO`, `RE_REQUI`);
  - `pedidos.regras.norm_u` / `norm_placa`;
  - o `logger` de `scpi.lancamento`.
- Produces:
  - `class NavegadorSCPI` (implementa `scpi.lancamento.SCPI`);
  - `navegador() -> Iterator[NavegadorSCPI]`: `@contextmanager` que abre o
    `sync_playwright` (import dentro da função, como `relatorios.py`), abre a sessão, entrega
    e fecha no `finally`.

- [ ] **Step 1: Write the failing test**

```python
def test_navegador_implementa_o_protocolo_do_lancamento():
    from scpi.lancador import NavegadorSCPI
    from scpi.lancamento import SCPI
    metodos = {n for n in vars(SCPI) if not n.startswith("_")}
    assert metodos <= set(dir(NavegadorSCPI))

def test_lancador_nao_importa_playwright_no_topo():
    import scpi.lancador
    assert "sync_playwright" not in vars(scpi.lancador)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_scpi_lancador.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'scpi.lancador'`)

- [ ] **Step 3: Copy the navigation** de `ER:lancar_saidas.py`, linhas 489–1002 (de
  `JS_INPUT_POR_ROTULO` até a classe `Sessao`), mais `TIMEOUT`, `PAUSA_DRY_RUN_MS`,
  `resumo_erro` e `parse_decimal_br`. A docstring cita origem e commit, como `relatorios.py`.
  Só estas mudanças:
  - `log` = `logging.getLogger("scpi.lancamento").info`; `norm` e `norm_placa` vêm de
    `pedidos.regras` (`norm_u`, `norm_placa`); as exceções e `RE_*` vêm de `scpi.requisicoes`;
  - `req.linhas[0].recebimento` → `req.recebedor` (`preencher_cabecalho` e
    `conferir_cabecalho`);
  - `Sessao.abrir` usa `abrir_sessao(self.playwright, settings.SCPI_PERFIL_DIR /
    "lancamento")`;
  - o `processar` do original vira os métodos de `NavegadorSCPI`, que estende `Sessao`:
    - `preencher(req)`: `abrir_formulario` → `preencher_cabecalho` → `adicionar_itens` →
      `conferir_cabecalho` → `self._salvar = localizar_salvar(frame)`. Exceção que não seja
      `ErroSCPI` vira `ErroSCPI(resumo_erro(e))`;
    - `salvar()`: `salvar_requisicao(self.frame, self._salvar)`. Exceção que não seja
      `ResultadoIncerto` vira `ResultadoIncerto(resumo_erro(e))`;
    - `depois_de_salvar()`: `fechar_janelas_pos_salvar` (exceção só vai para o log, como no
      original) e depois `reabrir_modulo()`;
    - `encerrar_simulacao()`: o log `[DRY-RUN] …` do original, a pausa de
      `PAUSA_DRY_RUN_MS` e `self.limpar()`;
    - `descartar(lote)`: print da tela em
      `settings.LOG_DIR / f"scpi-lancamento-{lote}-{momento:%Y%m%d_%H%M%S}.png"` (falha do
      print é ignorada, com o caminho no log) e depois `self.limpar()`.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_scpi_lancador.py -q && uv run ruff check scpi/lancador.py`
Expected: PASS e nenhum aviso. Ajuste só o estilo que o ruff pedir (por exemplo, `l` → `linha`
e lambda atribuída → `def`), nunca seletores nem esperas.

- [ ] **Step 5: Commit** — `Navegação do lançamento no SCPI copiada do extrair-relatorio`

---

### Task 5: Comando `lancar_saidas` e disparo pelo botão

**Files:**
- Create: `scpi/management/commands/lancar_saidas.py`
- Modify: `scpi/disparo.py`
- Test: `tests/test_lancar_saidas.py`

**Interfaces:**
- Consumes:
  - `executar_lancamento`, `LancamentoEmAndamento` e `FalhaCritica` (Tarefas 2 e 3);
  - `scpi.lancador.navegador` (Tarefa 4);
  - `ExecucaoRobo` (Tarefa 1).
- Produces:
  - `manage.py lancar_saidas [--execucao ID] [--dry-run] [--limite N]`:
    - com `--execucao`, usa o registro: inexistente ou fora de `ANDAMENTO` →
      `CommandError("Execução <id> não encontrada ou já encerrada.")`;
    - sem `--execucao`, cria um registro com `iniciada_por=None`;
    - `simulacao = execucao.simulacao or dry_run`, gravado no registro antes de começar;
    - `navegador` é importado no topo do módulo do comando, para o teste trocar;
    - saídas:
      - `LancamentoEmAndamento` → `CommandError("Outro lançamento já está em andamento.")`;
      - `FalhaCritica` → `CommandError(str(exc), returncode=2)`;
      - situação `ATENCAO` → `CommandError("Lançamento terminou com erros ou linhas a
        verificar.")`;
      - sucesso → escreve no stdout `"Lançadas: N · simuladas: N · falhas: N · verificar: N ·
        ignoradas: N"`.
  - `scpi.disparo.iniciar_lancamento(usuario, *, simulacao: bool) -> ExecucaoRobo | None`:
    - devolve `None` se `ExecucaoRobo.em_andamento().exists()`;
    - senão cria a execução e inicia
      `[python, manage.py, "lancar_saidas", "--execucao", str(id)]`, mais `"--dry-run"` na
      simulação;
    - a saída do processo vai para `LOG_DIR/lancar_saidas.log`, com o cabeçalho
      `=== dd/mm/aaaa HH:MM:SS Lançar no SCPI ===` (`Simular no SCPI` na simulação).
  - `iniciar_atualizacao` e `iniciar_lancamento` passam a usar
    `_iniciar_comando(argumentos: list[str], arquivo_log: str, titulo: str) -> None`, com o
    `Popen` de hoje (flags do Windows, `PYTHONIOENCODING`, `DEVNULL`).

- [ ] **Step 1: Write the failing tests**

```python
def test_comando_usa_a_execucao_do_botao(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    e = ExecucaoRobo.objects.create()
    call_command("lancar_saidas", "--execucao", str(e.pk))
    e.refresh_from_db()
    assert e.situacao == "SUCESSO" and e.resumo["lancadas"] == 2

def test_dry_run_vence_uma_execucao_real(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    e = ExecucaoRobo.objects.create(simulacao=False)
    call_command("lancar_saidas", "--execucao", str(e.pk), "--dry-run")
    e.refresh_from_db()
    assert e.simulacao and not any(c[0] == "salvar" for c in scpi.chamadas)

def test_sem_execucao_cria_registro_de_linha_de_comando(monkeypatch, dois_lotes):
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", SCPISimulado().abrir)
    call_command("lancar_saidas", "--limite", "1")
    e = ExecucaoRobo.objects.get()
    assert e.iniciada_por is None and e.resumo["lancadas"] == 1

def test_execucao_encerrada_e_recusada():
    e = ExecucaoRobo.objects.create(situacao="SUCESSO")
    with pytest.raises(CommandError, match="não encontrada ou já encerrada"):
        call_command("lancar_saidas", "--execucao", str(e.pk))

def test_falhas_viram_codigo_de_saida(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    scpi.falhas_preencher[dois_lotes[0]] = ErroSCPI("x")
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    with pytest.raises(CommandError, match="erros ou linhas a verificar"):
        call_command("lancar_saidas")

def test_disparo_cria_execucao_e_inicia_processo(monkeypatch, usuario):
    chamadas = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: chamadas.append(args))
    e = iniciar_lancamento(usuario, simulacao=True)
    assert e.iniciada_por == usuario and e.simulacao and e.situacao == "ANDAMENTO"
    assert chamadas[0][1:] == [str(settings.BASE_DIR / "manage.py"), "lancar_saidas",
                               "--execucao", str(e.pk), "--dry-run"]

def test_disparo_recusa_com_execucao_em_andamento_mas_nao_interrompida(monkeypatch, usuario):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    ExecucaoRobo.objects.create()
    assert iniciar_lancamento(usuario, simulacao=False) is None
    ExecucaoRobo.objects.update(inicio=timezone.now() - timedelta(hours=2))
    assert iniciar_lancamento(usuario, simulacao=False) is not None
```

(`dois_lotes`: a mesma fixture da Tarefa 3. Passe-a para um `tests/conftest.py`, ou
ponha-a num ajudante de `tests/cenario.py` com uma fixture fina em cada arquivo. `usuario`,
aqui e na Tarefa 6: `get_user_model().objects.create_user("00012", password="x")`.)
`tests/test_atualizar_catalogo.py::test_disparo_inicia_processo_separado` precisa continuar
verde sem mudança.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_lancar_saidas.py -q`
Expected: FAIL (`Unknown command: 'lancar_saidas'` / `ImportError: iniciar_lancamento`)

- [ ] **Step 3: Implement** o comando e o disparo conforme as interfaces.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_lancar_saidas.py tests/test_atualizar_catalogo.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Comando lancar_saidas e disparo em processo separado`

---

### Task 6: Resolver travas

**Files:**
- Modify: `pedidos/regras.py`, `pedidos/servicos.py`
- Test: `tests/test_resolver_travas.py`

**Interfaces:**
- Consumes: `LinhaSaida`, `ExecucaoRobo.em_andamento()`, `Resposta` (já em `servicos.py`).
- Produces:
  - `regras.requisicao_valida(valor: object) -> bool`: `texto(valor)` casa com
    `^\d{6}/\d{2}$`.
  - `servicos.resolver_lote(lote: str, acao: str, *, usuario, requisicao: str = "",
    conferido: bool = False, agora: datetime | None = None) -> Resposta`. Faz, em ordem:
    1. ação fora de `("lancada", "liberar", "nao_lancar")` → `"Ação desconhecida."`;
    2. execução em andamento → `"Há um lançamento no SCPI em andamento. Aguarde terminar para
       resolver as travas."`;
    3. numa transação, `select_for_update` das linhas do lote em `ESTADOS_TRAVA` (as três
       constantes de `regras`). Nenhuma → `"Nenhuma linha do lote <lote> aguarda
       conferência."`;
    4. `lancada` sem `requisicao_valida` → `"Informe o número da requisição no formato
       000000/00."`;
    5. `liberar` com alguma linha `VERIFICAR`/`EM_LANCAMENTO` e sem `conferido` → `"Antes de
       liberar, confira no SCPI que a requisição não foi gravada e marque a confirmação."`;
    6. grava só nessas linhas:
       - `lancada`: `status=LANCADA`, `requisicao_scpi`, `lancado_em=agora`;
       - `liberar`: `PENDENTE`;
       - `nao_lancar`: `NAO_LANCAR`.
       A `mensagem` de cada linha vira `"<Requisição 003354/26 informada | Liberada para
       relançar | Marcada para não lançar> por <username> em dd/mm/aaaa HH:MM. Antes: <rótulo
       do status> — <mensagem anterior>"`. Sem mensagem anterior, termina em `"Antes: <rótulo
       do status>."`.
    7. `Resposta(ok=True, mensagem=...)`:
       - `"Lote <lote>: requisição <n> registrada."`;
       - `"Lote <lote> liberado para o próximo lançamento."`;
       - `"Lote <lote> marcado para não lançar no SCPI."`.
    Erro sai em `Resposta(ok=False, mensagem=...)`.

- [ ] **Step 1: Write the failing tests**

```python
def lote(*status):
    p = criar_pedido(atendido=True, linhas=[(s, "") for s in status])
    return p.numero

def test_informar_requisicao_lanca_so_as_travadas(usuario):
    n = lote("VERIFICAR", "LANCADA", "PENDENTE")
    r = resolver_lote(n, "lancada", usuario=usuario, requisicao=" 003354/26 ")
    assert r.ok and r.mensagem == f"Lote {n}: requisição 003354/26 registrada."
    assert list(LinhaSaida.objects.filter(lote=n).order_by("seq").values_list("status", "requisicao_scpi")) == \
        [("LANCADA", "003354/26"), ("LANCADA", ""), ("PENDENTE", "")]
    msg = LinhaSaida.objects.get(lote=n, seq=1).mensagem
    assert msg.startswith(f"Requisição 003354/26 informada por {usuario.username} em ") and "Antes: Verificar no SCPI" in msg

@pytest.mark.parametrize("numero", ["", "3354/26", "003354-26", "0033540/26"])
def test_numero_fora_do_formato_e_recusado(usuario, numero):
    n = lote("VERIFICAR")
    r = resolver_lote(n, "lancada", usuario=usuario, requisicao=numero)
    assert not r.ok and r.mensagem == "Informe o número da requisição no formato 000000/00."
    assert LinhaSaida.objects.get(lote=n).status == "VERIFICAR"

def test_liberar_verificar_exige_conferencia(usuario):
    n = lote("VERIFICAR")
    assert not resolver_lote(n, "liberar", usuario=usuario).ok
    assert resolver_lote(n, "liberar", usuario=usuario, conferido=True).ok
    assert LinhaSaida.objects.get(lote=n).status == "PENDENTE"

def test_liberar_erro_nao_exige_conferencia(usuario):
    n = lote("ERRO")
    assert resolver_lote(n, "liberar", usuario=usuario).ok

def test_em_lancamento_orfa_pode_ser_marcada_nao_lancar(usuario):
    n = lote("EM_LANCAMENTO")
    r = resolver_lote(n, "nao_lancar", usuario=usuario)
    assert r.ok and LinhaSaida.objects.get(lote=n).status == "NAO_LANCAR"

def test_lote_sem_trava_ou_inexistente(usuario):
    assert resolver_lote(lote("PENDENTE"), "liberar", usuario=usuario).mensagem.endswith("aguarda conferência.")
    assert not resolver_lote("P-999999", "liberar", usuario=usuario).ok

def test_acao_desconhecida(usuario):
    assert resolver_lote(lote("ERRO"), "apagar", usuario=usuario).mensagem == "Ação desconhecida."

def test_recusa_durante_execucao_e_libera_quando_interrompida(usuario):
    n = lote("VERIFICAR")
    e = ExecucaoRobo.objects.create()
    assert "em andamento" in resolver_lote(n, "nao_lancar", usuario=usuario).mensagem
    ExecucaoRobo.objects.filter(pk=e.pk).update(inicio=timezone.now() - timedelta(hours=2))
    assert resolver_lote(n, "nao_lancar", usuario=usuario).ok

def test_requisicao_valida():
    assert requisicao_valida("003354/26") and not requisicao_valida("003354/2026")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_resolver_travas.py -q`
Expected: FAIL (`ImportError: cannot import name 'resolver_lote'`)

- [ ] **Step 3: Implement** `requisicao_valida` e `resolver_lote`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_resolver_travas.py tests/test_regras_saidas.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Resolução das travas do robô por lote`

---

### Task 7: Página "Lançamentos SCPI", cartão no painel e menu

**Files:**
- Create: `pedidos/views/lancamentos.py`, `pedidos/templates/pedidos/lancamentos.html`,
  `pedidos/templates/pedidos/_lancamentos.html`
- Modify:
  - `pedidos/consultas.py`, `pedidos/urls.py`, `pedidos/views/almoxarifado.py` (painel);
  - `pedidos/templates/pedidos/painel.html`, `pedidos/templates/pedidos/detalhe.html`;
  - `pedidos/static/pedidos/css/pedidos.css`;
  - `interface/navegacao.py`, `interface/templates/interface/_icone.html`;
  - `tests/test_acesso.py` (ordem do menu).
- Test: `tests/test_pagina_lancamentos.py`

**Interfaces:**
- Consumes: `iniciar_lancamento` (Tarefa 5), `resolver_lote` (Tarefa 6), `ExecucaoRobo`.
- Produces:
  - Em `pedidos/consultas.py`:
    - `lotes_pendentes() -> int`: número de lotes distintos com linha `PENDENTE`;
    - `@dataclass LoteTravado(lote: str, linhas: list[LinhaSaida], conferir: bool)`:
      `conferir` = alguma linha `VERIFICAR`/`EM_LANCAMENTO`;
    - `lotes_travados() -> list[LoteTravado]`: linhas em `VERIFICAR`, `EM_LANCAMENTO` ou
      `ERRO`, agrupadas por lote, na ordem do `id` da primeira linha.
  - Rotas:
    - `pedidos:lancamentos`: `almoxarifado/lancamentos/`;
    - `pedidos:lancar`: `almoxarifado/lancamentos/iniciar/`, POST, campo `simulacao=1`
      opcional;
    - `pedidos:resolver`: `almoxarifado/lancamentos/<str:lote>/resolver/`, POST com `acao`,
      `requisicao` e `conferido`.
    Todas com `login_required`.
  - Menu: `ItemMenu("Lançamentos SCPI", "pedidos:lancamentos", "robo")`, entre "Catálogo" e
    "Cadastros". O ícone `robo` é o Lucide `bot`:
    `<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2
    14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>`.

Conteúdo:
- **View `lancamentos`.** Contexto:
  - `execucao`: a mais recente, ou `None`;
  - `em_andamento`;
  - `acompanhar` = em andamento ou terminou há menos de 30 s;
  - `log_recente`: as últimas 40 linhas do `log`;
  - `pendentes`, `travados` e `execucoes` (as 10 últimas).
  Com `HX-Request` (e sem `HX-History-Restore-Request`) devolve só `_lancamentos.html`,
  como o catálogo.
- **`_lancamentos.html`** fica numa `<section id="lancamentos">`, com
  `hx-get … hx-trigger="every 3s" hx-swap="outerHTML"` só quando `acompanhar`. Dentro:
  - os formulários "Lançar no SCPI" (primário) e "Simular" (secundário, com
    `simulacao=1`), desabilitados durante a execução, e a frase `"N lote(s) aguardando o
    robô."`;
  - o cartão "Andamento" da última execução:
    - selo com o texto da situação ("Interrompida" quando `interrompida`) e o modo
      (Simulação/Lançamento real);
    - quem iniciou ("linha de comando" sem usuário), início e fim;
    - "Lote X de Y" (`processadas`/`requisicoes`) e as contagens;
    - `erro`, se houver;
    - `log_recente` num `<pre class="log-execucao mono">`;
  - o cartão "Travas para conferir". Cada lote mostra:
    - Nº (`.mono`, link para o detalhe), data, recebedor, centro de custo;
    - os materiais (código `.mono` e quantidade);
    - o selo do status com texto e a `mensagem`;
    - o formulário de resolução (POST para `pedidos:resolver`): campo "Nº da requisição"
      (`.mono`), botão "Informar requisição", checkbox "Conferi no SCPI: a requisição não
      foi gravada" (só quando `conferir`) e os botões "Liberar para relançar" e "Não lançar"
      (`name="acao"` com os três valores).
    - Durante a execução, os formulários dão lugar a "A resolução fica disponível quando o
      lançamento terminar.".
    - Sem travas: estado vazio "Nenhuma trava para conferir.".
  - o cartão "Últimas execuções": tabela com início, modo, quem, situação, lançadas, falhas,
    verificar.
- **View `lancar`.**
  - `None` → `messages.warning("Já há um lançamento em andamento. Aguarde terminar.")`;
  - real → `messages.success("Lançamento iniciado. Acompanhe o andamento abaixo.")`;
  - simulação → `messages.success("Simulação iniciada: o robô preenche cada requisição no
    SCPI e não salva.")`.
  Redireciona para `pedidos:lancamentos`.
- **View `resolver`.** `messages.success` ou `messages.error` com `Resposta.mensagem` e
  redireciona para `pedidos:lancamentos`.
- **Painel.** Novo cartão "Lançamentos no SCPI" depois do de saúde:
  - `"N lote(s) aguardando o robô · M lote(s) para conferir"`;
  - o formulário "Lançar no SCPI" (desabilitado durante a execução);
  - o link "Ver lançamentos".
  - Contexto: `lancamento_pendentes`, `lancamento_travados` e `lancamento_em_andamento`, só
    na página inteira.
- **Detalhe.** Quando `pedido.situacao_scpi.chave == "atencao"`, um link "Resolver em
  Lançamentos SCPI" no quadro do SCPI. Fica em `detalhe.html`, fora de `_recibo.html`, e
  com `nao-imprimir`.
- **CSS.** `.log-execucao` (fonte mono pequena, `max-height: 20rem`, `overflow: auto`,
  `white-space: pre-wrap`) e o que faltar para o formulário de resolução, sempre com os
  tokens de `clean.css` e as classes de `docs/DESIGN.md`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pagina_exige_login(client):
    r = client.get(reverse("pedidos:lancamentos"))
    assert r.status_code == 302 and "entrar" in r.url

def test_pagina_mostra_pendentes_travas_e_formulario(client, usuario_logado):
    criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    p = criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    LinhaSaida.objects.filter(lote=p.numero).update(mensagem="Resultado incerto: Timeout")
    texto = client.get(reverse("pedidos:lancamentos")).text
    assert "1 lote(s) aguardando o robô." in texto
    assert p.numero in texto and "Resultado incerto: Timeout" in texto
    assert "Conferi no SCPI: a requisição não foi gravada" in texto
    assert reverse("pedidos:resolver", args=[p.numero]) in texto
    assert "every 3s" not in texto

def test_em_andamento_desabilita_botoes_esconde_resolucao_e_acompanha(client, usuario_logado):
    criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    ExecucaoRobo.objects.create(log="10:00:01 → (1/2) P-000001\n")
    texto = client.get(reverse("pedidos:lancamentos")).text
    assert 'hx-trigger="every 3s"' in texto and "→ (1/2) P-000001" in texto
    assert "A resolução fica disponível quando o lançamento terminar." in texto
    assert re.search(r'<button[^>]*disabled[^>]*>\s*(<svg.*?</svg>)?\s*Lançar no SCPI', texto, re.S)

def test_htmx_recebe_so_o_trecho(client, usuario_logado):
    r = client.get(reverse("pedidos:lancamentos"), headers={"HX-Request": "true"})
    assert r.text.lstrip().startswith("<section") and "app-menu" not in r.text

def test_lancar_inicia_e_avisa(client, usuario_logado, monkeypatch):
    chamadas = []
    monkeypatch.setattr("pedidos.views.lancamentos.iniciar_lancamento",
                        lambda u, simulacao: chamadas.append((u, simulacao)) or object())
    r = client.post(reverse("pedidos:lancar"), {"simulacao": "1"}, follow=True)
    assert chamadas == [(usuario_logado, True)]
    assert "Simulação iniciada" in r.text

def test_lancar_recusa_em_andamento(client, usuario_logado, monkeypatch):
    monkeypatch.setattr("pedidos.views.lancamentos.iniciar_lancamento", lambda u, simulacao: None)
    r = client.post(reverse("pedidos:lancar"), follow=True)
    assert "Já há um lançamento em andamento" in r.text

def test_lancar_e_resolver_so_por_post(client, usuario_logado):
    assert client.get(reverse("pedidos:lancar")).status_code == 405
    assert client.get(reverse("pedidos:resolver", args=["P-000001"])).status_code == 405

def test_resolver_mostra_o_resultado(client, usuario_logado):
    p = criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    url = reverse("pedidos:resolver", args=[p.numero])
    r = client.post(url, {"acao": "lancada", "requisicao": "3354/26"}, follow=True)
    assert "Informe o número da requisição no formato 000000/00." in r.text
    r = client.post(url, {"acao": "lancada", "requisicao": "003354/26"}, follow=True)
    assert f"Lote {p.numero}: requisição 003354/26 registrada." in r.text

def test_painel_mostra_cartao_de_lancamentos(client, usuario_logado):
    criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    criar_pedido(atendido=True, linhas=[("ERRO", "")])
    texto = client.get(reverse("pedidos:painel")).text
    assert "1 lote(s) aguardando o robô · 1 lote(s) para conferir" in texto
    assert reverse("pedidos:lancar") in texto and reverse("pedidos:lancamentos") in texto

def test_detalhe_com_trava_aponta_para_a_resolucao(client, usuario_logado):
    p = criar_pedido(atendido=True, linhas=[("ERRO", "")])
    assert "Resolver em Lançamentos SCPI" in client.get(reverse("pedidos:detalhe", args=[p.numero])).text

def test_menu_tem_lancamentos_entre_catalogo_e_cadastros(admin_client):
    texto = admin_client.get(reverse("pedidos:lancamentos")).text
    assert item_atual(texto, reverse("pedidos:lancamentos"), "Lançamentos SCPI")
    assert texto.index("<span>Catálogo</span>") < texto.index("<span>Lançamentos SCPI</span>") < texto.index("<span>Cadastros</span>")
```

Também em `tests/test_acesso.py::test_menu_na_ordem_da_spec`, os rótulos passam a
`("Painel", "Saída avulsa", "Recibos", "Catálogo", "Lançamentos SCPI", "Cadastros")`.
`usuario_logado` e `item_atual` repetem os de `tests/test_pagina_catalogo.py`.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_pagina_lancamentos.py tests/test_acesso.py -q`
Expected: FAIL (`NoReverseMatch: 'lancamentos'`)

- [ ] **Step 3: Implement** consultas, views, rotas, templates, ícone, menu, cartão do painel,
  link no detalhe e CSS.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q`
Expected: PASS. `tests/test_clean.py` (todos os itens do menu com ícone) e
`tests/test_painel.py` (limite de consultas do painel) continuam verdes. Se o limite de
consultas do painel subir, aumente-o só pelas consultas novas do cartão (até 3).

- [ ] **Step 5: Commit** — `Página Lançamentos SCPI, cartão no painel e resolução de travas`

---

### Task 8: Documentação, conferência visual e simulação no SCPI real

**Files:**
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Documentation**
  - `CLAUDE.md`:
    - em "O projeto", o subprojeto 4 passa a feito;
    - nos comandos, `uv run python manage.py lancar_saidas --dry-run --limite 1` (abre o
      SCPI);
    - em "Arquitetura", um parágrafo sobre:
      - `scpi/requisicoes.py` (puro, agrupa por lote, travas);
      - `scpi/lancamento.py` (protocolo `SCPI`, `EM_LANCAMENTO` confirmado antes do Salvar,
        `VERIFICAR` para tudo que falha depois, journal em `logs/`, trava `GET_LOCK`);
      - `scpi/lancador.py` (navegação copiada, sem testes);
      - `ExecucaoRobo` e a página Lançamentos SCPI;
      - o robô como o único lugar fora de `servicos.py` que grava em `pedidos` (só status,
        requisição, `lancado_em` e mensagem das linhas).
  - `README.md`: a mesma linha de comando, e um aviso de que `lancar_saidas` sem `--dry-run`
    lança de verdade no SCPI.

- [ ] **Step 2: Visual check (navegador do app, `preview_start`)**
  - Monte o banco local com `montar_cenario()`.
  - Crie um lote `PENDENTE`, um `VERIFICAR` e um `ERRO` pelo shell, com `criar_pedido`.
  - Uma `ExecucaoRobo` em andamento, com algumas linhas de log.
  - Confira o painel (cartão), a página Lançamentos SCPI e o detalhe com trava, em desktop e
    em `resize_window` mobile (375 px), sem rolagem horizontal da página.
  - Apague a execução em andamento e confira a resolução das três ações.

- [ ] **Step 3: Simulação no SCPI real — pare e peça ao João.** Precisa do `.env` com
  `SAEP_USER`/`SAEP_PASS`, da rede da SAEP e de um lote de teste `PENDENTE`. Comando:

```bash
uv run python manage.py lancar_saidas --dry-run --limite 1
```

  Esperado:
  - o Chromium abre, preenche a requisição e confere os itens e o cabeçalho, sem clicar em
    Salvar;
  - o terminal termina com `Lançadas: 0 · simuladas: 1 · …`;
  - a linha continua `PENDENTE`.
  Registre o resultado na descrição do PR. O lançamento real fica para a virada (subprojeto
  5, seção 8 da spec).

- [ ] **Step 4: Full verification**

Run: `uv run ruff check . && uv run ruff format --check . && uv run python manage.py makemigrations --check --dry-run && uv run pytest -q`
Expected: tudo limpo e verde.

- [ ] **Step 5: Commit** — `Documentação do lançamento no SCPI`

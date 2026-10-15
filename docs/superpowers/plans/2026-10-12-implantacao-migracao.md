# Subprojeto 5 — Implantação e migração: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O sistema sobe no servidor Windows do ProducaoLab, recebe os dados das planilhas do
Apps Script (`importar_planilhas`), roda em paralelo com o Apps Script sem lançar nada de
verdade no SCPI e, na virada, assume o lugar dele.

**Architecture:**
- Novo app `implantacao`, sem modelos: leitura do `.xlsx` exportado (`planilha.py`, puro),
  conversão das abas em registros não salvos (`conversao.py`, sem acesso ao banco), gravação
  numa transação (`migracao.py`), backup do banco (`backup.py`) e os comandos
  `importar_planilhas`, `backup_banco` e `robos_em_andamento`.
- Uma chave `LANCAMENTO_REAL` no `.env` bloqueia o lançamento real no SCPI (comando, página e
  painel) até a virada. A importação das planilhas só roda com essa chave desligada.
- Pasta `deploy/`: `tarefa.bat` (Agendador de Tarefas), `atualizar.bat`, `INSTALACAO.md` (para o
  André) e `VIRADA.md` (roteiro da migração e da virada).

**Tech Stack:** Python 3.13, Django 6.x, mysqlclient, openpyxl (novo), waitress, NSSM,
Agendador de Tarefas do Windows, `mysqldump`, pytest + pytest-django, ruff.

**Spec:** `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`, seções 2
(stack: waitress, NSSM, Apache opcional em `/almoxarifado`), 6 (logs), 8 (implantação, migração e
virada) e 9 (item 5).

**Código de referência (fora do repositório):** `AS:` = `../CentralAlmoxarifado/`. O formato das
abas vem de `AS:apps-script/Config.gs` (`COL_`), `AS:apps-script/Setup.gs` (`ABAS_`),
`AS:apps-script/Repositorio.gs` (o que cada coluna recebe) e `AS:apps-script/Regras.gs`
(`montarLinhasSaida_`, `marcadoNaoLancar_`, `situacaoScpi_`).

## Decisões deste plano

Pontos que a spec deixa em aberto:

1. **App `implantacao` em vez de `scpi/`.** A spec põe `importar_planilhas` entre os comandos do
   `scpi`. Ele não fala com o SCPI, e sim com `pedidos` e `catalogo`; o backup também não cabe
   em nenhum app. Depois da virada, `importar_planilhas` e seus módulos podem ser apagados sem
   mexer no resto.
2. **Um `.xlsx` com todas as abas.** É o que "Arquivo › Fazer download › Microsoft Excel" do
   Google Sheets entrega. As colunas são achadas pelo nome do cabeçalho (linha 1), como no
   Apps Script.
3. **A importação substitui tudo, e pode rodar de novo.** Durante o período em paralelo, a
   planilha continua sendo a fonte. Cada execução apaga e recria, numa transação, os pedidos e
   tudo o que deles depende, e também os centros de custo, as opções e os itens de limpeza. Duas
   travas impedem perder dados do Django:
   - recusa se `LANCAMENTO_REAL` está ligado (depois da virada);
   - recusa se o banco tem algum pedido que não está na planilha (pedido feito direto no Django).
4. **Erro bloqueia; aviso não.** Os problemas da planilha são todos juntados e mostrados de uma
   vez. Havendo algum erro, nada é gravado. Saída que o robô lançaria e que se perderia é erro;
   o que só se perde como histórico é aviso.
5. **Status das linhas de saída.** Vem de `Requisição`, `Observações` e `Status SCPI`, nesta
   ordem:
   1. requisição preenchida → `LANCADA` (o número do SCPI vence a observação);
   2. observação com "FORA DE ESTOQUE" ou "NÃO LANÇAR" → `NAO_LANCAR`;
   3. status começando por "VERIFICAR" → `VERIFICAR`; por "EM LANÇAMENTO" → `EM_LANCAMENTO`; por
      "ERRO" → `ERRO`; por "LANÇADA" → `LANCADA`. Os prefixos são comparados após `norm_u`;
   4. status vazio → `PENDENTE`;
   5. outro texto → `VERIFICAR`, com aviso. Na dúvida, a linha fica travada; nunca vira
      `PENDENTE`, que o robô lançaria de novo.

   O texto original do "Status SCPI" vai para `LinhaSaida.mensagem`.
6. **Usuário `planilha`.** `Atendimento.atendido_por` é obrigatório, e a planilha só guarda
   e-mails. Os atendimentos importados e as saídas avulsas (`registrado_por`) apontam para o
   usuário `planilha`: inativo, sem senha utilizável, `first_name` "Planilha (Apps Script)". A
   importação o cria se ele não existir.
7. **Ordem da carga inicial.** O cadastro do SCPI vem antes das planilhas, porque `ItemLimpeza`
   aponta para `Material`. Sem nenhum material no banco, a importação recusa. Item de limpeza
   cujo código não está no cadastro vira aviso e fica de fora.
8. **A coluna "Destinos" da aba `Listas` é ignorada.** No Django, o destino é um centro de custo
   (subprojeto 3). O destino dos pedidos antigos é copiado como texto.
9. **`LANCAMENTO_REAL` vem desligado por padrão.** Sem a variável, só a simulação roda. O
   `settings_test` liga a chave, porque os testes do robô lançam no SCPI simulado; os testes do
   bloqueio desligam com o fixture `settings`.
10. **Os `.bat` chamam o Python do `.venv`, não o `uv run`.** O `uv run` sincronizaria o grupo
    `dev` no servidor. Só o `atualizar.bat` usa o `uv`, com `uv sync --frozen --no-dev`. O
    serviço NSSM também roda `.venv\Scripts\python.exe -m waitress`.
11. **Reinício sem matar o robô.** O NSSM encerra a árvore de processos do serviço ao reiniciar,
    e o `lancar_saidas` disparado pela página é filho do waitress. Duas proteções:
    - `atualizar.bat` começa por `robos_em_andamento`, que falha se houver lançamento ou
      importação em andamento;
    - o `INSTALACAO.md` manda configurar `AppKillProcessTree 0`.
12. **Agendador:**
    - `importar_estoque` a cada 30 min, das 07:00 às 17:00, de segunda a sexta (`/RI 30 /DU 10:01`:
      o minuto a mais garante a execução das 17:00, que cairia no limite exato da duração);
    - `atualizar_catalogo` (cadastro incremental, estoque e saídas) todo dia às 06:30;
    - `backup_banco` todo dia às 23:00, com retenção de 60 dias pelo nome do arquivo.

    A saída de cada tarefa vai para `logs\agendador.log`. São poucas linhas por execução, por
    isso o arquivo não gira.
13. **Apache em `/almoxarifado`, com a área interna em `/painel/`.** O site sai em
    `/almoxarifado` pela opção `--url-prefix=/almoxarifado` do waitress, com
    `ProxyPreserveHost On`. Para o endereço não repetir "almoxarifado", a área interna (painel,
    login, catálogo, lançamentos, recibos e saída avulsa) troca o caminho `/almoxarifado/` por
    `/painel/`. Resultado:
    - formulários: `servidor/almoxarifado/`;
    - área interna: `servidor/almoxarifado/painel/`;
    - admin: `servidor/almoxarifado/admin/`.

    Os nomes das rotas não mudam. Os caminhos antigos não são redirecionados, porque o sistema
    ainda não está no ar. Um teste garante que nenhuma página tem caminho fixo fora do prefixo.

## Global Constraints

- Python `>=3.13,<3.14`, Django 6.x; dependências pelo `uv` (`uv add openpyxl`), sem npm nem CDN.
- Nomes de código, textos, mensagens e commits em português (pt-BR).
- Testes contra MySQL/MariaDB (`config.settings_test`), nunca SQLite; os testes nunca abrem o
  navegador, nunca rodam `mysqldump` de verdade e nunca gravam no `logs/` do repositório.
- Nenhuma mudança de modelo neste plano: `makemigrations --check --dry-run` continua limpo, e o
  app `implantacao` não tem `migrations/`.
- `check --deploy --fail-level WARNING` continua sem avisos (`tests/test_config.py`).
- Segredos só no `.env`, com cada variável nova documentada no `.env.example`.
- Backup: retenção de **60 dias**, pasta **fora do repositório**. Estoque a cada **30 min** em
  horário de expediente; cadastro e saídas **uma vez por dia** (spec, seção 8).
- `ruff check .` e `ruff format --check .` limpos (linha de 100).

## Review Focus

1. **Lançamento real durante o período em paralelo.** As mesmas saídas estão pendentes no Apps
   Script e no Django; um clique em "Lançar" criaria requisições duplicadas no SCPI. Com
   `LANCAMENTO_REAL` desligado, nem o comando, nem a página, nem o painel lançam (Tarefa 1).
2. **Reimportar depois da virada ou por cima de pedido feito no Django.** A substituição
   apagaria dados que só existem no banco. A importação recusa nos dois casos e não toca em nada
   (Tarefa 4).
3. **Saída pendente que não chega ao Django.** É a linha da aba Saídas sem atendimento: pedido
   com transferência incompleta ou linha digitada à mão. Ela deixaria de ser lançada sem
   ninguém notar. Por isso vira erro, e a planilha é recusada (Tarefa 3).
4. **Backup que falha.** Não pode deixar um arquivo parcial com cara de backup, nem apagar os
   backups antigos. A limpeza só roda depois de um backup completo (Tarefa 5).
5. **`atualizar.bat` com o robô lançando.** O reinício do serviço mataria o robô no meio de uma
   requisição, deixando lotes em `VERIFICAR`. O script para antes de tudo se houver robô em
   andamento (Tarefa 6).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `config/settings.py` | `LANCAMENTO_REAL`, `BACKUP_DIR`, `BACKUP_RETENCAO_DIAS`, `MYSQLDUMP`; `implantacao` em `INSTALLED_APPS` |
| `config/settings_test.py` | `LANCAMENTO_REAL = True` |
| `.env.example` | `LANCAMENTO_REAL`, `BACKUP_DIR`, `MYSQLDUMP`, `PLAYWRIGHT_BROWSERS_PATH` |
| `scpi/lancamento.py` | `LANCAMENTO_BLOQUEADO` (texto) |
| `scpi/management/commands/lancar_saidas.py` | recusa o lançamento real bloqueado |
| `pedidos/forms.py`, `pedidos/views/lancamentos.py`, `pedidos/views/almoxarifado.py` | recusa e contexto `lancamento_real` |
| `pedidos/templates/pedidos/_lancamentos.html`, `painel.html` | botões e aviso do bloqueio |
| `implantacao/planilha.py` | `ler_xlsx` e conversão de células (puro) |
| `implantacao/conversao.py` | abas → `Carga` (registros não salvos, erros, avisos) |
| `implantacao/migracao.py` | `gravar(carga)` numa transação, com as travas |
| `implantacao/backup.py` | `fazer_backup`, `vencidos`, `nome_backup` |
| `implantacao/management/commands/` | `importar_planilhas`, `backup_banco`, `robos_em_andamento` |
| `config/urls.py`, `pedidos/urls.py` | área interna em `/painel/` em vez de `/almoxarifado/` |
| `deploy/tarefa.bat`, `deploy/atualizar.bat` | Agendador e atualização (CRLF) |
| `deploy/INSTALACAO.md`, `deploy/VIRADA.md` | instalação e roteiro da migração |
| `tests/planilha_exemplo.py` | abas de exemplo e gravação em `.xlsx` |

---

### Task 1: Bloqueio do lançamento real (`LANCAMENTO_REAL`)

**Files:**
- Modify: `config/settings.py` (perto de `SCPI_PERFIL_DIR`), `config/settings_test.py`, `.env.example`
- Modify: `scpi/lancamento.py`, `scpi/management/commands/lancar_saidas.py`
- Modify: `pedidos/forms.py`, `pedidos/views/lancamentos.py`, `pedidos/views/almoxarifado.py` (função `painel`, contexto dos atalhos)
- Modify: `pedidos/templates/pedidos/_lancamentos.html`, `pedidos/templates/pedidos/painel.html`
- Test: `tests/test_lancamento_real.py`

**Interfaces:**
- Produces: `settings.LANCAMENTO_REAL: bool`; `scpi.lancamento.LANCAMENTO_BLOQUEADO: str`
  ("O lançamento real no SCPI está bloqueado (LANCAMENTO_REAL=0 no .env): até a virada, só a
  simulação roda."); contexto `lancamento_real` nas views `lancamentos` e `painel`.

- [ ] **Step 1: Write the failing tests** em `tests/test_lancamento_real.py` (usa os fixtures
  `dois_lotes`, `journal` e `scpi` do `conftest.py`; `usuario_logado` como em
  `tests/test_pagina_lancamentos.py`; `rodar` e `PRODUCAO` importados de `tests.test_config`):

```python
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _bloqueado(settings, journal):
    settings.LANCAMENTO_REAL = False


def test_comando_recusa_lancamento_real_sem_criar_execucao(monkeypatch, dois_lotes, scpi):
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    with pytest.raises(CommandError, match="bloqueado"):
        call_command("lancar_saidas")
    assert ExecucaoRobo.objects.count() == 0 and scpi.chamadas == []
    assert set(LinhaSaida.objects.values_list("status", flat=True)) == {"PENDENTE"}


def test_execucao_real_do_botao_termina_em_falha(monkeypatch, dois_lotes, scpi):
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    e = ExecucaoRobo.objects.create(simulacao=False)
    with pytest.raises(CommandError, match="bloqueado"):
        call_command("lancar_saidas", "--execucao", str(e.pk))
    e.refresh_from_db()
    assert e.situacao == "FALHA" and "bloqueado" in e.erro and e.fim is not None
    assert scpi.chamadas == []


def test_simulacao_roda_com_o_bloqueio(monkeypatch, dois_lotes, scpi):
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    call_command("lancar_saidas", "--dry-run")
    assert ExecucaoRobo.objects.get().resumo["simuladas"] == 2


@pytest.mark.parametrize("dados", [{}, {"modo": "lancar"}])
def test_botao_lancar_recusado_com_mensagem(client, usuario_logado, monkeypatch, dados):
    monkeypatch.setattr(
        "pedidos.views.lancamentos.iniciar_lancamento",
        lambda *a, **k: pytest.fail("não deveria iniciar"),
    )
    r = client.post(reverse("pedidos:lancar"), dados, follow=True)
    # A mensagem da recusa, não só o aviso fixo da página.
    assert LANCAMENTO_BLOQUEADO in r.content.decode()


def test_simulacao_pelo_botao_continua(client, usuario_logado, monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "pedidos.views.lancamentos.iniciar_lancamento",
        lambda usuario, **k: chamadas.append(k) or ExecucaoRobo(pk=1),
    )
    client.post(reverse("pedidos:lancar"), {"simulacao": "1"})
    assert chamadas == [{"simulacao": True, "limite": None}]


@pytest.mark.parametrize("rota", ["pedidos:lancamentos", "pedidos:painel"])
def test_paginas_mostram_o_bloqueio(client, usuario_logado, dois_lotes, settings, rota):
    html = client.get(reverse(rota)).content.decode()
    assert "Lançamento real bloqueado" in html
    settings.LANCAMENTO_REAL = True
    assert "Lançamento real bloqueado" not in client.get(reverse(rota)).content.decode()


def test_sem_a_variavel_o_lancamento_real_fica_bloqueado():
    codigo = "import django; django.setup(); from django.conf import settings; print(settings.LANCAMENTO_REAL)"
    r = rodar(["-c", codigo], **{**PRODUCAO, "LANCAMENTO_REAL": "", "PYTHON_DOTENV_DISABLED": "1"})
    assert r.stdout.strip() == "False", r.stderr


def test_env_exemplo_documenta_o_bloqueio():
    assert "\nLANCAMENTO_REAL=0\n" in (RAIZ / ".env.example").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_lancamento_real.py -v`
Expected: FAIL (`LANCAMENTO_REAL` não existe; nada é bloqueado).

- [ ] **Step 3: Implement**
  - `settings.py`: `LANCAMENTO_REAL = ler_bool("LANCAMENTO_REAL", False)`, com um comentário
    sobre o período em paralelo. `settings_test.py`: `LANCAMENTO_REAL = True`, com o comentário
    da Decisão 9.
  - `.env.example`, depois de `SCPI_PERFIL_DIR`:
    ```
    # 1 libera o lançamento real no SCPI. Fica 0 no período em paralelo com o Apps Script
    # (só a simulação roda) e vira 1 na virada (deploy/VIRADA.md).
    LANCAMENTO_REAL=0
    ```
  - `scpi/lancamento.py`: constante `LANCAMENTO_BLOQUEADO` (texto em Interfaces).
  - `lancar_saidas.handle`: decidir o modo antes de qualquer trabalho. É simulação se
    `dry_run`, ou se a execução do botão é simulação. Se não for simulação e
    `settings.LANCAMENTO_REAL` estiver desligado:
    - com `--execucao`, a execução vira `FALHA`, com `erro=LANCAMENTO_BLOQUEADO` e `fim=now`;
    - sem `--execucao`, nada é criado;
    - nos dois casos, `CommandError(LANCAMENTO_BLOQUEADO)`.
  - `LancamentoForm.clean_modo`: `"lancar"` com a chave desligada →
    `ValidationError(LANCAMENTO_BLOQUEADO)`. A view já mostra os erros do formulário como
    mensagens.
  - Views `lancamentos` e `painel`: `contexto["lancamento_real"] = settings.LANCAMENTO_REAL`.
  - Templates com `lancamento_real` falso:
    - o botão "Lançar no SCPI" (página e atalho do painel) fica `disabled`;
    - em `_lancamentos.html`, o rádio "Lançar" fica `disabled` e o "Simular" vem `checked`;
    - um `<p class="campo-dica">` diz: "Lançamento real bloqueado até a virada: só a simulação
      roda (LANCAMENTO_REAL no .env)." É texto, não só cor.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_lancamento_real.py tests/test_lancar_saidas.py tests/test_pagina_lancamentos.py tests/test_painel.py -v`
Expected: PASS (os testes antigos continuam passando com `LANCAMENTO_REAL = True` no `settings_test`).

- [ ] **Step 5: Commit**

```bash
git add config/ .env.example scpi/lancamento.py scpi/management/commands/lancar_saidas.py pedidos/ tests/test_lancamento_real.py
git commit -m "Lançamento real no SCPI bloqueado até a virada (LANCAMENTO_REAL)"
```

---

### Task 2: Leitura da planilha exportada

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (`uv add openpyxl`), `config/settings.py` (`"implantacao"` em `INSTALLED_APPS`, depois de `"scpi"`)
- Create: `implantacao/__init__.py`, `implantacao/apps.py` (`ImplantacaoConfig`, `verbose_name = "Implantação"`), `implantacao/planilha.py`
- Create: `tests/planilha_exemplo.py`
- Test: `tests/test_planilha_leitura.py`

**Interfaces:**
- Produces, em `implantacao/planilha.py`:
  - `Linha = dict[str, object]`: cabeçalho → valor da célula, mais a chave `"_linha"`
    (número da linha na planilha; o cabeçalho é a 1).
  - `ABAS: dict[str, tuple[str, ...]]`: colunas obrigatórias por aba, com os nomes exatos de
    `AS:Config.gs`.
    - `"Pedidos"`: Nº, ID, Origem, Criado em, Solicitante, Destino, Observação,
      Atendimento_ID, Data efetiva, Recebedor, Centro de custo, Tipo Saída, Placa, Obs. da
      saída, Atendido em.
    - `"Itens"`: Nº, ID, Código, Material, Unidade, Categoria, Grupo, Subgrupo, Estoque no
      pedido, Qtd pedida, Qtd entregue.
    - `"Saídas"`: Data, Qtd, Código, Descrição do Material, Recebimento, Centro de Custo, Tipo
      Saída, Veículo (Placa), Observações, Requisição, Status SCPI, Lançado SCPI em,
      Origem_ID, Lote_SCPI.
    - `"Centros de Custo"`: DESCR, CODCCUSTO, PLACA.
    - `"Listas"`: Tipos de saída, Grupos ocultos (AB), Categorias (limpeza), Funcionários.
    - `"Lista_Limpeza"`: Código, Categoria, Nome exibido, Unidade exibida.

    "Recibo impresso em" (Pedidos) e "Destinos" (Listas) são opcionais.
  - `class ErroPlanilha(ValueError)`.
  - `ler_xlsx(caminho: Path) -> dict[str, list[Linha]]`.
  - Conversão de células:
    - `texto_celula(v) -> str`;
    - `data_celula(v) -> date | None`;
    - `momento_celula(v) -> datetime | None`;
    - `qtd_celula(v) -> Decimal | None`.
- Produces, em `tests/planilha_exemplo.py`: `abas_exemplo() -> dict[str, list[Linha]]` (os
  dados da tabela abaixo, com `_linha` a partir de 2) e `salvar_xlsx(abas, caminho: Path) -> Path`
  (uma aba por chave; cabeçalho = as chaves da primeira linha, sem `_linha`).

Dados de `abas_exemplo()`. U1, U2, U3 e A1, A2 são UUIDs fixos no módulo. Datas sem aspas são
`datetime`; entre aspas, texto (como o Apps Script grava).

| Aba | Linhas |
|---|---|
| Pedidos | `P-000120`, U1, LIMPEZA, criado 01/09/2026 08:30, "Ana Exemplo", destino "ETA II", obs "", Atendimento_ID A1, "02/09/2026", recebedor "Ana Exemplo", cc "ETA II", "BALCÃO", placa "", obs saída "", atendido 02/09/2026 09:00, recibo 02/09/2026 09:05 · `P-000121`, U2, AB, criado 03/09/2026 10:00, "João Fictício", "ETE Santa Fé", obs "urgente", A2, "05/09/2026", "João Fictício", "ETE Santa Fé", "ENTREGA", "", "", atendido 05/09/2026 11:00, recibo vazio · `AV-000122`, U3, AVULSA, criado 04/09/2026 14:00, "almox@saep.sp.gov.br", "", "", Atendimento_ID U3, "04/09/2026", "Motorista Teste", "FROTA", "ENTREGA", "CZA-1614", "", atendido 04/09/2026 14:00, recibo vazio |
| Itens | U1/P-000120: "023.001.002" DETERGENTE NEUTRO, UN, Limpeza, LIMPEZA, SUB, estoque "", pedida 2, entregue 2 · U1: "008.001.002" CAFÉ 500 G, PCT, Copa/cozinha, GÊNEROS, SUB, "", 1.5, 1.5 · U2/P-000121: "016.005.010" FITA VEDA ROSCA, UN, "", REDES DE ÁGUA, SUB, estoque 10, 3, 3 · U3/AV-000122: "023.004.001" PAPEL HIGIÊNICO, UN, "", LIMPEZA, "", "", 1, 1 |
| Saídas | "02/09/2026", "2", "023.001.002", "DETERGENTE NEUTRO", "Ana Exemplo", "ETA II", "BALCÃO", "", "", "003354/26", "LANÇADA", "02/09/2026 17:10:00", "P-000120", "P-000120" · igual para "008.001.002"/"CAFÉ 500 G"/"1,5" · "05/09/2026", "3", "016.005.010", "FITA VEDA ROSCA", "João Fictício", "ETE Santa Fé", "ENTREGA", "", "", "", "", "", "P-000121", "P-000121" · "04/09/2026", "1", "023.004.001", "PAPEL HIGIÊNICO", "Motorista Teste", "FROTA", "ENTREGA", "CZA1614", "", "", "VERIFICAR NO SCPI: tempo esgotado", "", "AV-000122", "AV-000122" |
| Centros de Custo | ("ETA II", "101", "") · ("ETE Santa Fé", "102", "") · ("FROTA", "205", "CZA1614") |
| Listas | Destinos: ETA II · Tipos de saída: BALCÃO, ENTREGA · Grupos ocultos (AB): GERAL · Categorias (limpeza): Limpeza, Copa/cozinha · Funcionários: Ana Exemplo (colunas de alturas diferentes; as células que sobram ficam `None`) |
| Lista_Limpeza | ("023.001.002", "Limpeza", "Detergente", "") · ("008.001.002", "Copa/cozinha", "", "PCT") |

- [ ] **Step 1: Write the failing tests** em `tests/test_planilha_leitura.py` (sem banco):

```python
def test_le_todas_as_abas_com_numero_da_linha(tmp_path):
    abas = ler_xlsx(salvar_xlsx(abas_exemplo(), tmp_path / "p.xlsx"))
    assert set(abas) == set(ABAS)
    assert [l["Nº"] for l in abas["Pedidos"]] == ["P-000120", "P-000121", "AV-000122"]
    assert abas["Pedidos"][0]["_linha"] == 2 and isinstance(abas["Pedidos"][0]["Criado em"], datetime)


def test_linha_vazia_e_pulada_sem_mudar_a_numeracao(tmp_path):
    exemplo = abas_exemplo()
    caminho = salvar_xlsx(exemplo, tmp_path / "p.xlsx")
    livro = openpyxl.load_workbook(caminho)
    livro["Pedidos"].insert_rows(3)  # linha 3 em branco
    livro.save(caminho)
    assert [l["_linha"] for l in ler_xlsx(caminho)["Pedidos"]] == [2, 4, 5]


def test_cabecalho_com_espacos_e_colunas_opcionais(tmp_path):
    exemplo = abas_exemplo()
    exemplo["Pedidos"] = [{(" Nº " if k == "Nº" else k): v for k, v in l.items() if k != "Recibo impresso em"} for l in exemplo["Pedidos"]]
    abas = ler_xlsx(salvar_xlsx(exemplo, tmp_path / "p.xlsx"))
    assert abas["Pedidos"][0]["Nº"] == "P-000120"


def test_aba_e_coluna_faltando_aparecem_juntas(tmp_path):
    exemplo = abas_exemplo()
    del exemplo["Listas"]
    exemplo["Saídas"] = [{k: v for k, v in l.items() if k != "Qtd"} for l in exemplo["Saídas"]]
    with pytest.raises(ErroPlanilha) as erro:
        ler_xlsx(salvar_xlsx(exemplo, tmp_path / "p.xlsx"))
    assert 'aba "Listas"' in str(erro.value) and 'Saídas: coluna "Qtd"' in str(erro.value)


@pytest.mark.parametrize(("valor", "esperado"), [
    (None, ""), ("  x ", "x"), ("'=SOMA(A1)", "=SOMA(A1)"), (12.0, "12"), (12, "12"), (1.5, "1.5"),
])
def test_texto_celula(valor, esperado):
    assert texto_celula(valor) == esperado


@pytest.mark.parametrize(("valor", "esperado"), [
    (datetime(2026, 9, 2, 0, 0), date(2026, 9, 2)), (date(2026, 9, 2), date(2026, 9, 2)),
    ("02/09/2026", date(2026, 9, 2)), ("2026-09-02", date(2026, 9, 2)), ("", None), (None, None),
])
def test_data_celula(valor, esperado):
    assert data_celula(valor) == esperado


@pytest.mark.parametrize("valor", ["31/02/2026", "2/9/26", "ontem", 45000])
def test_data_celula_invalida(valor):
    with pytest.raises(ValueError):
        data_celula(valor)


@pytest.mark.parametrize(("valor", "local"), [
    (datetime(2026, 9, 2, 17, 10), datetime(2026, 9, 2, 17, 10)),
    ("02/09/2026 17:10", datetime(2026, 9, 2, 17, 10)),
    ("02/09/2026 17:10:05", datetime(2026, 9, 2, 17, 10, 5)),
    ("02/09/2026", datetime(2026, 9, 2, 0, 0)),
])
def test_momento_celula_no_fuso_do_sistema(valor, local):
    m = momento_celula(valor)
    assert timezone.is_aware(m) and timezone.localtime(m).replace(tzinfo=None) == local


@pytest.mark.parametrize(("valor", "esperado"), [
    (1.5, Decimal("1.5")), (2, Decimal("2")), ("1,5", Decimal("1.5")), ("", None), (None, None),
    (0.30000000000000004, Decimal("0.300")),
])
def test_qtd_celula(valor, esperado):
    assert qtd_celula(valor) == esperado


@pytest.mark.parametrize("valor", ["1.5", "abc", -1, "-1"])
def test_qtd_celula_invalida(valor):
    with pytest.raises(ValueError):
        qtd_celula(valor)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_planilha_leitura.py -v`
Expected: FAIL (`ModuleNotFoundError: implantacao` / `openpyxl`).

- [ ] **Step 3: Implement**
  - `uv add openpyxl`.
  - `ler_xlsx`: `openpyxl.load_workbook(caminho, read_only=True, data_only=True)`.
    - Os cabeçalhos são lidos com `texto_celula`; se um nome se repete, vale a primeira coluna.
    - Linha com todas as células `None` ou `""` é descartada; as outras mantêm o número real.
    - Aba ou coluna obrigatória faltando: um único `ErroPlanilha` com todos os casos, um por
      linha. Formato: `A planilha não tem a aba "Listas".` e
      `Saídas: coluna "Qtd" não encontrada.`
  - Conversão de células:
    - `texto_celula`: `None` → `""`; número inteiro (inclusive `12.0`) sem casas decimais;
      texto sem espaços nas pontas e sem um `'` inicial (o `sanitizarTexto_` do Apps Script).
    - `data_celula`: aceita `datetime`/`date` e os textos `dd/mm/aaaa` e `aaaa-mm-dd`; outra
      coisa é `ValueError`.
    - `momento_celula`: `datetime` ingênuo → `timezone.make_aware` (fuso de `TIME_ZONE`);
      aceita também os textos `dd/mm/aaaa[ hh:mm[:ss]]`.
    - `qtd_celula`: número → `Decimal(repr(v)).quantize(Decimal("0.001"))`; texto →
      `regras.parse_qtd_br`; negativo ou inválido → `ValueError`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_planilha_leitura.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock config/settings.py implantacao/ tests/planilha_exemplo.py tests/test_planilha_leitura.py
git commit -m "Leitura do .xlsx exportado das planilhas do Apps Script"
```

---

### Task 3: Conversão das abas em registros

**Files:**
- Create: `implantacao/conversao.py`
- Test: `tests/test_planilha_conversao.py`

**Interfaces:**
- Consumes: `planilha.Linha`, `texto_celula`, `data_celula`, `momento_celula`, `qtd_celula`
  (Task 2); `pedidos.regras` (`norm_placa`, `norm_u`, `marcado_nao_lancar` e as constantes de
  status e origem).
- Produces, em `implantacao/conversao.py`:
  - `status_da_planilha(status: str, requisicao: str, obs: str) -> str | None`, conforme a
    Decisão 5; `None` = texto desconhecido.
  - A dataclass `Carga`, cujos registros nunca são salvos aqui:
    - `pedidos: list[Pedido]`, `itens: list[ItemPedido]`, `atendimentos: list[Atendimento]` e
      `linhas: list[LinhaSaida]`, com as FKs apontando para os objetos da própria carga;
    - `centros: list[CentroCusto]` e `opcoes: list[Opcao]`;
    - `itens_limpeza: list[tuple[str, str, str, str, int]]` (código, categoria, nome exibido,
      unidade exibida, ordem dentro da categoria);
    - `ultimo_numero: int`, `erros: list[str]` e `avisos: list[str]`.
  - `converter(abas: dict[str, list[Linha]]) -> Carga`.
  - Cada erro e aviso começa por `"{aba}, linha {n}: "`.
  - `atendido_por` e `registrado_por` ficam vazios: quem grava os preenche (Task 4).

Regras de `converter`. O que não está aqui segue `AS:Repositorio.gs` (`lerRegistros_`).

- **Pedidos.**
  - Linha sem ID é pulada. Se tem Nº, vira aviso "linha sem ID ignorada".
  - Erros:
    - "ID inválido": não é UUID;
    - "número inválido": não segue `^(P|AV)-\d+$`;
    - "origem inválida": não é LIMPEZA, AB nem AVULSA;
    - "o número X não combina com a origem Y": AV- só com AVULSA, P- só com as outras;
    - "ID repetido (linha N)" e "número repetido (linha N)";
    - "data de criação inválida";
    - "ID do atendimento inválido";
    - "data efetiva inválida", obrigatória quando há atendimento;
    - "saída avulsa sem atendimento".
  - "Atendido em" vazio = "Criado em". "Recibo impresso em" é opcional.
  - `placa = norm_placa`; `nao_lancar = marcado_nao_lancar(Obs. da saída)`. O id do
    atendimento vem do `Atendimento_ID`.
- **Itens.**
  - Ligados pelo ID (minúsculo). Sem pedido: aviso "item sem pedido (gravação incompleta no
    Apps Script) ignorado". O número dele ainda conta para `ultimo_numero`.
  - Erros: "quantidade pedida inválida" (vazia também) e "quantidade entregue inválida".
  - Estoque ilegível vira `None`, sem aviso.
  - Pedido sem nenhum item: aviso "pedido sem itens".
- **Saídas.**
  - Ligadas ao pedido pelo `Origem_ID`; `seq` = ordem de aparição dentro do pedido (1, 2, …);
    `lote` = `Lote_SCPI`, ou o Nº se estiver vazio.
  - Status pela Decisão 5; desconhecido vira `VERIFICAR`, com aviso "status desconhecido".
  - `mensagem` = texto de "Status SCPI".
  - "Lançado SCPI em" ilegível → `None` e aviso.
  - Erros: "data inválida" e "quantidade inválida" (vazia, ilegível ou zero).
  - Linha cujo pedido não existe ou não tem atendimento:
    - status `LANCADA` ou `NAO_LANCAR` → aviso "saída sem atendimento ignorada";
    - qualquer outro → erro "saída sem atendimento, que o robô lançaria: conclua a
      transferência no Apps Script ou marque NÃO LANÇAR".
- **Centros de Custo.**
  - Linha toda vazia é pulada; erros "descrição vazia" e "código vazio".
  - `placa = norm_placa(...) or None`; placa repetida é erro "a placa X já está na linha N".
- **Listas.** Cada coluna obrigatória vira `Opcao(lista=…, valor, ordem=posição, ativo=True)`,
  sem vazios nem repetidos. Mapeamento:
  - Tipos de saída → `TIPO_SAIDA`;
  - Grupos ocultos (AB) → `GRUPO_OCULTO_AB`;
  - Categorias (limpeza) → `CATEGORIA_LIMPEZA`;
  - Funcionários → `FUNCIONARIO`.
- **Lista_Limpeza.**
  - Código ou categoria vazios → aviso e a linha fica de fora.
  - Código repetido → aviso "código repetido"; vale a primeira linha.
  - Categoria fora de "Categorias (limpeza)" → aviso, mas o item entra.
- **`ultimo_numero`.** É o maior número entre os Nº de Pedidos e de Itens e os `Origem_ID` de
  Saídas.

- [ ] **Step 1: Write the failing tests** em `tests/test_planilha_conversao.py` (sem banco):

```python
def test_exemplo_converte_sem_erros():
    c = converter(abas_exemplo())
    assert c.erros == [] and c.avisos == []
    assert [p.numero for p in c.pedidos] == ["P-000120", "P-000121", "AV-000122"]
    assert len(c.itens) == 4 and len(c.atendimentos) == 3 and c.ultimo_numero == 122
    assert [(l.lote, l.seq, l.status) for l in c.linhas] == [
        ("P-000120", 1, "LANCADA"), ("P-000120", 2, "LANCADA"),
        ("P-000121", 1, "PENDENTE"), ("AV-000122", 1, "VERIFICAR"),
    ]
    av = c.linhas[3]
    assert av.placa == "CZA1614" and av.mensagem == "VERIFICAR NO SCPI: tempo esgotado"
    assert c.linhas[1].qtd == Decimal("1.5") and c.linhas[0].requisicao_scpi == "003354/26"
    assert timezone.localtime(c.linhas[0].lancado_em).replace(tzinfo=None) == datetime(2026, 9, 2, 17, 10)
    assert c.atendimentos[2].id == c.pedidos[2].id and c.atendimentos[2].placa == "CZA1614"
    assert c.atendimentos[0].recibo_impresso_em is not None and c.atendimentos[1].recibo_impresso_em is None
    assert [(o.lista, o.valor) for o in c.opcoes] == [
        ("TIPO_SAIDA", "BALCÃO"), ("TIPO_SAIDA", "ENTREGA"), ("GRUPO_OCULTO_AB", "GERAL"),
        ("CATEGORIA_LIMPEZA", "Limpeza"), ("CATEGORIA_LIMPEZA", "Copa/cozinha"), ("FUNCIONARIO", "Ana Exemplo"),
    ]
    assert [(x.codigo, x.placa) for x in c.centros] == [("101", None), ("102", None), ("205", "CZA1614")]
    assert c.itens_limpeza == [("023.001.002", "Limpeza", "Detergente", "", 0), ("008.001.002", "Copa/cozinha", "", "PCT", 0)]


@pytest.mark.parametrize(("status", "requisicao", "obs", "esperado"), [
    ("LANÇADA", "003354/26", "", "LANCADA"), ("", "003354/26", "", "LANCADA"),
    ("ERRO: x", "003354/26", "NÃO LANÇAR", "LANCADA"), ("", "", "FORA DE ESTOQUE", "NAO_LANCAR"),
    ("", "", "não lançar", "NAO_LANCAR"), ("VERIFICAR NO SCPI: x", "", "", "VERIFICAR"),
    ("EM LANÇAMENTO 09/10", "", "", "EM_LANCAMENTO"), ("ERRO: saldo", "", "", "ERRO"),
    ("LANÇADA", "", "", "LANCADA"), ("", "", "", "PENDENTE"), ("OK", "", "", None),
])
def test_status_da_planilha(status, requisicao, obs, esperado):
    assert status_da_planilha(status, requisicao, obs) == esperado


@pytest.mark.parametrize(("aba", "indice", "campos", "erro"), [
    ("Pedidos", 0, {"ID": "abc"}, "Pedidos, linha 2: ID inválido"),
    ("Pedidos", 0, {"Nº": "X-1"}, "Pedidos, linha 2: número inválido"),
    ("Pedidos", 0, {"Origem": "OUTRA"}, "Pedidos, linha 2: origem inválida"),
    ("Pedidos", 2, {"Nº": "P-000122"}, "Pedidos, linha 4: o número P-000122 não combina com a origem AVULSA"),
    ("Pedidos", 0, {"Criado em": ""}, "Pedidos, linha 2: data de criação inválida"),
    ("Pedidos", 0, {"Data efetiva": "31/02/2026"}, "Pedidos, linha 2: data efetiva inválida"),
    ("Pedidos", 0, {"Atendimento_ID": "x"}, "Pedidos, linha 2: ID do atendimento inválido"),
    ("Pedidos", 2, {"Atendimento_ID": ""}, "Pedidos, linha 4: saída avulsa sem atendimento"),
    ("Itens", 0, {"Qtd pedida": "1.5"}, "Itens, linha 2: quantidade pedida inválida"),
    ("Itens", 0, {"Qtd entregue": "abc"}, "Itens, linha 2: quantidade entregue inválida"),
    ("Saídas", 2, {"Qtd": "0"}, "Saídas, linha 4: quantidade inválida"),
    ("Saídas", 2, {"Data": ""}, "Saídas, linha 4: data inválida"),
    ("Saídas", 2, {"Origem_ID": "P-000999"}, "Saídas, linha 4: saída sem atendimento"),
    ("Centros de Custo", 0, {"CODCCUSTO": ""}, "Centros de Custo, linha 2: código vazio"),
    ("Centros de Custo", 0, {"PLACA": "cza-1614"}, "Centros de Custo, linha 4: a placa CZA1614 já está na linha 2"),
])
def test_erros(aba, indice, campos, erro):
    abas = abas_exemplo()
    abas[aba][indice].update(campos)
    assert any(e.startswith(erro) for e in converter(abas).erros), converter(abas).erros


def test_id_e_numero_repetidos():
    abas = abas_exemplo()
    abas["Pedidos"][1].update({"ID": abas["Pedidos"][0]["ID"], "Nº": "P-000120"})
    erros = converter(abas).erros
    assert any(e.startswith("Pedidos, linha 3: ID repetido (linha 2)") for e in erros)
    assert any(e.startswith("Pedidos, linha 3: número repetido (linha 2)") for e in erros)


def test_saida_de_pedido_sem_atendimento_e_erro():
    abas = abas_exemplo()
    abas["Pedidos"][1]["Atendimento_ID"] = ""
    assert any(e.startswith("Saídas, linha 4: saída sem atendimento") for e in converter(abas).erros)


@pytest.mark.parametrize("campos", [
    {"Origem_ID": "P-000999", "Requisição": "003400/26"},
    {"Origem_ID": "P-000999", "Observações": "NÃO LANÇAR"},
])
def test_saida_sem_atendimento_ja_resolvida_e_so_aviso(campos):
    abas = abas_exemplo()
    abas["Saídas"][2].update(campos)
    c = converter(abas)
    assert c.erros == [] and any(a.startswith("Saídas, linha 4: saída sem atendimento ignorada") for a in c.avisos)
    assert len(c.linhas) == 3


def test_status_desconhecido_trava_a_linha_com_aviso():
    abas = abas_exemplo()
    abas["Saídas"][2]["Status SCPI"] = "OK"
    c = converter(abas)
    assert c.linhas[2].status == "VERIFICAR" and c.linhas[2].mensagem == "OK"
    assert any(a.startswith("Saídas, linha 4: status desconhecido") for a in c.avisos)


def test_item_sem_pedido_e_aviso_e_conta_na_numeracao():
    abas = abas_exemplo()
    abas["Itens"].append({**abas["Itens"][0], "ID": str(uuid.uuid4()), "Nº": "P-000130", "_linha": 6})
    c = converter(abas)
    assert c.erros == [] and c.ultimo_numero == 130 and len(c.itens) == 4
    assert any(a.startswith("Itens, linha 6: item sem pedido") for a in c.avisos)


def test_lista_limpeza_repetida_ou_com_categoria_fora_da_lista():
    abas = abas_exemplo()
    abas["Lista_Limpeza"].append({**abas["Lista_Limpeza"][0], "_linha": 4})
    abas["Lista_Limpeza"][1]["Categoria"] = "Escritório"
    c = converter(abas)
    assert [i[0] for i in c.itens_limpeza] == ["023.001.002", "008.001.002"]
    assert any(a.startswith("Lista_Limpeza, linha 4: código repetido") for a in c.avisos)
    assert any(a.startswith("Lista_Limpeza, linha 3:") and "Escritório" in a for a in c.avisos)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_planilha_conversao.py -v`
Expected: FAIL (`ModuleNotFoundError: implantacao.conversao`).

- [ ] **Step 3: Implement `converter` and `status_da_planilha`** in `implantacao/conversao.py` following the rules above. Instantiating models without saving needs no database.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_planilha_conversao.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add implantacao/conversao.py tests/test_planilha_conversao.py
git commit -m "Conversão das abas Pedidos, Itens, Saídas e cadastros em registros"
```

---

### Task 4: Gravação e comando `importar_planilhas`

**Files:**
- Create: `implantacao/migracao.py`, `implantacao/management/__init__.py`, `implantacao/management/commands/__init__.py`, `implantacao/management/commands/importar_planilhas.py`
- Test: `tests/test_importar_planilhas.py`

**Interfaces:**
- Consumes: `ler_xlsx`, `ErroPlanilha` (Task 2); `converter`, `Carga` (Task 3); `settings.LANCAMENTO_REAL` (Task 1).
- Produces, em `implantacao/migracao.py`:
  - `USUARIO_PLANILHA = "planilha"`;
  - `class MigracaoRecusada(Exception)`;
  - `gravar(carga: Carga) -> list[str]`, que devolve os avisos da gravação (itens de limpeza
    sem material).
- Comando: `importar_planilhas --arquivo <xlsx> [--dry-run]`.
  - Os avisos saem como linhas `  Aviso: …`.
  - Havendo erros, `CommandError` com o texto `A planilha tem N problema(s); nada foi gravado:`
    seguido de um erro por linha (`- …`).
  - O resumo, na simulação e na gravação, é
    `Pedidos: 3 · itens: 4 · atendimentos: 3 · linhas de saída: 4 (pendentes: 1) · centros de custo: 3 · opções: 6 · itens de limpeza: 2 · último número: 122`.
  - Com `--dry-run`, a última linha é `Simulação: nada foi gravado.`

`gravar` roda numa única `transaction.atomic()`, nesta ordem:
1. As travas. Qualquer uma levanta `MigracaoRecusada` antes de alterar qualquer coisa:
   - `settings.LANCAMENTO_REAL` ligado → "O lançamento real já foi liberado (LANCAMENTO_REAL=1):
     depois da virada, a importação das planilhas substituiria dados do sistema.";
   - pedido no banco cujo id não está na carga → "O banco tem pedidos que não estão na planilha:
     P-…, … (até 10 números). A importação substituiria esses pedidos; apague-os no admin se
     forem de teste.";
   - carga com itens de limpeza e nenhum `Material` → "Nenhum material cadastrado: carregue o
     cadastro do SCPI antes (importar_cadastro).".
2. Apaga `Pedido` (em cascata: itens, atendimentos e linhas), `ItemLimpeza`, `CentroCusto` e
   `Opcao`.
3. Obtém ou cria o usuário `planilha` (Decisão 6). Ele vira `atendido_por` de todos os
   atendimentos e `registrado_por` das saídas avulsas.
4. `bulk_create` de cada lista. Item de limpeza cujo código não está em `Material` vira o aviso
   `Lista_Limpeza: código X não está no cadastro do SCPI; item ignorado.`
5. `Sequencia` "PEDIDOS": `ultimo = max(ultimo atual, carga.ultimo_numero)`.

- [ ] **Step 1: Write the failing tests** em `tests/test_importar_planilhas.py`:

```python
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _antes_da_virada(settings):
    settings.LANCAMENTO_REAL = False


@pytest.fixture
def xlsx(tmp_path):
    return lambda abas=None: str(salvar_xlsx(abas or abas_exemplo(), tmp_path / "planilha.xlsx"))


def importar(caminho, *args):
    saida = io.StringIO()
    call_command("importar_planilhas", "--arquivo", caminho, *args, stdout=saida)
    return saida.getvalue()


def test_importa_a_planilha_de_ponta_a_ponta(xlsx):
    montar_cenario()
    saida = importar(xlsx())
    assert "Pedidos: 3 · itens: 4 · atendimentos: 3 · linhas de saída: 4 (pendentes: 1)" in saida
    p = Pedido.objects.get(numero="P-000120")
    assert p.situacao_scpi.rotulo == "Lançado 003354/26" and p.atendimento.recebedor == "Ana Exemplo"
    planilha = get_user_model().objects.get(username="planilha")
    assert not planilha.is_active and not planilha.has_usable_password()
    assert p.atendimento.atendido_por == planilha
    assert Pedido.objects.get(numero="AV-000122").registrado_por == planilha
    assert lotes_pendentes() == 1 and [t.lote for t in lotes_travados()] == ["AV-000122"]
    assert Sequencia.objects.get(nome="PEDIDOS").ultimo == 122
    assert list(CentroCusto.objects.order_by("codigo").values_list("codigo", flat=True)) == ["101", "102", "205"]
    assert Opcao.valores(Opcao.Lista.FUNCIONARIO) == ["Ana Exemplo"]
    assert ItemLimpeza.objects.get(material__codigo="023.001.002").nome_exibido == "Detergente"


def test_reimportar_substitui_sem_duplicar(xlsx):
    montar_cenario()
    importar(xlsx())
    abas = abas_exemplo()
    abas["Saídas"][2].update({"Requisição": "003400/26", "Status SCPI": "LANÇADA"})
    importar(xlsx(abas))
    assert Pedido.objects.count() == 3 and LinhaSaida.objects.count() == 4
    assert LinhaSaida.objects.get(lote="P-000121").status == "LANCADA" and lotes_pendentes() == 0


def test_dry_run_nao_grava(xlsx):
    montar_cenario()
    saida = importar(xlsx(), "--dry-run")
    assert "Pedidos: 3" in saida and "Simulação: nada foi gravado." in saida
    assert Pedido.objects.count() == 0 and not get_user_model().objects.filter(username="planilha").exists()


def test_planilha_com_erro_nao_grava_nada(xlsx):
    montar_cenario()
    centros_antes = CentroCusto.objects.count()
    abas = abas_exemplo()
    abas["Itens"][0]["Qtd pedida"] = "1.5"
    with pytest.raises(CommandError, match=r"nada foi gravado:(.|\n)*Itens, linha 2"):
        importar(xlsx(abas))
    assert Pedido.objects.count() == 0 and CentroCusto.objects.count() == centros_antes


def test_recusa_depois_da_virada(xlsx, settings):
    montar_cenario()
    settings.LANCAMENTO_REAL = True
    with pytest.raises(CommandError, match="LANCAMENTO_REAL=1"):
        importar(xlsx())
    assert Pedido.objects.count() == 0


def test_recusa_pedido_do_banco_fora_da_planilha(xlsx):
    montar_cenario()
    feito_no_django = criar_pedido()
    with pytest.raises(CommandError, match=f"não estão na planilha: {feito_no_django.numero}"):
        importar(xlsx())
    assert list(Pedido.objects.all()) == [feito_no_django]


def test_recusa_sem_cadastro_do_scpi(xlsx):
    with pytest.raises(CommandError, match="importar_cadastro"):
        importar(xlsx())


def test_item_de_limpeza_sem_material_vira_aviso(xlsx):
    montar_cenario()
    abas = abas_exemplo()
    abas["Lista_Limpeza"].append({"Código": "999.999.999", "Categoria": "Limpeza", "Nome exibido": "", "Unidade exibida": "", "_linha": 4})
    saida = importar(xlsx(abas))
    assert "Aviso: Lista_Limpeza: código 999.999.999 não está no cadastro" in saida
    assert ItemLimpeza.objects.count() == 2


def test_arquivo_sem_aba_obrigatoria(xlsx):
    abas = abas_exemplo()
    del abas["Itens"]
    with pytest.raises(CommandError, match='aba "Itens"'):
        importar(xlsx(abas))
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_importar_planilhas.py -v`
Expected: FAIL (`Unknown command: 'importar_planilhas'`).

- [ ] **Step 3: Implement `gravar` and the command.** `ErroPlanilha` and `MigracaoRecusada` both become `CommandError`. Log the summary to the `"implantacao"` logger as well (`logger.info`).

- [ ] **Step 4: Run the tests and the full suite**

Run: `uv run pytest tests/test_importar_planilhas.py -v` then `uv run pytest`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add implantacao/ tests/test_importar_planilhas.py
git commit -m "Comando importar_planilhas: migração única das planilhas do Apps Script"
```

---

### Task 5: Backup do banco (`backup_banco`)

**Files:**
- Modify: `config/settings.py` (depois de `LOG_DIR`), `.env.example`
- Create: `implantacao/backup.py`, `implantacao/management/commands/backup_banco.py`
- Test: `tests/test_backup.py`

**Interfaces:**
- Produces:
  - `settings.BACKUP_DIR: Path`: env `BACKUP_DIR`, padrão `BASE_DIR.parent / "backups-almoxarifado"`
    (fora do repositório);
  - `settings.BACKUP_RETENCAO_DIAS = 60`;
  - `settings.MYSQLDUMP: str`: env `MYSQLDUMP`, padrão `"mysqldump"`.
- Produces, em `implantacao/backup.py`:
  - `class ErroBackup(Exception)`;
  - `nome_backup(momento: datetime) -> str`: `almoxarifado-AAAAMMDD-HHMMSS.sql.gz`, na hora local;
  - `vencidos(pasta: Path, hoje: date, dias: int) -> list[Path]`: os arquivos com aquele padrão
    de nome cuja data é anterior a `hoje - dias`, ordenados. Os outros arquivos nunca entram;
  - `fazer_backup(pasta: Path, momento: datetime) -> Path`.
- Comando `backup_banco`:
  1. `fazer_backup(settings.BACKUP_DIR, timezone.localtime())`;
  2. só depois de um backup bem-sucedido, apaga os `vencidos(..., settings.BACKUP_RETENCAO_DIAS)`;
  3. imprime `Backup gravado: <caminho> (<tamanho> KB). Apagados N backup(s) com mais de 60 dias.`

  `ErroBackup` vira `CommandError`.

`fazer_backup`:
1. Cria a pasta.
2. Roda `subprocess.run` com `[MYSQLDUMP, "--single-transaction", "--routines", "--triggers",
   "--default-character-set=utf8mb4", "--host", HOST, "--port", PORT, "--user", USER, NAME]`.
   - A senha vai só no ambiente, em `MYSQL_PWD`; nunca nos argumentos.
   - `stdout` vai para um arquivo temporário `<nome>.sql.parcial` na própria pasta;
     `stderr=PIPE`.
3. Programa ausente (`FileNotFoundError`) → `ErroBackup("Programa não encontrado: … (MYSQLDUMP no .env)")`.
4. Código diferente de zero → `ErroBackup("O mysqldump terminou com o código N: <fim do stderr>")`;
   saída vazia → `ErroBackup("O mysqldump não gerou nada (saída vazia).")`.
5. No sucesso, comprime com `gzip` para `<nome>.gz.parcial` e renomeia para o nome final.
6. Arquivos `.parcial` são sempre apagados (`finally`).

- [ ] **Step 1: Write the failing tests** em `tests/test_backup.py`:

```python
DUMP = b"-- MySQL dump\nCREATE TABLE x (id int);\n"


@pytest.fixture
def pasta(settings, tmp_path):
    settings.BACKUP_DIR = tmp_path / "backups"
    return settings.BACKUP_DIR


def falso_mysqldump(chamadas, codigo=0, saida=DUMP, erro=b""):
    def run(args, **kwargs):
        chamadas.append((args, kwargs))
        kwargs["stdout"].write(saida)
        return subprocess.CompletedProcess(args, codigo, stderr=erro)
    return run


def test_nome_e_vencidos(tmp_path):
    assert nome_backup(datetime(2026, 10, 12, 23, 0, 5)) == "almoxarifado-20261012-230005.sql.gz"
    hoje = date(2026, 10, 12)
    for nome in ["almoxarifado-20260812-230000.sql.gz", "almoxarifado-20260813-230000.sql.gz",
                 "outro.txt", "almoxarifado-lixo.sql.gz"]:
        (tmp_path / nome).write_bytes(b"x")
    assert [p.name for p in vencidos(tmp_path, hoje, 60)] == ["almoxarifado-20260812-230000.sql.gz"]


@pytest.mark.django_db
def test_backup_comprime_e_apaga_os_vencidos(monkeypatch, pasta, settings):
    chamadas = []
    monkeypatch.setattr("implantacao.backup.subprocess.run", falso_mysqldump(chamadas))
    pasta.mkdir()
    (pasta / "almoxarifado-20200101-230000.sql.gz").write_bytes(b"velho")
    saida = io.StringIO()
    call_command("backup_banco", stdout=saida)
    arquivos = sorted(p.name for p in pasta.iterdir())
    assert len(arquivos) == 1 and arquivos[0].startswith("almoxarifado-") and arquivos[0].endswith(".sql.gz")
    assert gzip.decompress((pasta / arquivos[0]).read_bytes()) == DUMP
    args, kwargs = chamadas[0]
    banco = settings.DATABASES["default"]
    assert "--single-transaction" in args and args[-1] == banco["NAME"]
    assert kwargs["env"]["MYSQL_PWD"] == banco["PASSWORD"]
    assert not any(a.startswith("-p") or a.startswith("--password") for a in args)
    assert "Apagados 1 backup(s)" in saida.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize(("codigo", "saida", "erro"), [(2, b"", b"Access denied for user"), (0, b"", b"")])
def test_falha_nao_deixa_parcial_nem_apaga_os_antigos(monkeypatch, pasta, codigo, saida, erro):
    monkeypatch.setattr("implantacao.backup.subprocess.run", falso_mysqldump([], codigo, saida, erro))
    pasta.mkdir()
    antigo = pasta / "almoxarifado-20200101-230000.sql.gz"
    antigo.write_bytes(b"velho")
    with pytest.raises(CommandError, match="Access denied" if erro else "vazia"):
        call_command("backup_banco")
    assert list(pasta.iterdir()) == [antigo]


@pytest.mark.django_db
def test_programa_ausente(monkeypatch, pasta, settings):
    settings.MYSQLDUMP = "nao-existe-mysqldump"
    with pytest.raises(CommandError, match="MYSQLDUMP"):
        call_command("backup_banco")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_backup.py -v`
Expected: FAIL (`ModuleNotFoundError: implantacao.backup`).

- [ ] **Step 3: Implement** `backup.py`, the command and the settings, and add to `.env.example`:

```
# Pasta dos backups diários do banco, fora do repositório (vazio = ..\backups-almoxarifado).
BACKUP_DIR=
# Programa do dump: mysqldump (MySQL) ou mariadb-dump (MariaDB), com o caminho se não estiver no PATH.
MYSQLDUMP=
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_backup.py -v`
Expected: PASS

- [ ] **Step 5: Check by hand against the local database** (needs `mysqldump` or `mariadb-dump`; set `MYSQLDUMP` in `.env` if it is not on the PATH)

Run: `uv run python manage.py backup_banco`
Expected: `Backup gravado: ...\backups-almoxarifado\almoxarifado-....sql.gz (... KB). Apagados 0 backup(s) com mais de 60 dias.`; the file opens with `uv run python -c "import gzip,sys; print(gzip.open(sys.argv[1]).read(200))" <arquivo>`.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py .env.example implantacao/ tests/test_backup.py
git commit -m "Backup diário do banco com retenção de 60 dias (backup_banco)"
```

---

### Task 6: Scripts do servidor (`robos_em_andamento`, `tarefa.bat`, `atualizar.bat`)

**Files:**
- Create: `implantacao/management/commands/robos_em_andamento.py`
- Create: `deploy/tarefa.bat`, `deploy/atualizar.bat` (CRLF)
- Modify: `.gitattributes`
- Test: `tests/test_scripts_servidor.py`

**Interfaces:**
- Consumes: `ExecucaoRobo.em_andamento()`, `Importacao.em_andamento()`.
- Produces:
  - Comando `robos_em_andamento`: sem nenhum robô, imprime `Nenhum robô em andamento.` e sai
    com 0. Com algum, levanta `CommandError` que começa por
    `Há robô em andamento; espere terminar:`, com uma linha por execução:
    - `Simulação #<pk> desde <hh:mm>` ou `Lançamento #<pk> desde <hh:mm>`;
    - `Importação de <tipo legível> desde <hh:mm>`.
  - `deploy/tarefa.bat <comando> [args]`: roda `.venv\Scripts\python.exe manage.py <comando>`
    na raiz, acrescenta a saída em `%TAREFA_LOG%` e repassa o código de saída. Sem
    `TAREFA_LOG`, grava em `logs\agendador.log`.

`deploy/tarefa.bat`:

```bat
@echo off
rem Roda um comando do manage.py pelo Agendador de Tarefas, com a saída em logs\agendador.log.
rem Exemplo: deploy\tarefa.bat importar_estoque
setlocal
cd /d "%~dp0.."
if not defined TAREFA_LOG set "TAREFA_LOG=%CD%\logs\agendador.log"
echo === %DATE% %TIME% %* ===>> "%TAREFA_LOG%"
".venv\Scripts\python.exe" manage.py %* >> "%TAREFA_LOG%" 2>&1
exit /b %ERRORLEVEL%
```

`deploy/atualizar.bat`. A ordem é fixa: cada linha de comando termina em `|| goto :falha`.

```bat
@echo off
rem Atualiza o Central Almoxarifado no servidor e reinicia o serviço (rode como administrador).
rem Para antes de tudo se houver robô em andamento: o reinício o mataria no meio.
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" manage.py robos_em_andamento || goto :falha
git pull --ff-only || goto :falha
uv sync --frozen --no-dev || goto :falha
".venv\Scripts\python.exe" manage.py migrate --noinput || goto :falha
".venv\Scripts\python.exe" manage.py collectstatic --noinput || goto :falha
".venv\Scripts\python.exe" manage.py check --deploy --fail-level WARNING || goto :falha
nssm restart CentralAlmoxarifado || goto :falha
echo Atualizado.
exit /b 0
:falha
echo Atualização interrompida: corrija o erro acima e rode de novo.
exit /b 1
```

- [ ] **Step 1: Write the failing tests** em `tests/test_scripts_servidor.py`:

```python
RAIZ = Path(__file__).resolve().parent.parent
DEPLOY = RAIZ / "deploy"


@pytest.mark.django_db
def test_sem_robo_em_andamento():
    saida = io.StringIO()
    call_command("robos_em_andamento", stdout=saida)
    assert "Nenhum robô em andamento." in saida.getvalue()


@pytest.mark.django_db
def test_lancamento_ou_importacao_em_andamento_param_a_atualizacao():
    e = ExecucaoRobo.objects.create(simulacao=True)
    Importacao.objects.create(tipo=Importacao.Tipo.ESTOQUE)
    with pytest.raises(CommandError) as erro:
        call_command("robos_em_andamento")
    assert f"Simulação #{e.pk}" in str(erro.value) and "Importação de Estoque" in str(erro.value)


@pytest.mark.django_db
def test_execucao_interrompida_nao_conta():
    ExecucaoRobo.objects.create(inicio=timezone.now() - timedelta(hours=2))
    call_command("robos_em_andamento", stdout=io.StringIO())


def test_atualizar_para_no_primeiro_erro_e_segue_a_ordem():
    texto = (DEPLOY / "atualizar.bat").read_text(encoding="utf-8")
    comandos = [l for l in texto.splitlines() if l.startswith(('".venv', "git ", "uv ", "nssm "))]
    assert comandos and all(l.endswith(" || goto :falha") for l in comandos)
    ordem = ["robos_em_andamento", "git pull --ff-only", "uv sync --frozen --no-dev", "migrate --noinput",
             "collectstatic --noinput", "check --deploy --fail-level WARNING", "nssm restart CentralAlmoxarifado"]
    posicoes = [texto.index(trecho) for trecho in ordem]
    assert posicoes == sorted(posicoes)


@pytest.mark.parametrize("nome", ["tarefa.bat", "atualizar.bat"])
def test_bat_com_fim_de_linha_do_windows(nome):
    dados = (DEPLOY / nome).read_bytes()
    assert dados.count(b"\n") == dados.count(b"\r\n") > 0


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe")
def test_tarefa_repassa_o_codigo_de_saida(tmp_path):
    ambiente = {**os.environ, "TAREFA_LOG": str(tmp_path / "agendador.log")}
    ok = subprocess.run(["cmd", "/c", str(DEPLOY / "tarefa.bat"), "check"], env=ambiente, timeout=120)
    falha = subprocess.run(["cmd", "/c", str(DEPLOY / "tarefa.bat"), "comando_que_nao_existe"], env=ambiente, timeout=120)
    assert ok.returncode == 0 and falha.returncode != 0
    log = (tmp_path / "agendador.log").read_text(encoding="utf-8", errors="replace")
    assert "=== " in log and "comando_que_nao_existe" in log
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_scripts_servidor.py -v`
Expected: FAIL (`Unknown command: 'robos_em_andamento'`; `deploy/` não existe).

- [ ] **Step 3: Implement**
  - O comando `robos_em_andamento`.
  - Os dois `.bat` acima, gravados com CRLF:
    `uv run python -c "import pathlib,sys; [pathlib.Path(p).write_bytes(pathlib.Path(p).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')) for p in sys.argv[1:]]" deploy/tarefa.bat deploy/atualizar.bat`.
  - Em `.gitattributes`, as linhas
    `# Scripts do cmd.exe: CRLF, senão rótulos e goto falham.` e
    `deploy/*.bat text eol=crlf`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_scripts_servidor.py -v`
Expected: PASS (no Windows, também `test_tarefa_repassa_o_codigo_de_saida`).

- [ ] **Step 5: Commit**

```bash
git add .gitattributes deploy/tarefa.bat deploy/atualizar.bat implantacao/management/commands/robos_em_andamento.py tests/test_scripts_servidor.py
git commit -m "Scripts do servidor: tarefas agendadas e atualização que espera os robôs"
```

---

### Task 7: Área interna em `/painel/`

**Files:**
- Modify: `config/urls.py` (`almoxarifado/catalogo/` → `painel/catalogo/`; `almoxarifado/` → `painel/`, o `include("contas.urls")`)
- Modify: `pedidos/urls.py` (o prefixo `almoxarifado/` de cada rota interna vira `painel/`)
- Modify: `tests/test_clean.py:119-123` (caminho fixo `/almoxarifado/` → `reverse("pedidos:painel")`)
- Test: `tests/test_rotas.py`

**Interfaces:**
- Produces: os mesmos nomes de rota, com caminhos novos. Todo o resto do código usa
  `{% url %}`/`reverse`, e a Task 8 confere que nenhuma página tem caminho fixo.

- [ ] **Step 1: Write the failing test** em `tests/test_rotas.py`:

```python
@pytest.mark.parametrize(("rota", "args", "caminho"), [
    ("pedidos:inicio", [], "/"),
    ("pedidos:formulario", ["limpeza"], "/pedido/limpeza/"),
    ("pedidos:painel", [], "/painel/"),
    ("login", [], "/painel/entrar/"),
    ("logout", [], "/painel/sair/"),
    ("pedidos:detalhe", ["P-000001"], "/painel/pedidos/P-000001/"),
    ("pedidos:avulsa", [], "/painel/saida-avulsa/"),
    ("pedidos:recibos_pendentes", [], "/painel/recibos/pendentes/"),
    ("pedidos:lancamentos", [], "/painel/lancamentos/"),
    ("catalogo:situacao", [], "/painel/catalogo/"),
    ("admin:index", [], "/admin/"),
])
def test_area_interna_fica_em_painel(rota, args, caminho):
    assert reverse(rota, args=args) == caminho


@pytest.mark.django_db
def test_caminho_antigo_nao_existe_mais(client):
    assert client.get("/almoxarifado/").status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_rotas.py -v`
Expected: FAIL (as rotas internas ainda começam por `/almoxarifado/`).

- [ ] **Step 3: Implement.** Trocar os prefixos em `config/urls.py` e `pedidos/urls.py`, sem
  mudar nenhum nome de rota. Depois procurar caminhos fixos com
  `rg -n '"/almoxarifado|almoxarifado/' --glob '!docs/**'`; só podem sobrar o nome do módulo
  `views/almoxarifado.py`, os textos de exemplo de `.env.example` e `tests/test_telegram.py`
  (uma URL qualquer). Corrigir `tests/test_clean.py` para usar `reverse`.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/urls.py pedidos/urls.py tests/test_clean.py tests/test_rotas.py
git commit -m "Área interna em /painel/ (atrás do Apache em /almoxarifado)"
```

---

### Task 8: Guia de instalação e Apache em `/almoxarifado`

**Files:**
- Create: `deploy/INSTALACAO.md`
- Modify: `.env.example` (`PLAYWRIGHT_BROWSERS_PATH`)
- Test: `tests/test_prefixo.py`, `tests/test_config.py` (um teste novo)

**Interfaces:**
- Consumes: `deploy/tarefa.bat`, `deploy/atualizar.bat`, comandos `backup_banco` e
  `robos_em_andamento` (Tasks 5 e 6), `LANCAMENTO_REAL` (Task 1).

- [ ] **Step 1: Write the failing tests**

Em `tests/test_prefixo.py`:

```python
PREFIXO = "/almoxarifado"
ATRIBUTOS = re.compile(r'(?:href|src|action|hx-get|hx-post)="(/[^"]*)"')


@pytest.fixture
def prefixo():
    set_script_prefix(PREFIXO + "/")
    yield
    set_script_prefix("/")


@pytest.mark.django_db
@pytest.mark.parametrize("rota", [
    "pedidos:inicio", "login", "pedidos:painel", "pedidos:avulsa", "pedidos:recibos_pendentes",
    "pedidos:lancamentos", "catalogo:situacao",
])
def test_nenhum_caminho_fixo_fora_do_prefixo(client, prefixo, rota):
    """Atrás do Apache em /almoxarifado, todo link, formulário e chamada HTMX leva o prefixo."""
    montar_cenario()
    client.force_login(get_user_model().objects.create_user("12345", password="x"))
    url = reverse(rota)  # já com o prefixo
    assert url.startswith(PREFIXO + "/")
    html = client.get(url[len(PREFIXO):], SCRIPT_NAME=PREFIXO).content.decode()
    fora = [c for c in ATRIBUTOS.findall(html) if not c.startswith(PREFIXO + "/")]
    assert fora == [], fora


def test_estatico_servido_sob_o_prefixo(prefixo):
    """O waitress com --url-prefix passa SCRIPT_NAME=/almoxarifado; o whitenoise acha o arquivo.
    O WSGIHandler grava o prefixo na thread; o fixture `prefixo` o devolve a "/" no fim."""
    from config.wsgi import application
    ambiente = {}
    setup_testing_defaults(ambiente)
    ambiente.update(SCRIPT_NAME=PREFIXO, PATH_INFO="/static/interface/css/clean.css", HTTP_HOST="testserver")
    estado = []
    corpo = b"".join(application(ambiente, lambda status, cabecalhos, *a: estado.append(status)))
    assert estado[0].startswith("200") and corpo
```

Em `tests/test_config.py`:

```python
def test_env_exemplo_documenta_a_implantacao():
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for variavel in ["LANCAMENTO_REAL", "BACKUP_DIR", "MYSQLDUMP", "PLAYWRIGHT_BROWSERS_PATH", "SCPI_HEADLESS"]:
        assert f"\n{variavel}=" in exemplo, variavel
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/test_prefixo.py tests/test_config.py::test_env_exemplo_documenta_a_implantacao -v`
Expected: `test_env_exemplo_documenta_a_implantacao` FAILS (`PLAYWRIGHT_BROWSERS_PATH`).

The prefix tests pass if no template has a fixed path. If one fails, the list in the assertion
names the path: replace it with `{% url %}`/`{% static %}` in the template that produced it, and
commit that fix with this task.

- [ ] **Step 3: Add to `.env.example`** (depois de `SCPI_PERFIL_DIR`):

```
# Pasta do Chromium do Playwright, comum ao serviço e às tarefas agendadas (vazio = a pasta do
# usuário que rodou "playwright install"). Instale com a mesma variável definida no terminal.
PLAYWRIGHT_BROWSERS_PATH=
```

- [ ] **Step 4: Write `deploy/INSTALACAO.md`**

Escrito para o André, em seções numeradas, com os comandos em blocos `bat`.

1. **Requisitos.**
   - Windows Server com Git, Python 3.13 e uv (`winget`/instalador oficial).
   - NSSM no `PATH`.
   - O MySQL/MariaDB do ProducaoLab e o `mysqldump` (ou `mariadb-dump`) dele.
2. **Conta e pasta.**
   - Uma conta local dedicada (ex.: `svc-almoxarifado`), que roda o serviço e as tarefas.
   - Clone em `C:\CentralAlmoxarifado`. O caminho não pode ter espaços: os `.bat` e o
     Agendador dependem disso.
   - Permissão de escrita da conta em `logs\`, `.pw-profile\`, `staticfiles\` e na pasta de
     backup.
3. **Banco.** O SQL do README sem o `GRANT` do `test_almoxarifado`, com senha forte.
4. **`.env` de produção.** Cada variável do `.env.example`, com o valor de produção:
   - `DEBUG=0`, `SECRET_KEY` gerada, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` com esquema;
   - `USAR_HTTPS` e `PROXY_HTTPS` conforme o Apache;
   - `SCPI_HEADLESS=1` (sem janela, rodando como serviço);
   - `LANCAMENTO_REAL=0` até a virada;
   - `PLAYWRIGHT_BROWSERS_PATH=C:\CentralAlmoxarifado-navegadores`;
   - `BACKUP_DIR` e `MYSQLDUMP`;
   - Telegram e SCPI.
5. **Instalação.**
   - `uv sync --frozen --no-dev`;
   - `set PLAYWRIGHT_BROWSERS_PATH=...` e `.venv\Scripts\python.exe -m playwright install chromium`;
   - `migrate`, `collectstatic --noinput`, `createsuperuser`;
   - `check --deploy --fail-level WARNING` sem avisos.
6. **Serviço (NSSM).**
   - `nssm install CentralAlmoxarifado "C:\CentralAlmoxarifado\.venv\Scripts\python.exe"`.
   - `nssm set CentralAlmoxarifado AppParameters "-m waitress --listen=127.0.0.1:8010 --threads=8 --trusted-proxy=127.0.0.1 --trusted-proxy-headers=\"x-forwarded-proto x-forwarded-for\" config.wsgi:application"`.
     Sem Apache, use `--listen=0.0.0.0:8010` e tire as opções de proxy.
   - `AppDirectory C:\CentralAlmoxarifado`.
   - `ObjectName .\svc-almoxarifado <senha>`.
   - `AppStdout`/`AppStderr` em `logs\servico.log`.
   - `AppKillProcessTree 0`, para o reinício não matar o robô disparado pela página (Decisão 11).
   - `Start SERVICE_AUTO_START`.
7. **Apache.**
   - Em `/almoxarifado` (o padrão): acrescente `--url-prefix=/almoxarifado` aos `AppParameters` e
     use `ProxyPass /almoxarifado http://127.0.0.1:8010/almoxarifado`. Os formulários ficam em
     `servidor/almoxarifado/` e a área interna em `servidor/almoxarifado/painel/`.
   - Se um dia houver um nome próprio na rede: tire o `--url-prefix` e use
     `ProxyPass / http://127.0.0.1:8010/`.
   - Nos dois casos:
     - `ProxyPreserveHost On` (o link "Abrir painel" do Telegram usa o host da requisição);
     - `RequestHeader set X-Forwarded-Proto "https"` com HTTPS;
     - `PROXY_HTTPS=1`.
   - Sem `--trusted-proxy-headers`, todo pedido divide o mesmo limite por IP.
8. **Agendador de Tarefas.** Três comandos `schtasks /Create`, rodando como a conta do serviço
   com "executar estando o usuário conectado ou não" (`/RU .\svc-almoxarifado /RP *`):

   ```bat
   schtasks /Create /TN "Central Almoxarifado\Estoque" /TR "C:\CentralAlmoxarifado\deploy\tarefa.bat importar_estoque" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:00 /RI 30 /DU 10:01 /RU .\svc-almoxarifado /RP *
   schtasks /Create /TN "Central Almoxarifado\Catalogo" /TR "C:\CentralAlmoxarifado\deploy\tarefa.bat atualizar_catalogo" /SC DAILY /ST 06:30 /RU .\svc-almoxarifado /RP *
   schtasks /Create /TN "Central Almoxarifado\Backup" /TR "C:\CentralAlmoxarifado\deploy\tarefa.bat backup_banco" /SC DAILY /ST 23:00 /RU .\svc-almoxarifado /RP *
   ```

   O resultado das importações aparece em Almoxarifado › Catálogo; a saída de cada tarefa, em
   `logs\agendador.log`.
9. **Backup e restauração.**
   - Onde ficam os arquivos e a retenção de 60 dias.
   - Restauração em dois comandos:
     `.venv\Scripts\python.exe -c "import gzip,shutil,sys; shutil.copyfileobj(gzip.open(sys.argv[1]), open(sys.argv[2], 'wb'))" <arquivo>.sql.gz restaurar.sql`
     e `mysql -u almox -p almoxarifado < restaurar.sql` (no `cmd.exe`).
   - Teste a restauração num banco vazio uma vez depois de instalar.
10. **Atualização.** Rode `deploy\atualizar.bat` como administrador. Ele para se houver robô em
    andamento.
11. **Conferência depois de instalar.**
    - O login abre.
    - "Atualizar agora" no Catálogo termina sem erro.
    - "Simular" em Lançamentos SCPI abre o SCPI headless e termina.
    - `deploy\tarefa.bat backup_banco` gera o arquivo.
    - As três tarefas aparecem no Agendador.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_prefixo.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add deploy/INSTALACAO.md .env.example tests/test_prefixo.py tests/test_config.py
git commit -m "Guia de instalação no servidor e Apache em /almoxarifado"
```

---

### Task 9: Roteiro da migração e da virada; documentação do projeto

**Files:**
- Create: `deploy/VIRADA.md`
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: `importar_planilhas` (Task 4), `LANCAMENTO_REAL` (Task 1), a área interna em
  `/painel/` (Task 7), `deploy/INSTALACAO.md` (Task 8).

- [ ] **Step 1: Write `deploy/VIRADA.md`**

Um roteiro com caixas de seleção, na ordem da spec (seção 8). Cada passo diz quem faz.

1. **Instalação** (André, `INSTALACAO.md`), com `LANCAMENTO_REAL=0`.
2. **Carga inicial do catálogo** (João; Decisão 7):
   - o cadastro completo por CSV enviado (Catálogo › Cadastro, recarga completa);
   - `importar_estoque`;
   - `importar_saidas_scpi --desde <primeiro dia do histórico que a curva ABC usa>`.
3. **Primeira importação das planilhas:**
   - "Arquivo › Fazer download › Microsoft Excel (.xlsx)" da planilha do sistema;
   - `importar_planilhas --arquivo <xlsx> --dry-run`;
   - corrigir na planilha cada erro listado (em geral, "Concluir transferência" no Apps Script
     ou marcar NÃO LANÇAR). Os avisos são lidos e aceitos;
   - por fim, `importar_planilhas --arquivo <xlsx>`.
4. **Período em paralelo** (pelo menos uma semana de lançamentos):
   - o Apps Script continua sendo o sistema em uso;
   - a cada conferência, reexportar e reimportar. A importação substitui tudo;
   - no Django, conferir os números, a situação e a situação no SCPI de cada pedido no painel
     contra o painel antigo;
   - usar "Simular" em Lançamentos SCPI e comparar os lotes simulados com o que o robô antigo
     lançou;
   - nenhum pedido é feito direto no Django. Se for feito, a reimportação recusa até ele ser
     apagado no admin.
5. **Virada**, fora do expediente:
   1. Esvaziar as pendências do robô antigo: `lancar_saidas.py` até não restar linha pendente e
      cada "VERIFICAR NO SCPI"/"EM LANÇAMENTO" conferido.
   2. Importação final: exportar, `--dry-run` e importar.
   3. Desativar a implantação do Apps Script e trocar o `doGet` (`AS:apps-script/WebApp.gs`) por
      uma página que aponta para o endereço novo:
      ```js
      function doGet() {
        return HtmlService.createHtmlOutput(
          '<p>O Central Almoxarifado mudou de endereço: <a href="https://ENDERECO-NOVO/" target="_top">abrir</a>.</p>'
        ).setTitle('Central Almoxarifado');
      }
      ```
      Depois de publicar, conferir que o último Nº da planilha é o importado. Se entrou pedido
      no intervalo, repetir o passo 2.
   4. Liberar o lançamento real: `LANCAMENTO_REAL=1` no `.env`, `nssm restart
      CentralAlmoxarifado`, e o primeiro lançamento com "Executar com opções", limite 1,
      conferido no SCPI.
   5. Arquivar o repositório: `gh repo archive <dono>/CentralAlmoxarifado`.
6. **Depois da virada:**
   - `importar_planilhas` não roda mais (recusa com `LANCAMENTO_REAL=1`);
   - mudança de modelo passa a ter migration nova, nunca regenerada.

- [ ] **Step 2: Update `README.md`.** Uma seção "Implantação" aponta para
  `deploy/INSTALACAO.md` e `deploy/VIRADA.md` e cita `LANCAMENTO_REAL`, `backup_banco` e
  `importar_planilhas`. O item 6 (lançamento) avisa que, sem `LANCAMENTO_REAL=1`, só a simulação
  roda. A área do almoxarifado passa de `/almoxarifado/` para `/painel/` em "O que tem".

- [ ] **Step 3: Update `CLAUDE.md`.**
  - "O projeto": o subprojeto 5 tem código feito; falta a execução da virada (`deploy/VIRADA.md`).
  - "Arquitetura": o login passa a ser `/painel/entrar/`, e um item novo explica que a área
    interna fica em `/painel/` e o site sai atrás do Apache em `/almoxarifado` (`--url-prefix`).
  - "Comandos": `importar_planilhas --arquivo <xlsx> [--dry-run]`, `backup_banco` e
    `robos_em_andamento`.
  - "Arquitetura": um item para `implantacao` (Decisões 1, 3, 5, 6 e 11, em uma linha cada) e
    um para `LANCAMENTO_REAL` (comando, página e painel; `settings_test` ligado).
  - "Convenções": a regra das migrations regeneradas vale até a importação das planilhas no
    servidor; depois, migration nova.

- [ ] **Step 4: Full verification**

Run: `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run python manage.py makemigrations --check --dry-run`
Expected: all pass; `No changes detected`.

- [ ] **Step 5: Commit**

```bash
git add deploy/VIRADA.md README.md CLAUDE.md
git commit -m "Roteiro da migração e da virada; documentação do subprojeto 5"
```

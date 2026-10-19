# Edição do atendimento — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir reabrir e corrigir o atendimento de um pedido (ou uma saída avulsa) até o robô
lançar o lote no SCPI, com histórico, concorrência otimista e bloqueio depois do lançamento.

**Architecture:** Regras puras novas em `pedidos/regras.py` (estado da edição e diferenças);
dois serviços novos em `pedidos/servicos.py` (`editar_atendimento`, `editar_saida_avulsa`) que
travam o pedido e as linhas, conferem a versão e recriam as `LinhaSaida` com IDs novos; uma rota
`pedidos:editar` que reaproveita o formulário de atendimento (`detalhe.html`) e o da saída avulsa
(`avulsa.html`) com o modo `editando`.

**Tech Stack:** Django 5, MariaDB/MySQL (pytest contra o banco real), HTMX 4, JavaScript sem
build (`pedidos.js`), design system Clean (`docs/DESIGN.md`).

**Spec:** `docs/superpowers/specs/2026-10-17-edicao-pedido-design.md` (ler inteira antes de
começar; as seções citadas abaixo são dela).

## Global Constraints

- Nomes de código, textos de interface, mensagens e commits em português (pt-BR).
- O servidor está em produção: mudança de modelo ganha **migration nova** em `pedidos`
  (`0002_…`), nunca regenerar a `0001_initial`; sem operação sobre dados.
- `servicos.py` continua o único lugar que grava em `pedidos` (o robô só mexe nos quatro campos
  de `LinhaSaida` de sempre).
- As linhas de saída nunca são atualizadas no lugar na edição: apagadas e recriadas pelo
  `_gravar_linhas` (IDs novos).
- O que veio do funcionário (solicitante, destino, observação do pedido, a lista de materiais
  `PEDIDO` e `qtd_pedida`) nunca muda, mesmo que o POST traga esses campos.
- Estado nunca só por cor; códigos em `.mono`; requisição HTMX que grava vai dentro de `<form>`
  com `{% csrf_token %}`; scripts só no `<head>` com `defer`; nenhum caminho fixo em template
  (`tests/test_prefixo.py`).
- Ajuste de UI usa as skills `clean-design` (com `docs/DESIGN.md`, que vence), `ui-ux-pro-max` e
  `frontend-design`, sem refazer o questionário da `clean-design`.
- Comandos: `uv run pytest`, `uv run ruff check . && uv run ruff format --check .`,
  `uv run python manage.py makemigrations --check --dry-run`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Edição que zera todas as quantidades entregues: recusa "ao menos um material", nada gravado
   (teste na Task 4).
2. Lote `NAO_LANCAR` editado com "Não lançar" desmarcado: as linhas viram `PENDENTE` e o lote
   aparece em `consultas.fila_do_robo` (teste na Task 4).
3. Duas pessoas salvando o mesmo pedido ao mesmo tempo (`em_paralelo`): uma grava, a outra recebe
   `motivo="versao"`, e as linhas não duplicam (teste na Task 4).
4. Pedido AB editado com quantidade decimal ("1,5"): recusa pela regra do inteiro (teste na
   Task 4).
5. Lote `ERRO` com `requisicao_scpi` vazio e `lancado_em` preenchido por engano: a edição recria
   as linhas sem número nem data de lançamento (teste na Task 4).

---

### Task 1: Modelo e migration

**Files:**
- Modify: `pedidos/models.py` (classe `Pedido`; novo modelo `AlteracaoPedido` depois de `Atendimento`)
- Create: `pedidos/migrations/0002_edicao_atendimento.py` (gerada pelo `makemigrations`)
- Modify: `pedidos/admin.py` (registrar `AlteracaoPedido` só leitura)
- Test: `tests/test_modelos_pedidos.py`

**Interfaces:**
- Produces: `Pedido.versao: int` (default 0); `AlteracaoPedido(pedido, usuario, em, versao,
  diferencas: list[dict], scpi_antes: list[dict])`, `related_name="alteracoes"`, ordem `-em`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pedido_nasce_na_versao_zero():
    assert criar_pedido().versao == 0

def test_alteracao_guarda_diferencas_e_scpi_antes():
    p = criar_pedido(atendido=True)
    u = get_user_model().objects.create_user(username="00001")
    a = AlteracaoPedido.objects.create(
        pedido=p, usuario=u, versao=1,
        diferencas=[{"campo": "Recebedor", "antes": "João", "depois": "Ana"}],
        scpi_antes=[{"seq": 1, "status": "PENDENTE", "mensagem": "", "requisicao_scpi": ""}],
    )
    assert list(p.alteracoes.all()) == [a] and a.diferencas[0]["depois"] == "Ana"

def test_migration_da_edicao_so_acrescenta():
    from importlib import import_module
    from django.db.migrations import AddField, CreateModel
    m = import_module("pedidos.migrations.0002_edicao_atendimento").Migration
    assert {type(op) for op in m.operations} <= {AddField, CreateModel}
```

- [ ] **Step 2: Run** `uv run pytest tests/test_modelos_pedidos.py -k "versao or alteracao or migration_da_edicao" -v` — Expected: FAIL (`versao`/`AlteracaoPedido` não existem).

- [ ] **Step 3: Implement** `Pedido.versao = models.PositiveIntegerField(default=0)` e o
  `AlteracaoPedido` da spec §3 (`usuario` `PROTECT` para `settings.AUTH_USER_MODEL`; `em`
  `default=timezone.now`; `diferencas` e `scpi_antes` `JSONField(default=list)`;
  `verbose_name="alteração do pedido"`). Gerar a migration com
  `uv run python manage.py makemigrations pedidos --name edicao_atendimento`. No admin, `AlteracaoPedido`
  com `has_add_permission`/`has_change_permission`/`has_delete_permission` falsos, como o das
  importações.

- [ ] **Step 4: Run** os testes do Step 2 e `uv run python manage.py makemigrations --check --dry-run` — Expected: PASS e "No changes detected".

- [ ] **Step 5: Commit** — `git commit -m "Pedidos: versão do pedido e histórico de alterações (migration nova)"`

---

### Task 2: Regras puras da edição

**Files:**
- Modify: `pedidos/regras.py` (nova seção "Edição do atendimento", depois de "Situação do pedido e no SCPI")
- Test: `tests/test_regras_edicao.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class Edicao:
    chave: str          # "antes_do_atendimento" | "editavel" | "suspensa" | "bloqueada"
    motivo: str         # texto da tela (spec §2); vazio em "editavel"
    numeros: tuple[str, ...] = ()
    lancado_em: datetime | None = None
    @property
    def permitida(self) -> bool: ...   # chave == "editavel"

def edicao_permitida(atendido: bool, linhas) -> Edicao
    # linhas: objetos com status, requisicao_scpi, lancado_em

ROTULOS_CABECALHO = ("Data efetiva", "Recebedor", "Centro de custo", "Tipo de saída",
                     "Placa", "Observações", "Não lançar no SCPI")

@dataclass(frozen=True)
class EstadoAtendimento:
    cabecalho: tuple[str, ...]                        # ordem de cabecalho_saida
    entregues: dict[str, Decimal | None]              # itens PEDIDO; na avulsa, todos
    adicionados: dict[str, tuple[str, Decimal | None]]  # código -> (no_lugar_de, qtd)
    nomes: dict[str, str]                             # código -> material, para as frases

def diferencas_atendimento(gravado: EstadoAtendimento, enviado: EstadoAtendimento) -> list[dict]
def frase_diferenca(d: dict) -> str
```

Formato das diferenças (vai para o `JSONField`, então só `str`): cabeçalho
`{"campo": ROTULOS_CABECALHO[i], "antes": str, "depois": str}` (no "Não lançar", "Sim"/"Não";
na data, `dd/mm/aaaa`); material `{"codigo", "material", "mudanca", "antes", "depois"}` com
`mudanca` em `"entregue"` (quantidade mudou), `"incluido"` (só no enviado), `"removido"` (só no
gravado), `"troca"` (acrescentado com outro `no_lugar_de`). Quantidades por `qtd_br`; ausente
como `""`. Ordem: cabeçalho, entregues, acrescentados (na ordem do enviado, removidos no fim).

- [ ] **Step 1: Write the failing tests**

```python
def linha(status, req="", lancado=None):
    return SimpleNamespace(status=status, requisicao_scpi=req, lancado_em=lancado)

@pytest.mark.parametrize("linhas, chave", [
    ([linha("PENDENTE")], "editavel"),
    ([linha("NAO_LANCAR")], "editavel"),
    ([linha("ERRO")], "editavel"),
    ([linha("PENDENTE"), linha("EM_LANCAMENTO")], "suspensa"),
    ([linha("VERIFICAR")], "suspensa"),
    ([linha("LANCADA", "000123/26")], "bloqueada"),
    ([linha("PENDENTE"), linha("LANCADA", "000123/26")], "bloqueada"),
    ([linha("PENDENTE", "000123/26")], "bloqueada"),
])
def test_edicao_permitida_pelas_linhas(linhas, chave):
    assert edicao_permitida(True, linhas).chave == chave

def test_sem_atendimento_nao_ha_edicao():
    assert edicao_permitida(False, []).chave == "antes_do_atendimento"

def test_bloqueada_diz_requisicao_e_data():
    quando = datetime(2026, 10, 16, 15, 40)
    e = edicao_permitida(True, [linha("LANCADA", "004213/26", quando)])
    assert e.numeros == ("004213/26",) and not e.permitida
    assert e.motivo == ("Lançado na requisição 004213/26 em 16/10/2026 15:40; correções são "
                        "feitas no SCPI.")

def test_diferencas_vazias_quando_nada_muda():
    assert diferencas_atendimento(ESTADO, ESTADO) == []

def test_diferencas_do_cabecalho_entregue_troca_e_acrescimo():
    enviado = replace(ESTADO,
        cabecalho=("2026-10-09", "Ana", "ETA II", "BALCÃO", "", "", "1"),
        entregues={"023.001.002": Decimal(1), "008.001.002": Decimal("0")},
        adicionados={"023.004.001": ("008.001.002", Decimal(2))})
    assert diferencas_atendimento(ESTADO, enviado) == [
        {"campo": "Recebedor", "antes": "João", "depois": "Ana"},
        {"campo": "Não lançar no SCPI", "antes": "Não", "depois": "Sim"},
        {"codigo": "023.001.002", "material": "DETERGENTE NEUTRO", "mudanca": "entregue",
         "antes": "2", "depois": "1"},
        {"codigo": "008.001.002", "material": "CAFÉ 500 G", "mudanca": "entregue",
         "antes": "1,5", "depois": "0"},
        {"codigo": "023.004.001", "material": "PAPEL HIGIÊNICO", "mudanca": "incluido",
         "antes": "", "depois": "2"},
    ]

def test_acrescentado_removido_e_troca_desfeita(): ...  # mudanca "removido" e "troca"

def test_frase_diferenca():
    assert frase_diferenca({"campo": "Recebedor", "antes": "João", "depois": "Ana"}) == \
        "Recebedor: João → Ana"
    assert frase_diferenca({"codigo": "023.001.002", "material": "DETERGENTE NEUTRO",
        "mudanca": "entregue", "antes": "2", "depois": "1"}) == \
        "DETERGENTE NEUTRO (023.001.002): entregue 2 → 1"
```

`ESTADO` é um `EstadoAtendimento` de módulo com cabeçalho `("2026-10-09", "João", "ETA II",
"BALCÃO", "", "", "")`, entregues `{"023.001.002": Decimal(2), "008.001.002": Decimal("1.5")}`,
sem acrescentados e `nomes` dos três códigos do `tests/cenario.py`. Frases dos demais tipos:
`"<material> (<código>): incluído, <depois>"`, `"<material> (<código>): removido (era <antes>)"`,
`"<material> (<código>): agora no lugar de <nome do trocado>"` / `"…: deixou de ser troca"`.

Textos de `motivo` (spec §2): `suspensa` → `"Edição suspensa: o robô não confirmou se a
requisição foi gravada no SCPI. Resolva em Automações."`; `antes_do_atendimento` → `""`.

- [ ] **Step 2: Run** `uv run pytest tests/test_regras_edicao.py -v` — Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** as funções acima em `pedidos/regras.py` (sem ORM). Na bloqueada, `lancado_em` é o maior entre as linhas, em hora local.
- [ ] **Step 4: Run** `uv run pytest tests/test_regras_edicao.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Regras: estado da edição do atendimento e diferenças"`

---

### Task 3: Validação comum do atendimento e estados gravado/enviado

Refatoração sem mudança de comportamento: a suíte do atendimento continua verde.

**Files:**
- Modify: `pedidos/servicos.py` (`confirmar_atendimento`, linhas ~475-587)
- Test: `tests/test_editar_atendimento.py` (criar; só os testes de estado aqui)

**Interfaces:**
- Consumes: `EstadoAtendimento`, `cabecalho_saida` (regras).
- Produces:

```python
def _validar_atendimento(
    pedido: Pedido, itens: list[ItemPedido], dados: DadosSaida, parsed: dict,
    adicionados: list[Adicionado], qtds_adicionadas: dict[str, Decimal | None],
    nao_lancar: bool, *, hoje: date, catalogo_extra: dict[str, ItemCatalogo] | None = None,
) -> tuple[list[Adicionado], dict[str, ItemCatalogo], list[Erro]]
    # devolve os acrescentados únicos, o catálogo usado (avulsa + extra) e os erros

def estado_gravado(pedido: Pedido) -> EstadoAtendimento
def estado_enviado(pedido: Pedido, dados: DadosSaida, nao_lancar: bool, parsed: dict,
                   adicionados: list[Adicionado], qtds_adicionadas: dict) -> EstadoAtendimento
```

`catalogo_extra` entra por cima do catálogo da avulsa (é como a edição aceita acrescentado
gravado e oculto). Em `estado_gravado`, `entregues` vem dos itens `PEDIDO` (`qtd_entregue`),
`adicionados` dos `ALMOXARIFADO` (`no_lugar_de` pelo código do item trocado) e o cabeçalho de
`cabecalho_atendimento`. Na avulsa, `entregues` são todos os itens e `adicionados` é vazio.

- [ ] **Step 1: Write the failing tests** — `test_estado_gravado_de_um_atendimento_com_troca` (atende com `adicionados=[Adicionado("023.004.001", "008.001.002")]` e confere `entregues`, `adicionados == {"023.004.001": ("008.001.002", Decimal(1))}` e o cabeçalho) e `test_estado_enviado_igual_ao_gravado_nao_tem_diferencas`.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement** — mover o miolo de validação do `confirmar_atendimento` (de `lista_centros, tipos, dia = …` até `erros_extras_da_saida`) para `_validar_atendimento`; o `confirmar_atendimento` passa a chamá-la. Escrever `estado_gravado` e `estado_enviado`.
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_atendimento.py tests/test_atendimento_adicionados.py -v` — Expected: PASS (nenhum teste antigo muda).
- [ ] **Step 5: Commit** — `git commit -m "Atendimento: validação comum e estado gravado/enviado"`

---

### Task 4: Serviço `editar_atendimento`

**Files:**
- Modify: `pedidos/servicos.py` (`Resposta`; novo `editar_atendimento` depois de `confirmar_atendimento`)
- Test: `tests/test_editar_atendimento.py`, `tests/test_lancamento.py`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces:

```python
# Resposta ganha:
motivo: str = ""                # "lancamento" | "versao" | ""
diferencas: list[dict] = field(default_factory=list)

def editar_atendimento(
    pedido_id: uuid.UUID, versao: int, dados: DadosSaida, qtds: dict[str, str], *,
    nao_lancar: bool, adicionados: Sequence[Adicionado] = (), usuario, hoje: date | None = None,
) -> Resposta
```

Ordem e textos exatos (spec §3, "Serviço"):
1. `Pedido` com `select_for_update`; sem atendimento ou `AVULSA` → `"Pedido não encontrado."`.
2. Linhas com `select_for_update`; fora de `editavel` → `ok=False, motivo="lancamento"`,
   `mensagem=edicao.motivo`, `diferencas` calculadas.
3. `versao != pedido.versao`: diferenças vazias → `ok=True, reenvio=True`; senão `ok=False,
   motivo="versao"`, `mensagem=f"{nome} salvou alterações neste pedido às {hh:mm}."` (nome =
   `get_full_name() or username` da última `AlteracaoPedido`).
4. `_validar_atendimento` com `catalogo_extra` = acrescentados gravados cujo `(codigo,
   no_lugar_de)` continua igual no envio (`ItemCatalogo` montado do `ItemPedido`: nome, unidade,
   grupo, subgrupo, `estoque=0`, `disponivel=0`, `duplicado=False`, `categoria=""`). Antes da
   validação comum, para centro de custo, tipo de saída e placa: se o valor enviado é igual ao
   gravado e não está mais nas opções (`centros()`, `tipos_saida()`), acrescentar
   `Erro(None, f"{rótulo}: o valor gravado não existe mais. Escolha outro.")` (rótulo de
   `ROTULOS_CABECALHO`). Erros → `mensagem="Corrija os dados da saída."`.
5. Diferenças vazias → `ok=True, mensagem="Nada mudou; nada foi gravado."`, nada gravado.
6. Gravar (spec §3 passo 6), `AlteracaoPedido(versao=pedido.versao + 1, diferencas,
   scpi_antes=[{"seq","status","mensagem","requisicao_scpi"} das linhas antigas])`.
7. `LinhaSaida` do atendimento: `delete()`, `_gravar_linhas(...)`, e `update(mensagem=f"Refeita na
   edição de {dd/mm/aaaa hh:mm} por {usuario.username}.")` nas novas.
   Sucesso → `ok=True, mensagem=f"Alterações salvas no pedido {numero}.", diferencas`.

"Não lançar" vindo do `resolver_lote` (spec §3): quem preenche o formulário é a view (Task 8);
o serviço só grava o `nao_lancar` recebido.

- [ ] **Step 1: Write the failing tests** em `tests/test_editar_atendimento.py`, com um fixture `atendido` (pedido de limpeza do cenário atendido com `TUDO`, `hoje=HOJE`) e o helper `editar(pedido, usuario, versao=0, dados=None, qtds=None, **kw)`:
  - `test_edicao_grava_entregas_recria_linhas_e_registra` — muda `"008.001.002"` para `"1"`; `r.ok`; `Pedido.versao == 1`; IDs das linhas todos novos; `qtd` da linha nova `Decimal("1")`; uma `AlteracaoPedido` com a diferença; `mensagem` começa por `"Refeita na edição de"`.
  - `test_edicao_zera_recibo_impresso`.
  - `test_edicao_nao_muda_cabecalho_nem_qtd_pedida` — mesmo com `qtds` trazendo código desconhecido e o pedido intacto (`solicitante`, `destino`, `obs`, `qtd_pedida`).
  - `test_sem_mudanca_nao_grava_nada` — `versao` continua 0, nenhuma alteração, IDs das linhas iguais.
  - `test_recusas_da_validacao` — data futura, centro inexistente, trocado com quantidade > 0.
  - Review Focus 1: `test_zerar_tudo_recusa_ao_menos_um_material`.
  - `@pytest.mark.parametrize` por status: `PENDENTE`/`NAO_LANCAR`/`ERRO` editam; `EM_LANCAMENTO`, `VERIFICAR`, `LANCADA`, número de requisição recusam com `motivo == "lancamento"` e linhas intactas.
  - `test_erro_volta_a_pendente` e, Review Focus 5, `test_erro_com_lancado_em_volta_sem_data_nem_numero`.
  - Review Focus 2: `test_desmarcar_nao_lancar_poe_o_lote_na_fila` (`consultas.fila_do_robo` contém o lote).
  - `test_versao_diferente_recusa_com_quem_salvou` e `test_reenvio_igual_com_versao_antiga_e_sucesso`.
  - Review Focus 3: `test_duas_edicoes_ao_mesmo_tempo` (`@pytest.mark.django_db(transaction=True)`, `em_paralelo`): um `ok`, outro `motivo == "versao"`, `LinhaSaida.objects.count()` igual ao de uma edição.
  - Review Focus 4: `test_ab_recusa_decimal`.
  - `test_acrescentado_oculto_inalterado_e_aceito` (acrescenta `"023.004.001"`, oculta o `Material`, edita só o recebedor) e `test_acrescentado_oculto_novo_e_recusado`.
  - `test_valor_gravado_que_sumiu_diz_que_nao_existe_mais` (apaga o `CentroCusto` "ETA II").
  - `test_scpi_antes_guarda_a_situacao_anterior`.
- Em `tests/test_lancamento.py`:
  - `test_edicao_entre_a_leitura_e_a_trava_faz_o_robo_pular_o_lote(dois_lotes, scpi, monkeypatch)` — envolve `scpi.preencher` para, no lote `P-`, chamar `editar_atendimento` (muda o recebedor) antes de seguir; o resumo tem `ignoradas == 1` para ele; numa segunda `executar_lancamento`, o lote sai `LANCADA` com o recebedor novo.
  - `test_robo_trava_antes_e_a_edicao_e_recusada(dois_lotes, scpi, monkeypatch)` — envolve `scpi.salvar` para chamar `editar_atendimento` antes de devolver o número: `motivo == "lancamento"`; o lote termina `LANCADA` com o conteúdo antigo.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_lancamento.py -v` — Expected: os novos FAIL.
- [ ] **Step 3: Implement** `editar_atendimento` e os campos novos da `Resposta`.
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_lancamento.py tests/test_atendimento.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Atendimento: edição até o lançamento no SCPI"`

---

### Task 5: Serviço `editar_saida_avulsa`

**Files:**
- Modify: `pedidos/servicos.py`
- Test: `tests/test_editar_atendimento.py`

**Interfaces:**
- Consumes: Tasks 1-4 (mesmas travas, versão, diferenças e recriação de linhas; extrair o que
  for comum com `editar_atendimento` para `_conferir_edicao(pedido, enviado) -> Resposta | None`
  e `_gravar_edicao(pedido, atendimento, pares, diferencas, usuario)`).
- Produces: `editar_saida_avulsa(pedido_id: uuid.UUID, versao: int, envio: EnvioSaida, *, usuario, hoje: date | None = None) -> Resposta`

Validação igual à do `registrar_saida_avulsa` (o miolo vira `_validar_saida_avulsa(envio, *,
hoje, catalogo)`), com o catálogo da avulsa mais os itens gravados (como `catalogo_extra`).
Gravação: apaga os `ItemPedido` e recria pelo carrinho (`qtd_pedida = qtd_entregue`), atualiza o
atendimento, recria as linhas. Só aceita `origem == AVULSA` (senão "Pedido não encontrado.").

- [ ] **Step 1: Write the failing tests** — `test_avulsa_edita_quantidade_e_inclui_material`, `test_avulsa_remove_material` (diferença `"removido"`), `test_avulsa_lancada_recusa`, `test_avulsa_sem_material_recusa` ("Adicione ao menos um material."), `test_editar_atendimento_recusa_avulsa_e_vice_versa`.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -k avulsa -v` — Expected: FAIL.
- [ ] **Step 3: Implement** `editar_saida_avulsa` e as extrações.
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_saida_avulsa.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Saída avulsa: edição até o lançamento no SCPI"`

---

### Task 6: Confirmação de impresso conferindo a versão

**Files:**
- Modify: `pedidos/servicos.py:667` (`marcar_recibos_impressos`), `pedidos/views/almoxarifado.py:384` (`marcar_impressos`), `pedidos/templates/pedidos/detalhe.html:23-29`
- Test: `tests/test_recibos.py`

**Interfaces:**
- Produces: `marcar_recibos_impressos(atendimento_ids, agora=None, versoes: dict[uuid.UUID, int] | None = None) -> int` — sem `versoes`, como hoje; com, ignora o atendimento cujo `pedido.versao` difere.

O formulário manda `versao` junto do `atendimento`. A view, quando o único atendimento enviado é
ignorado pela versão, dá `messages.warning(request, "O pedido foi alterado depois de abrir esta
página; imprima de novo.")`.

- [ ] **Step 1: Write the failing tests** — `test_marcar_impresso_com_versao_antiga_e_ignorado` (serviço devolve 0, `recibo_impresso_em` continua nulo) e `test_view_avisa_quando_o_pedido_mudou` (POST com `versao=0` num pedido na versão 1 → mensagem acima).
- [ ] **Step 2: Run** `uv run pytest tests/test_recibos.py -v` — Expected: FAIL nos novos.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/test_recibos.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Recibos: confirmação de impresso confere a versão do pedido"`

---

### Task 7: Detalhe em leitura — botão, avisos e histórico

**Files:**
- Modify: `pedidos/views/almoxarifado.py` (`_contexto_detalhe`), `pedidos/templates/pedidos/detalhe.html` (bloco `tools` e topo do `page`)
- Create: `pedidos/templates/pedidos/_alteracoes.html`
- Modify: `pedidos/templatetags/pedidos_extras.py` (filtro `frase_diferenca`, que chama a de `regras`)
- Test: `tests/test_editar_atendimento.py`

**Interfaces:**
- Consumes: `edicao_permitida`, `frase_diferenca`, `AlteracaoPedido`.
- Produces: no contexto do detalhe, `edicao: Edicao` e `alteracoes` (queryset com `usuario`).

Textos (spec §4): botão "Editar atendimento" (avulsa: "Editar saída"), `botao-secundario`, com
ícone `lapis`, link para `pedidos:editar`; em `suspensa`/`bloqueada`, `<button
aria-disabled="true">` com ícone `cadeado` e `title`/dica igual a `edicao.motivo`. Aviso
`editavel`: "Pode ser editado até o robô lançar no SCPI." + com recibo impresso " Salvar
alterações devolve o recibo para impressão." + com lote `ERRO` " Corrija e salve: o lote volta
para a fila do próximo lançamento." Bloco `<details class="nao-imprimir">` "Alterações depois do
atendimento", uma linha por alteração: `dd/mm/aaaa hh:mm · <nome>` e as frases; sem nenhuma,
"Nenhuma alteração registrada." Sem atendimento, nada disso aparece.

- [ ] **Step 1: Write the failing tests** — `test_detalhe_mostra_editar_quando_editavel` (link para `reverse("pedidos:editar", args=[numero])`), `test_detalhe_desabilita_editar_quando_lancado` (`aria-disabled="true"` e o texto da requisição), `test_detalhe_suspenso_mostra_motivo`, `test_detalhe_sem_atendimento_nao_tem_editar`, `test_historico_no_detalhe_e_fora_do_recibo` (a frase está no HTML e fora do `<article class="folha-recibo">`), `test_aviso_de_recibo_impresso`.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -k detalhe -v` — Expected: FAIL (a rota `pedidos:editar` pode ser declarada já aqui apontando para a view da Task 8 com um `Http404` provisório, para o `reverse` funcionar).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_recibos.py tests/test_prefixo.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Detalhe: botão de editar, avisos e histórico de alterações"`

---

### Task 8: Modo de edição do pedido (rota e template)

**Files:**
- Modify: `pedidos/urls.py` (`path("painel/pedidos/<str:numero>/editar/", almoxarifado.editar, name="editar")`)
- Modify: `pedidos/views/almoxarifado.py` (`editar`, `_contexto_edicao`, `_pedido_pendente` → `_pedido_com_atendimento_aberto`)
- Modify: `pedidos/templates/pedidos/detalhe.html` (form com `action` e rótulos do modo; faixa; recusas)
- Test: `tests/test_editar_atendimento.py`

**Interfaces:**
- Consumes: `editar_atendimento` (Task 4), `edicao_permitida`, `frase_diferenca`.
- Produces: view `editar(request, numero)` (GET e POST; na avulsa delega à Task 9); contexto
  `editando=True`, `versao`, `form_acao` (URL do POST: `pedidos:atender` no atendimento,
  `pedidos:editar` na edição), `rotulo_enviar`.

Comportamento:
- GET fora de `editavel` → `redirect("pedidos:detalhe")` com `messages.info(edicao.motivo)`.
- GET `editavel` → `_contexto_detalhe(pedido, atendivel=True, editando=True, …)` com `campos`
  do atendimento (data iso, recebedor, centro, placa, obs; `tipo` como hoje), `entregues` pelo
  `_formatar_qtd` de `qtd_entregue`, `adicionados` montados dos `ALMOXARIFADO` gravados (nome e
  unidade do `ItemPedido`, não do catálogo), `nao_lancar = atendimento.nao_lancar or` todas as
  linhas ativas `NAO_LANCAR`.
- POST → `editar_atendimento` com os mesmos campos que o `atender` lê. `ok` → redirect ao detalhe
  com `messages.success` da mensagem e, havendo diferenças, as frases; se o recibo estava
  impresso, acrescentar "O recibo voltou para impressão." `motivo="lancamento"` → render com
  `bloqueado_no_salvar=True` (formulário só leitura: sem "Salvar", campos `disabled`), faixa
  `aviso-erro` com `resposta.mensagem` e a lista "Alterações não gravadas" com
  `data-copiar-resumo`. `motivo="versao"` → render com a mensagem e as diferenças e o link
  "Editar de novo a partir do que está gravado" (GET do `/editar/`). Erros de validação → render
  como no `atender`.
- Template: faixa "Editando <número>. Nada é gravado até você salvar."; `link-voltar` "Voltar ao
  pedido (descarta as alterações)"; `<form data-editando>` com `<input type="hidden"
  name="versao">`; rodapé com "Descartar" (link ao detalhe) e "Salvar alterações"; título do
  cartão "Editar atendimento".
- `atendimento_materiais` e `atendimento_adicionar` passam a aceitar pedido não avulso sem
  atendimento ou com `edicao_permitida(...).permitida`; os demais, `Http404`.

- [ ] **Step 1: Write the failing tests** — `test_editar_exige_login`, `test_editar_404_sem_pedido`, `test_editar_redireciona_quando_lancado`, `test_editar_preenche_o_formulario` (valores de `recebedor`, `entregue-<codigo>`, `versao`, linha do acrescentado gravado), `test_editar_marca_nao_lancar_vindo_de_automacoes`, `test_post_editar_salva_e_volta_ao_detalhe`, `test_post_em_lancamento_mostra_alteracoes_nao_gravadas_sem_salvar`, `test_post_versao_antiga_oferece_editar_de_novo`, `test_busca_e_adicionar_aceitam_editavel_e_recusam_bloqueado`, `test_atendimento_continua_igual` (GET do detalhe de pedido aguardando não tem `data-editando` e posta em `pedidos:atender`).
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -k "editar_ or post_ or busca or continua" -v` — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_atendimento.py tests/test_atendimento_adicionados.py tests/test_prefixo.py tests/test_rotas.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Pedidos: modo de edição do atendimento"`

---

### Task 9: Modo de edição da saída avulsa

**Files:**
- Modify: `pedidos/views/almoxarifado.py` (`editar` delega a `_editar_avulsa` quando `origem == AVULSA`)
- Modify: `pedidos/templates/pedidos/avulsa.html` (form com `action`, `versao` no lugar de `envio_id` quando `editando`; heading "Editar saída <número>"; rótulo do envio "Salvar alterações"; faixa e recusas iguais às da Task 8, num parcial comum `pedidos/_edicao_faixa.html` criado aqui e usado também no `detalhe.html`)
- Test: `tests/test_editar_atendimento.py`

**Interfaces:**
- Consumes: `editar_saida_avulsa` (Task 5).
- Produces: GET monta `carrinho=Carrinho([LinhaCarrinho(i.codigo, i.qtd_entregue, catalogo.get(i.codigo) or <ItemCatalogo do ItemPedido>)])` e `campos` do atendimento.

- [ ] **Step 1: Write the failing tests** — `test_editar_avulsa_preenche_carrinho_e_saida`, `test_post_editar_avulsa_salva`, `test_editar_avulsa_com_material_oculto_abre`, `test_post_editar_avulsa_lancada_mostra_alteracoes_nao_gravadas`.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -k avulsa -v` — Expected: FAIL nos novos.
- [ ] **Step 3: Implement** (mover a faixa e as recusas da Task 8 para `_edicao_faixa.html`).
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_saida_avulsa.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Saída avulsa: modo de edição"`

---

### Task 10: JavaScript da edição

**Files:**
- Modify: `pedidos/static/pedidos/js/pedidos.js`, `pedidos/static/pedidos/css/pedidos.css`

Comportamento (só com `form[data-editando]` na página; nada muda no atendimento):
- Ao abrir, cada quantidade entregue válida começa confirmada (`confirmarEntrega` sem mover o
  foco); trocas gravadas são reaplicadas por `iniciarTrocas`, como na página devolvida pela
  recusa.
- Cada campo do formulário guarda o valor de abertura (`data-valor-inicial`); diferente dele, o
  campo ganha a classe `campo-alterado` (borda `--cor-primaria` do Clean) e um
  `<span class="campo-dica">alterado</span>`; acrescentado novo ou removido conta como alteração.
  O rodapé mostra `"N alterações"` (`aria-live="polite"`; "1 alteração"; vazio com 0).
- `beforeunload` pede confirmação com N > 0, exceto no envio do próprio formulário e no
  "Descartar" (que, com N > 0, pede `confirm("Descartar as alterações?")`).
- `[data-copiar-resumo]` copia o texto da lista para a área de transferência e troca o rótulo
  para "Copiado" por 2 s.

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Verificar no navegador** (`preview_start`, banco local com `montar_cenario()` e um pedido atendido): abrir `/editar/`, mudar uma quantidade e o recebedor → dois campos destacados e "2 alterações"; desfazer → some; "Descartar" pede confirmação; recarregar com alteração pede confirmação; o atendimento de um pedido aguardando segue igual (sem destaque, sem contagem). Console sem erros.
- [ ] **Step 3: Run** `uv run pytest tests/test_editar_atendimento.py tests/test_atendimento.py -v` — Expected: PASS.
- [ ] **Step 4: Commit** — `git commit -m "Edição: destaque do que mudou, contagem e confirmação ao sair"`

---

### Task 11: Faixa que acompanha o robô durante a edição

**Files:**
- Modify: `pedidos/views/almoxarifado.py` (`editar`: com `HX-Target == "div#edicao-faixa"`, devolve só o parcial; `patch_vary_headers` como em `automacoes/views.py:195-197`)
- Modify: `pedidos/templates/pedidos/_edicao_faixa.html`
- Test: `tests/test_editar_atendimento.py`

Com `ExecucaoRobo.em_andamento()` não vazio, a faixa (`<div id="edicao-faixa">`) leva
`hx-get` da própria URL, `hx-trigger="every 5s"` e `hx-target="this"`, e acrescenta o aviso "Um
lançamento está em andamento; se chegar a este pedido, suas alterações serão recusadas." Se o
lote saiu de `editavel`, o parcial devolve a faixa vermelha com `edicao.motivo` e um atributo
`data-edicao-encerrada`, que o `pedidos.js` usa para desabilitar o "Salvar alterações". Sem
execução em andamento, sem `hx-trigger`.

- [ ] **Step 1: Write the failing tests** — `test_faixa_consulta_so_com_robo_rodando` (com `trava_ocupada` e uma `ExecucaoRobo` sem fim, o HTML tem `every 5s`; sem, não tem), `test_faixa_parcial_pelo_hx_target`, `test_faixa_encerra_quando_o_lote_trava`.
- [ ] **Step 2: Run** `uv run pytest tests/test_editar_atendimento.py -k faixa -v` — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/test_editar_atendimento.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "Edição: faixa acompanha o lançamento em andamento"`

---

### Task 12: Documentação e conferência final

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Atualizar o `CLAUDE.md`** — na área do almoxarifado, um parágrafo sobre a edição (rota `pedidos:editar`, `editar_atendimento`/`editar_saida_avulsa`, `Pedido.versao`, `AlteracaoPedido`, linhas recriadas com IDs novos e por quê, recibo volta a pendente); em "O projeto", o subprojeto 5 como implantado; em Convenções, trocar a regra das migrations por "O servidor está em produção: mudança de modelo ganha migration nova, nunca regenerada."
- [ ] **Step 2: Run** `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run python manage.py makemigrations --check --dry-run` — Expected: tudo verde.
- [ ] **Step 3: Conferência no navegador** com screenshots: detalhe editável, suspenso (lote em `VERIFICAR` pelo admin) e lançado; modo de edição com campos destacados; recusa por lançamento (lote posto em `EM_LANCAMENTO` pelo admin com a edição aberta); edição da avulsa; 375 px (`resize_window` mobile).
- [ ] **Step 4: Commit** — `git commit -m "Documentação: edição do atendimento e regra das migrations"`

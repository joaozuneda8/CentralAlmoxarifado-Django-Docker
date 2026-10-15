# Material adicionado pelo almoxarifado — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No atendimento, o almoxarifado troca um material pedido por outro ou acrescenta um material, e o pedido guarda separados o que o solicitante pediu e o que o almoxarifado acrescentou.

**Architecture:** O `ItemPedido` ganha `origem`, `no_lugar_de` e `adicionado_por` (e `qtd_pedida` nula nos acrescentados). Os acrescentados vivem em campos do `#form-atendimento` até o envio e são gravados por `confirmar_atendimento` na mesma transação. A busca reaproveita a da saída avulsa; um endpoint novo devolve a linha do acrescentado já pronta, e o `pedidos.js` cuida de Trocar, Remover e Desfazer.

**Tech Stack:** Django, MySQL/MariaDB, HTMX 4 (vendorizado), JavaScript sem build, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-material-adicionado-pelo-almoxarifado-design.md`

## Global Constraints

- Código, textos, mensagens e commits em pt-BR; códigos (CADPRO) em `.mono`; estado nunca só por cor.
- Testes só contra MySQL/MariaDB (`uv run pytest`); nunca abrem o navegador.
- Antes da importação das planilhas: a migration `pedidos/migrations/0001_initial.py` é **regenerada** (`migrate pedidos zero` + apagar + `makemigrations pedidos` + `migrate`), sem migration nova nem de conversão de dados.
- `servicos.py` continua o único lugar que grava pedidos; tudo do atendimento numa transação.
- Scripts no `<head>` com `defer`; requisição HTMX que grava vai dentro de `<form>` com `{% csrf_token %}`.
- Interface no vocabulário do `docs/DESIGN.md` (classes novas registradas lá); skills `clean-design`, `ui-ux-pro-max` e `frontend-design` em todo ajuste de UI.
- Catálogo dos acrescentados: `catalogo_de(AVULSA)`; bloqueio só por cadastro duplicado; **sem limite de estoque** (`FLUXOS["avulsa"].com_estoque` é falso).
- Textos fixos: selo "Adicionado pelo almoxarifado"; grupos do recibo "Pedido pelo solicitante" e "Adicionado pelo almoxarifado"; notas "Trocado por {nome}" e "No lugar de {nome}"; recusa de repetido "{nome} ({codigo}) já está no pedido: altere a quantidade nele."; dica "para o que veio na observação ou um a mais, sem trocar nenhum".
- O recibo nunca mostra quem acrescentou.
- Após cada tarefa: `uv run pytest`, `uv run ruff check . && uv run ruff format --check .` e `uv run python manage.py makemigrations --check --dry-run` verdes; com estático alterado, `uv run python manage.py collectstatic --noinput` (o teste de produção lê o manifesto local).

## Review Focus

- Envio com um acrescentado cujo campo `entregue-<codigo>` sumiu (só o `adicionado` veio): deve recusar com erro naquela linha, nunca gravar item sem quantidade. → Tarefa 4.
- Dois acrescentados com o mesmo `no-lugar-de`, ou `no-lugar-de` com código de outro acrescentado: recusa, nada gravado. → Tarefa 4.
- Reenvio do mesmo atendimento com os acrescentados em outra ordem: confirma (o conjunto é o mesmo). → Tarefa 4.
- Pedido AB com acrescentado "1,5": recusa "deve ser inteira"; pedido de limpeza com "1.5": recusa (pt-BR estrito). → Tarefa 4.
- "Desfazer troca" depois de o item pedido ter sido alterado à mão: devolve a quantidade que ele tinha antes da troca, por confirmar. → Tarefa 7 (conferência no navegador).

---

### Task 1: Modelo, restrições e admin

**Files:**
- Modify: `pedidos/models.py` (`ItemPedido`, `LinhaSaida.Meta`)
- Modify: `pedidos/admin.py` (inline dos itens)
- Regenerate: `pedidos/migrations/0001_initial.py`
- Test: `tests/test_modelos_pedidos.py`

**Interfaces:**
- Produces: `ItemPedido.Origem` (`TextChoices`: `PEDIDO = "PEDIDO", "Pedido pelo solicitante"`, `ALMOXARIFADO = "ALMOXARIFADO", "Adicionado pelo almoxarifado"`); campos `origem` (padrão `PEDIDO`), `no_lugar_de` (FK self, `on_delete=restringir_troca` — o `RESTRICT` adaptado ao MySQL, ver a spec 2.1; o `PROTECT` barraria apagar o pedido com troca —, `related_name="trocado_por"`), `adicionado_por` (FK usuário, `PROTECT`, `related_name="+"`); `qtd_pedida` com `null=True, blank=True`; `ItemPedido.clean()`.

- [ ] **Step 1: Testes que falham**, em `tests/test_modelos_pedidos.py`:
  - `test_acrescentado_exige_qtd_pedida_nula_e_quem_acrescentou`: `ItemPedido.objects.create(origem=ALMOXARIFADO, qtd_pedida=1, adicionado_por=u, ...)` levanta `IntegrityError`; idem `origem=ALMOXARIFADO` sem `adicionado_por`; idem `origem=PEDIDO` com `qtd_pedida=None`.
  - `test_pedido_nao_tem_no_lugar_de_nem_adicionado_por`: item `PEDIDO` com `adicionado_por=u` levanta `IntegrityError`.
  - `test_codigo_unico_no_pedido`: dois itens com o mesmo `codigo` no mesmo pedido levantam `IntegrityError`; em pedidos diferentes, não.
  - `test_linha_de_saida_com_quantidade_zero_ou_negativa_e_recusada`: `LinhaSaida` com `qtd=0` e com `qtd=-1` levantam `IntegrityError`.
  - `test_clean_recusa_no_lugar_de_de_outro_pedido_ou_acrescentado`: `full_clean()` levanta `ValidationError` com `no_lugar_de` de outro pedido e com `no_lugar_de` apontando item `ALMOXARIFADO`.
- [ ] **Step 2:** `uv run pytest tests/test_modelos_pedidos.py -q` → FAIL (campos não existem).
- [ ] **Step 3: Implementar** os campos e `Meta.constraints` de `ItemPedido`: `CheckConstraint` "qtd_pedida nula ⇔ ALMOXARIFADO", "adicionado_por preenchido ⇔ ALMOXARIFADO", "no_lugar_de só com ALMOXARIFADO", `UniqueConstraint(fields=["pedido", "codigo"])`; em `LinhaSaida.Meta`, `CheckConstraint(condition=Q(qtd__gt=0), name="linha_saida_qtd_positiva")`. `clean()` com as duas regras do teste. Admin: `origem`, `no_lugar_de` e `adicionado_por` no inline, só leitura.
- [ ] **Step 4:** regenerar a migration (ver Global Constraints) e `uv run pytest -q` → todos passam.
- [ ] **Step 5: Commit** `feat: item do pedido com origem e trava de quantidade positiva na linha de saída`.

### Task 2: Implantação — itens das planilhas

**Files:**
- Modify: `implantacao/conversao.py` (`_converter_itens`, perto da linha 270)
- Test: `tests/test_planilha_conversao.py`

**Interfaces:**
- Consumes: `ItemPedido.Origem` (Task 1).

- [ ] **Step 1: Testes que falham:** `test_itens_importados_sao_pedidos_pelo_solicitante` (todo `carga.itens[i].origem == "PEDIDO"`); `test_codigo_repetido_no_mesmo_pedido_e_erro` (planilha com o mesmo código duas vezes no mesmo `Pedido_ID` → `carga.erros` contém `"Itens, linha N: código 008.001.002 repetido no pedido"` e só a primeira ocorrência entra em `carga.itens`).
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** `origem=ItemPedido.Origem.PEDIDO` no `ItemPedido(...)`; um `set` de `(id_pedido, codigo)` já vistos, com o erro acima usando `_msg("Itens", linha, ...)`.
- [ ] **Step 4:** `uv run pytest tests/test_planilha_conversao.py tests/test_migracao*.py -q` → passa.
- [ ] **Step 5: Commit** `feat: conversão das planilhas marca a origem dos itens e recusa código repetido`.

### Task 3: Situação do pedido com troca

**Files:**
- Modify: `pedidos/regras.py` (`situacao_pedido`, linha ~588)
- Modify: `pedidos/consultas.py` (`filtrar_situacao`, `entregue_a_menos`)
- Test: `tests/test_regras_saidas.py` (onde já estão os testes de `situacao_pedido`) e `tests/test_painel.py::test_filtros_de_situacao_concordam_com_as_regras`

**Interfaces:**
- Consumes: campos da Task 1. `situacao_pedido(origem, atendido, itens)` continua com a mesma assinatura; `itens` são objetos com `origem`, `qtd_pedida`, `qtd_entregue` e `trocado_por` (ou uma lista de dicionários equivalente nos testes puros, como os atuais).

- [ ] **Step 1: Testes que falham:** pedido atendido com item `PEDIDO` em 0 e um `ALMOXARIFADO` com `no_lugar_de` dele e entregue 1 → chave `"atendido"`; mesmo caso com o acrescentado entregue 0 → `"parcial"`; item `PEDIDO` abaixo sem troca → `"parcial"`; só acrescentados a mais e pedidos completos → `"atendido"`. No `test_painel.py`, os cenários de troca entram na lista que confere `filtrar_situacao` contra `situacao_pedido`.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** em `situacao_pedido`, `parcial` considera só itens `PEDIDO` sem acrescentado que os substitua com `qtd_entregue > 0`; acrescentados nunca contam. Em `consultas`, o `Exists` filtra `origem=PEDIDO` e exclui os itens com `Exists(ItemPedido(no_lugar_de=OuterRef("pk"), qtd_entregue__gt=0))`. Para não haver N+1, a propriedade `Pedido.situacao` (`pedidos/models.py:58`) passa os itens com `prefetch_related("trocado_por")`.
- [ ] **Step 4:** `uv run pytest tests/test_regras_saidas.py tests/test_painel.py -q` → passa.
- [ ] **Step 5: Commit** `feat: material trocado não deixa o pedido parcial`.

### Task 4: Serviço — gravar acrescentados no atendimento

**Files:**
- Modify: `pedidos/regras.py` (`Adicionado`, `atendimento_confere`)
- Modify: `pedidos/servicos.py` (`confirmar_atendimento`, linha 366; linha 114), `pedidos/telegram.py`, `pedidos/templates/pedidos/_sucesso.html`
- Test: `tests/test_atendimento_adicionados.py` (criar; usa `tests.cenario`: `montar_cenario`, `registrar`, `envio_limpeza`, `envio_ab`, `saida`)

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Adicionado: codigo: str; no_lugar_de: str = ""` em `regras.py`; `confirmar_atendimento(pedido_id, atendimento_id, dados, qtds, *, nao_lancar, usuario, hoje=None, adicionados: Sequence[Adicionado] = ())` — `qtds` traz também os códigos acrescentados; `atendimento_confere(cabecalho_gravado, entregues, dados, nao_lancar, qtds, adicionados_gravados=frozenset(), adicionados_enviados=frozenset())`, onde cada conjunto é de `(codigo, no_lugar_de, Decimal)`.
- Consumes: Task 1; `catalogo_de(AVULSA)`; `validar_saida(..., catalogo=)`.

- [ ] **Step 1: Testes que falham** (cenário: pedido de limpeza com `023.001.002` = 2 e `008.001.002` = 1,5; o catálogo da avulsa do cenário tem outro código livre — usar o primeiro código de `catalogo_de(AVULSA)` que não esteja no pedido):
  - `test_troca_grava_o_acrescentado_e_o_trocado_com_zero`: `qtds={"023.001.002": "2", "008.001.002": "0", X: "1"}`, `adicionados=[Adicionado(X, "008.001.002")]` → ok; o item X tem `origem="ALMOXARIFADO"`, `qtd_pedida is None`, `qtd_entregue == 1`, `no_lugar_de.codigo == "008.001.002"`, `adicionado_por == usuario`; o café com `qtd_entregue == 0`; as linhas de saída são `023.001.002` e X (seq 1 e 2), nenhuma do café.
  - `test_acrescimo_sem_vinculo`: `Adicionado(X)` → `no_lugar_de is None`.
  - `test_recusas_nao_gravam_nada` (parametrizado): código fora do catálogo; código duplicado no cadastro; X igual a `023.001.002` → mensagem exata do Global Constraints; dois `Adicionado` com o mesmo `no_lugar_de`; `no_lugar_de` = código de outro acrescentado; quantidade "0"; quantidade "abc"; `entregue-X` ausente de `qtds`; pedido AB com "1,5" → "deve ser inteira"; limpeza com "1.5". Para cada um: `ok is False`, `Erro.codigo` aponta X (ou o item trocado), e `Atendimento`, `LinhaSaida` e itens `ALMOXARIFADO` continuam vazios.
  - `test_lote_com_acrescentado_vira_uma_requisicao`: depois da troca, `scpi.requisicoes.selecionar(list(LinhaSaida.objects.all()), centros)` devolve uma requisição só, do lote do pedido, com os itens `023.001.002` e X nessa ordem e sem erro.
  - `test_reenvio_com_os_mesmos_acrescentados_confirma`: mesmo `atendimento_id`, acrescentados em outra ordem → `reenvio is True`; com quantidade diferente → recusa "já tem um atendimento registrado".
- [ ] **Step 2:** `uv run pytest tests/test_atendimento_adicionados.py -q` → FAIL.
- [ ] **Step 3: Implementar.** Converter as quantidades dos acrescentados com o mesmo `conv` do pedido; validar com `validar_saida` (os acrescentados entram como `ItemSaida(codigo, q)` sem `maximo`, passando `catalogo=` só para eles: chamar uma segunda vez com os dados e só os itens acrescentados, juntando os erros sem duplicar os de campo) e as regras de vínculo e repetição; quantidade do acrescentado tem de ser > 0 ("Informe a quantidade de {nome}."). Gravar os `ItemPedido` com `bulk_create` (retrato de `material`, `unidade`, `grupo`, `subgrupo` do `ItemCatalogo`), depois `_gravar_linhas` com pedidos e acrescentados nessa ordem. `atendimento_confere` compara os conjuntos. Por segurança, `servicos` linha 114, `telegram.py` e `_sucesso.html` iteram só os itens `PEDIDO` (`origem=ItemPedido.Origem.PEDIDO`).
- [ ] **Step 4:** `uv run pytest -q` → todos passam (os testes de atendimento de hoje continuam sem `adicionados`).
- [ ] **Step 5: Commit** `feat: atendimento grava materiais acrescentados pelo almoxarifado`.

### Task 5: Views — envio, busca e linha do acrescentado

**Files:**
- Modify: `pedidos/views/almoxarifado.py` (`atender`, `_contexto_detalhe`; views novas `atendimento_materiais`, `atendimento_adicionar`)
- Modify: `pedidos/urls.py`
- Modify: `pedidos/templates/pedidos/_resultados.html` (alvo configurável)
- Create: `pedidos/templates/pedidos/_adicionado.html` (uma `<tr>` do grupo, ou o erro)
- Test: `tests/test_atendimento_adicionados.py` (parte de views)

**Interfaces:**
- Consumes: Task 4 (`Adicionado`, `confirmar_atendimento(..., adicionados=)`).
- Produces:
  - URL `pedidos:atendimento_materiais` = `painel/pedidos/<numero>/materiais/` (GET `q`, `filtro`, `no_lugar_de`): `_resultados.html` do fluxo avulsa com `url_carrinho = reverse("pedidos:atendimento_adicionar", args=[numero])`, `alvo_resultado = "#adicionados"`, `troca_resultado = "beforeend"` e, na troca, `qtd_inicial` = quantidade pedida do item trocado.
  - URL `pedidos:atendimento_adicionar` = `painel/pedidos/<numero>/adicionar/` (POST `adicionar`, `qtd-<codigo>`, `no_lugar_de`, `adicionado` repetido): devolve `_adicionado.html` com a linha (`data-adicionado`, `data-no-lugar-de`, campos `adicionado`, `no-lugar-de-<codigo>` e `entregue-<codigo>` com `form="form-atendimento"`) ou, recusado, um `<tr>` de erro com `HX-Retarget` para `#adicionar-erro` e status 200 (o `htmx-config` não troca 4xx). Recusa os mesmos casos de vínculo e repetição da Task 4 contra o pedido e os `adicionado` enviados.
  - `_resultados.html`: `hx-target="{{ alvo_resultado|default:'#carrinho' }}"` e `hx-swap="{{ troca_resultado|default:'innerHTML' }}"` (o padrão de hoje, conferir no arquivo), `value` da quantidade com `qtd_inicial` quando houver.
  - `atender`: lê `request.POST.getlist("adicionado")` e `no-lugar-de-<codigo>`, monta `[Adicionado(...)]`, inclui `entregue-<codigo>` deles em `qtds`; na recusa, o contexto leva `adicionados` (lista de dicts com o `ItemCatalogo`, a quantidade digitada e o vínculo) para o template redesenhar as linhas.
- [ ] **Step 1: Testes que falham:** GET de `atendimento_materiais?q=café` traz resultados da avulsa com `hx-post` para a URL de adicionar e `hx-target="#adicionados"`; POST de `atendimento_adicionar` com X e `no_lugar_de=008.001.002` devolve `<tr` com `data-adicionado="X"`, `name="adicionado" value="X"`, `name="entregue-X"` e "No lugar de CAFÉ"; POST com código do pedido devolve a mensagem de repetido; POST de `atender` com um acrescentado válido grava (redireciona) e com um inválido devolve a página com a linha do acrescentado e o erro nela (`entrega-erro`); as duas URLs exigem login (`/painel/entrar/`).
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** implementar as views (com `@login_required`; a de adicionar com `@require_POST`), as URLs e os templates.
- [ ] **Step 4:** `uv run pytest -q` → todos passam (os testes da busca pública e da avulsa continuam com `#carrinho`).
- [ ] **Step 5: Commit** `feat: busca e linha do material acrescentado no atendimento`.

### Task 6: Recibo e tabela do atendimento

**Files:**
- Modify: `pedidos/templates/pedidos/_recibo.html`
- Modify: `pedidos/static/pedidos/css/pedidos.css`
- Modify: `docs/DESIGN.md` (classes novas: `atendimento-painel`, `recibo-grupo`, `recibo-nota`)
- Test: `tests/test_atendimento_adicionados.py` (parte de recibo)

**Interfaces:**
- Consumes: Tasks 1, 4 e 5 (`_adicionado.html` é incluído no laço dos acrescentados).

- [ ] **Step 1: Testes que falham:** detalhe pendente tem, por item pedido, um botão `data-trocar="<codigo>"` com `hidden` (o JS mostra), o botão `data-adicionar-material` com `hidden`, a observação do pedido acima dele quando houver, e o `<tbody id="adicionados">` (vazio); recibo atendido com troca tem as linhas de grupo "Pedido pelo solicitante" e "Adicionado pelo almoxarifado", "Trocado por …" no café, "No lugar de …" no acrescentado, "—" na coluna Pedido dele, e o nome de quem acrescentou **não** aparece; pedido sem acrescentado continua sem as linhas de grupo; o título conta todos ("Materiais (3)").
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** template: separar `itens` por `origem`; o grupo dos acrescentados num `<tbody id="adicionados">` com a linha de grupo e o selo `selo-info`; `data-pedido` vazio nos acrescentados (o estado total/parcial não se aplica); CSS das classes novas no vocabulário do `DESIGN.md`.
- [ ] **Step 4:** `uv run pytest -q` e `collectstatic` → passa.
- [ ] **Step 5: Commit** `feat: recibo separa o pedido pelo solicitante do acrescentado pelo almoxarifado`.

### Task 7: Comportamento na tela (pedidos.js)

**Files:**
- Modify: `pedidos/static/pedidos/js/pedidos.js`
- Modify: `CLAUDE.md` (parágrafo da área do almoxarifado)

**Interfaces:**
- Consumes: os atributos da Task 6 (`data-trocar`, `data-adicionar-material`, `#adicionados`) e da Task 5 (linha com `data-adicionado`, `data-no-lugar-de`; botões `data-remover-adicionado` e `data-desfazer-troca`).

- [ ] **Step 1:** mostrar `data-trocar` e `data-adicionar-material` só com JavaScript; "Trocar" abre o `atendimento-painel` embaixo da linha, com o título da spec, a busca (`hx-get` de `atendimento_materiais` com `no_lugar_de`) e "Desistir"; ao entrar a linha (`htmx:after:swap` em `#adicionados`): o item trocado vai para 0, fica confirmado ("Não entregue"), ganha "Trocado por {nome}", guarda a quantidade anterior em `data-qtd-antes` e esconde o seu "Trocar"; o foco vai para o campo da nova linha; o `role="status"` da tabela anuncia "{novo} entrou no lugar de {trocado}." (ou "{novo} foi adicionado.").
- [ ] **Step 2:** "Remover" tira a linha; "Desfazer troca" tira a linha e devolve ao item trocado o `data-qtd-antes`, por confirmar, mostrando de novo o "Trocar"; os dois anunciam no `role="status"`. "Entregar tudo o que foi pedido" ignora as linhas com `data-adicionado` e os itens trocados. A confirmação por linha e o bloqueio do envio (já existentes) valem para os acrescentados.
- [ ] **Step 3: Conferir no navegador** (`preview_start` com `django`, pedido pendente de limpeza): trocar o café, conferir as notas, o foco e o anúncio; desfazer depois de alterar o café à mão (volta a quantidade de antes da troca); adicionar sem vínculo; tentar enviar com o acrescentado por confirmar (barra); recusa do servidor devolve as linhas; celular (375px) sem rolagem lateral da página. **Não** enviar um atendimento válido no banco local sem combinar.
- [ ] **Step 4:** `uv run pytest -q`, ruff, `collectstatic`; atualizar o `CLAUDE.md` (troca e acréscimo no atendimento, origem do item, as três travas de quantidade > 0).
- [ ] **Step 5: Commit** `feat: trocar e adicionar material na tela de atendimento`.

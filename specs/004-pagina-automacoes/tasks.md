---

description: "Tarefas da página única de automações"
---

# Tasks: Página única de automações

**Input**: documentos em `specs/004-pagina-automacoes/` (plan.md, spec.md, research.md,
data-model.md, contracts/pagina-automacoes.md, quickstart.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: obrigatórios (constituição, Princípio V: toda mudança de comportamento vem com teste;
pytest contra MySQL/MariaDB, sem navegador). Escreva o teste antes e veja-o falhar.

**Organization**: por história de usuário (spec.md). Antes de começar: `git switch -c
004-pagina-automacoes`. Todo ajuste de UI usa `clean-design` + `docs/DESIGN.md`, `ui-ux-pro-max` e
`frontend-design` (convenção do `CLAUDE.md`). Textos de interface em pt-BR.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história da spec (US1…US6)

## Path Conventions

Django monolítico na raiz: apps `automacoes/` (novo), `catalogo/`, `pedidos/`, `interface/`,
`config/`; testes em `tests/`.

---

## Phase 1: Setup

**Purpose**: o app novo, vazio, registrado

- [X] T001 Criar o app `automacoes` sem models nem migrations: `automacoes/__init__.py`, `automacoes/apps.py` (`AutomacoesConfig`, `name = "automacoes"`, `verbose_name = "Automações"`), `automacoes/urls.py` (`app_name = "automacoes"`, lista vazia), `automacoes/views.py`, `automacoes/templates/automacoes/` e `automacoes/static/automacoes/css/automacoes.css` (vazio, com o comentário de cabeçalho no estilo de `catalogo/static/catalogo/css/catalogo.css`)
- [X] T002 Registrar o app em `INSTALLED_APPS` de `config/settings.py` (depois de `catalogo` e `pedidos`) e incluir `path("painel/automacoes/", include("automacoes.urls"))` em `config/urls.py`, antes de `path("painel/", include("contas.urls"))`
- [X] T003 Conferir que `uv run python manage.py check` e `uv run python manage.py makemigrations --check --dry-run` passam sem migration nova

---

## Phase 2: Foundational

**Purpose**: a página com as cinco abas e a escolha da região HTMX, ainda ao lado das páginas antigas

**⚠️ CRITICAL**: nenhuma história começa antes desta fase

- [X] T004 Escrever `tests/test_automacoes.py` com os testes da base (falhando): `GET reverse("automacoes:pagina")` exige login (redireciona para `/painel/entrar/?next=…`); logado responde 200 com o título "Automações", `[data-abas]` e as abas `#aba-visao-geral`, `#aba-lancamento`, `#aba-cadastro`, `#aba-estoque`, `#aba-saidas` nessa ordem, com os painéis `#painel-<chave>`; `?aba=` desconhecida, ausente ou `situacao` deixa `visao-geral` ativa (`aria-selected="true"`); com `HX-Request: true` e `HX-Target: section#situacao-catalogo` devolve só a seção `id="situacao-catalogo"` (sem `<html`), com `HX-Target: section#lancamentos` só `id="lancamentos"`, com alvo desconhecido ou com `HX-History-Restore-Request` a página inteira; toda resposta tem `Vary` com `HX-Request`, `HX-Target` e `HX-History-Restore-Request`
- [X] T005 Em `automacoes/views.py`, criar `ABAS` (lista de `(chave, rotulo)`: `("visao-geral", "Visão geral")`, `("lancamento", "Lançamento no SCPI")`, `("cadastro", "Cadastro")`, `("estoque", "Estoque")`, `("saidas", "Saídas")`), `aba_pedida(request) -> str` (regra: desconhecida, ausente ou `"situacao"` → `"visao-geral"`) e `REGIOES = {"section#situacao-catalogo": "catalogo/_situacao.html", "section#lancamentos": "pedidos/_lancamentos.html"}` (o histórico entra em US4)
- [X] T006 Levar para `automacoes/views.py` o contexto das duas páginas como funções: `contexto_catalogo(request, aba, formularios=None)` (cópia de `catalogo.views._contexto`, junto com `CARENCIA`, `CHAVE_DISPARO`, `_disparo_recente` e `importacao_em_andamento`, sem a chave `historico` nem `LINHAS_HISTORICO`) e `contexto_lancamento(request)` (o corpo de `pedidos.views.lancamentos.lancamentos` até montar o dicionário, sem `execucoes` nem o laço que preenche `requisicoes`/`duracao`); as views antigas passam a chamar essas funções enquanto existirem
- [X] T007 Em `automacoes/views.py`, criar `contexto_pagina(request, aba, formularios=None) -> dict` (o contexto inteiro da página, reusado pela view e pelo form inválido de importação em T021) e a view `pagina(request)` (`@login_required`), que usa `contexto_pagina` e junta `contexto_catalogo(request, aba)` e `contexto_lancamento(request)` (o `acompanhar` de cada um vira `acompanhar_catalogo` e `acompanhar_lancamento`, e os templates parciais passam a ler esses nomes), `abas`, `aba`; com `HX-Request` e sem `HX-History-Restore-Request`, escolhe o template em `REGIOES` pelo cabeçalho `HX-Target` (alvo fora de `REGIOES` → página inteira); `patch_vary_headers(resposta, ["HX-Request", "HX-Target", "HX-History-Restore-Request"])`. Registrar `path("", views.pagina, name="pagina")` em `automacoes/urls.py`
- [X] T008 Criar `automacoes/templates/automacoes/pagina.html` estendendo `interface/base_almoxarifado.html`: `title` "Automações — Central Almoxarifado", `heading` "Automações", `sub` "Robôs que trazem dados do SCPI e lançam as saídas atendidas."; `extra_css` com `catalogo/css/catalogo.css`, `pedidos/css/pedidos.css` e `automacoes/css/automacoes.css`; `extra_head` com `catalogo/js/importacoes.js` e `pedidos/js/pedidos.js` (`defer`); abas no padrão de `catalogo/templates/catalogo/situacao.html` (`[data-abas]` com `data-url="{% url 'automacoes:pagina' %}"`, `role="tablist"` com `aria-label="Automações"`), painéis: `visao-geral` inclui `catalogo/_situacao.html`; `lancamento` inclui `pedidos/_lancamentos.html`; um por robô inclui `catalogo/_robo.html` (o `for item in robos` de hoje)
- [X] T009 Trocar, em `catalogo/templates/catalogo/_situacao.html` e `pedidos/templates/pedidos/_lancamentos.html`, o `hx-get` da seção para `{% url 'automacoes:pagina' %}` e as condições de acompanhamento para `acompanhar_catalogo` / `acompanhar_lancamento`; trocar os links internos `?aba=<chave>` de `_situacao.html` para a página nova (`{% url 'automacoes:pagina' %}?aba=<chave>`, mantendo `data-abrir-aba`)
- [X] T010 Trocar em `interface/navegacao.py` os itens "Catálogo" e "Lançamentos SCPI" por `ItemMenu("Automações", "automacoes:pagina", "robo")`, depois de "Saída avulsa" e antes de "Curva ABC" (o menu não pode apontar para rotas que as fases seguintes apagam)
- [X] T011 Rodar `uv run pytest tests/test_automacoes.py` e a suíte inteira; corrigir só o que esta fase quebrou

**Checkpoint**: `/painel/automacoes/` mostra tudo das duas páginas em abas; as páginas antigas ainda existem.

---

## Phase 3: User Story 2 - Operar o lançamento no SCPI dentro de Automações (Priority: P1) 🎯 MVP

**Goal**: simular, lançar, ver a fila, acompanhar e resolver travas na aba Lançamento no SCPI, com o
mesmo comportamento de hoje; a página Lançamentos SCPI e suas rotas deixam de existir.

**Independent Test**: na aba Lançamento, simular com uma requisição na fila, acompanhar até o fim e
resolver uma trava; cada ação volta para `?aba=lancamento` com o aviso de hoje, e
`/painel/lancamentos/` dá 404.

### Tests for User Story 2

- [X] T012 [US2] Adaptar `tests/test_pagina_lancamentos.py` e `tests/test_lancamento_real.py` às rotas novas: `pedidos:lancamentos` → `reverse("automacoes:pagina") + "?aba=lancamento"` (asserções de conteúdo sobre a aba `#painel-lancamento`), `pedidos:lancar` → `automacoes:lancar`, `pedidos:resolver` → `automacoes:resolver`, `monkeypatch` de `pedidos.views.lancamentos.iniciar_lancamento` → `automacoes.views.iniciar_lancamento`, redirecionamentos esperados para `/painel/automacoes/?aba=lancamento`; o parcial HTMX é pedido com `HX-Target: section#lancamentos`; tirar as asserções de "Últimas execuções" (vão para o histórico, US4); a asserção do link do detalhe do pedido com lote travado ("Resolver em Lançamentos SCPI") passa a esperar "Resolver em Automações" com `href` para `?aba=lancamento#travas` (T016)
- [X] T013 [P] [US2] Acrescentar a `tests/test_automacoes.py`: `GET /painel/lancamentos/`, `POST /painel/lancamentos/iniciar/` e `POST /painel/lancamentos/P-1/resolver/` respondem 404; `reverse("pedidos:lancamentos")`, `reverse("pedidos:lancar")` e `reverse("pedidos:resolver", args=["P-1"])` levantam `NoReverseMatch`

### Implementation for User Story 2

- [X] T014 [US2] Mover `lancar` e `resolver` de `pedidos/views/lancamentos.py` para `automacoes/views.py` com o mesmo corpo (form `LancamentoForm.da_requisicao`, confirmação `confirmado == "1"` do "Não lançar", `resolver_lote`, mensagens), trocando cada `redirect("pedidos:lancamentos")` por um redirecionamento para `reverse("automacoes:pagina") + "?aba=lancamento"`; rotas em `automacoes/urls.py`: `path("lancar/", views.lancar, name="lancar")` e `path("lancamento/<str:lote>/resolver/", views.resolver, name="resolver")`
- [X] T015 [US2] Em `pedidos/templates/pedidos/_lancamentos.html`, trocar `{% url 'pedidos:lancar' %}` por `{% url 'automacoes:lancar' %}` e `{% url 'pedidos:resolver' trava.lote %}` por `{% url 'automacoes:resolver' trava.lote %}`; tirar o cartão "Últimas execuções" (o histórico combinado o substitui em US4)
- [X] T016 [US2] Em `pedidos/templates/pedidos/painel.html`, trocar o `action` do atalho "Lançar no SCPI" para `{% url 'automacoes:lancar' %}` e o link "para conferir" para `{% url 'automacoes:pagina' %}?aba=lancamento#travas`; em `pedidos/templates/pedidos/detalhe.html`, o link "Resolver em Lançamentos SCPI" vira "Resolver em Automações" com `{% url 'automacoes:pagina' %}?aba=lancamento#travas`; garantir `id="travas"` no cartão "Travas para conferir" de `_lancamentos.html`
- [X] T017 [US2] Apagar `pedidos/views/lancamentos.py`, `pedidos/templates/pedidos/lancamentos.html` e as três rotas de lançamento em `pedidos/urls.py` (`painel/lancamentos/`, `painel/lancamentos/iniciar/`, `painel/lancamentos/<str:lote>/resolver/`) e o import `lancamentos` de lá; conferir com `grep -rn "pedidos:lanc\|pedidos:resolver\|views.lancamentos" --include=*.py --include=*.html .` que nada mais aponta para elas
- [X] T018 [US2] Rodar `uv run pytest tests/test_pagina_lancamentos.py tests/test_lancamento_real.py tests/test_automacoes.py`

**Checkpoint**: lançamento completo dentro de Automações; nenhum caminho antigo de lançamento.

---

## Phase 4: User Story 3 - Rodar e acompanhar as importações dentro de Automações (Priority: P1)

**Goal**: "Atualizar agora", carga inicial completa e os três robôs de importação dentro de
Automações; a página Catálogo e suas rotas deixam de existir (fica só a Curva ABC).

**Independent Test**: "Atualizar agora" volta para `?aba=visao-geral` com o aviso e acompanha; enviar
um CSV na aba Estoque volta para `?aba=estoque`; form inválido re-renderiza Automações na aba do
robô com os erros; `/painel/catalogo/` dá 404 e `/painel/catalogo/curva/` continua.

### Tests for User Story 3

- [X] T019 [US3] Adaptar `tests/test_pagina_catalogo.py` e `tests/test_robos_avulsos.py`: `catalogo:situacao` → `automacoes:pagina` (com `?aba=` quando o teste abre um robô), `catalogo:atualizar` → `automacoes:atualizar`, `catalogo:importar` → `automacoes:importar`, `monkeypatch` de `catalogo.views.iniciar_atualizacao`/`iniciar_importacao`/`guardar_csv_enviado` → `automacoes.views.*`, redirecionamentos esperados (atualizar → `/painel/automacoes/?aba=visao-geral`; importar → `/painel/automacoes/?aba=<robo>`), parcial HTMX com `HX-Target: section#situacao-catalogo`; tirar as asserções do cartão "Histórico" da situação (vão para US4)
- [X] T020 [P] [US3] Acrescentar a `tests/test_automacoes.py`: `GET /painel/catalogo/`, `POST /painel/catalogo/atualizar/` e `POST /painel/catalogo/importar/estoque/` respondem 404; `reverse("catalogo:situacao")`, `reverse("catalogo:atualizar")` e `reverse("catalogo:importar", args=["estoque"])` levantam `NoReverseMatch`; `GET reverse("catalogo:curva")` continua 200

### Implementation for User Story 3

- [X] T021 [US3] Mover `atualizar` e `importar` de `catalogo/views.py` para `automacoes/views.py` com o mesmo corpo (confirmação "Estou ciente", carência do disparo, `guardar_csv_enviado`, apagar o CSV em falha, mensagens): atualizar redireciona para `?aba=visao-geral`; importar redireciona para `?aba=<robo>` e, com form inválido, renderiza `automacoes/pagina.html` com `contexto_pagina(request, robo, {robo: form})` (de T007, sem montar o contexto de novo); a mensagem de sucesso da importação diz "Acompanhe na Visão geral."; rotas em `automacoes/urls.py`: `path("atualizar/", …, name="atualizar")` e `path("importar/<str:robo>/", …, name="importar")`
- [X] T022 [US3] Em `catalogo/templates/catalogo/_situacao.html` e `catalogo/templates/catalogo/_robo.html`, trocar `{% url 'catalogo:atualizar' %}` por `{% url 'automacoes:atualizar' %}` e `{% url 'catalogo:importar' robo.chave %}` por `{% url 'automacoes:importar' robo.chave %}`; tirar o cartão "Histórico" de `_situacao.html` (US4 o recoloca combinado)
- [X] T023 [US3] Em `pedidos/templates/pedidos/painel.html`, o link "Ver catálogo" vira "Ver automações" para `{% url 'automacoes:pagina' %}`
- [X] T024 [US3] Apagar de `catalogo/views.py` tudo menos a curva (`situacao`, `atualizar`, `importar`, `_contexto`, `_historico`, `ABAS`, `LINHAS_HISTORICO`, `CARENCIA`, `CHAVE_DISPARO`, `_disparo_recente`, `importacao_em_andamento` e os imports que sobrarem); deixar em `catalogo/urls.py` só `path("curva/", views.curva, name="curva")`; apagar `catalogo/templates/catalogo/situacao.html`; atualizar o comentário de cabeçalho de `catalogo/static/catalogo/js/importacoes.js` ("Página Automações, abas dos robôs de importação…"); conferir com `grep -rn "catalogo:situacao\|catalogo:atualizar\|catalogo:importar\|catalogo.views.importacao_em_andamento" --include=*.py --include=*.html .`
- [X] T025 [US3] Rodar `uv run pytest tests/test_pagina_catalogo.py tests/test_robos_avulsos.py tests/test_pagina_curva.py tests/test_automacoes.py`

**Checkpoint**: importações completas dentro de Automações; a única rota de `catalogo` é a curva.

---

## Phase 5: User Story 1 - Ver de uma vez se os robôs estão bem (Priority: P1)

**Goal**: a visão geral com uma linha por automação (lançamento, cadastro, estoque, saídas), estado
em texto, quando rodou e o caminho para resolver; selos nas abas; acompanhamento também do
lançamento.

**Independent Test**: com uma falha de estoque, um lote travado e o resto em dia, a visão geral
mostra as quatro linhas, destaca as duas, "Tentar de novo" leva a `?aba=estoque` e "Conferir travas"
a `?aba=lancamento#travas`.

### Tests for User Story 1

- [X] T026 [P] [US1] Escrever `tests/test_visao_geral.py`: quatro linhas na ordem lançamento, cadastro, estoque, saídas; com tudo em dia, selos "Em dia" e nenhum alerta; `Importacao(tipo="ESTOQUE", situacao="FALHA", erro="TimeoutError: x")` → linha do estoque "Falhou" com a frase de `resumo_do_erro` e link "Tentar de novo" para `?aba=estoque`; um lote `VERIFICAR` (fixture de `tests/test_pagina_lancamentos.py`) → linha do lançamento "1 para conferir" com link para `?aba=lancamento#travas` e selo na aba `#aba-lancamento`; uma `LinhaSaida` `PENDENTE` → "1 requisição aguardando o robô"; `ExecucaoRobo` em andamento (situação `ANDAMENTO`, `inicio` agora) → linha "Em andamento", selo na aba e a seção `#situacao-catalogo` com `hx-trigger="every 5s"`; com uma `Importacao` e uma `ExecucaoRobo` em andamento juntas, as duas linhas dizem "Em andamento" e, depois de a importação terminar (`situacao="SUCESSO"`, `fim` há mais de 30 s), a resposta ainda traz `#situacao-catalogo` com `every 5s` (o lançamento segue) e `#lancamentos` com `every 3s`; com a execução terminada e a importação em andamento, `#situacao-catalogo` segue com `every 5s` e `#lancamentos` fica sem `hx-trigger`; sem nenhum registro → as importações dizem "Sem dados" e o lançamento "Sem execuções", sem erro
- [X] T027 [P] [US1] Escrever em `tests/test_visao_geral.py` os testes da função pura `linha_lancamento(...)` (sem banco): recebe `pendentes`, `travados`, a última execução (ou `None`), `em_andamento` e `agora`, e devolve `LinhaAutomacao` com `nivel` em `ok`/`andamento`/`aviso`/`erro` e `selo` em texto (FALHA → "Falhou"; interrompida → "Interrompida"; travados > 0 → "N para conferir", nível `aviso`; nenhuma execução → "Sem execuções")

### Implementation for User Story 1

- [X] T028 [US1] Criar `automacoes/visao_geral.py` com a dataclass `LinhaAutomacao` (`automacao`, `rotulo`, `nivel`, `selo`, `quando`, `ha_quanto`, `resumo`, `acao_rotulo`, `acao_url`, campos conforme `data-model.md`), `linha_lancamento(...)` pura (T027) e `linhas_da_visao_geral(situacao, lancamento, agora) -> list[LinhaAutomacao]`, que monta a do lançamento e converte cada `saude.Fonte` de cadastro, estoque e saídas (ação "Tentar de novo" para falha/interrompida, "Importar" discreto quando em dia, nenhuma em andamento — a regra que hoje está no template)
- [X] T029 [US1] Em `automacoes/views.py`, pôr `linhas` (de `linhas_da_visao_geral`) no contexto, calcular o selo de cada aba (importação: o da `Fonte` com nível `erro`/`aviso`; lançamento: "N para conferir" com travas, "Em andamento" com execução) e fazer `acompanhar_catalogo` valer também quando o lançamento está em andamento (`ExecucaoRobo.em_andamento()`), para a linha do lançamento na visão geral se atualizar
- [X] T030 [US1] Em `catalogo/templates/catalogo/_situacao.html`, trocar a lista de fontes pela lista de `linhas` (uma por automação: rótulo, selo `selo selo-<nivel>` com texto, "há quanto tempo", resumo, link de ação), mantendo "Atualizar agora", "Para conferir", os números dos formulários e a carga inicial recolhida; em `automacoes/templates/automacoes/pagina.html`, mostrar o selo de cada aba como hoje (`selo-erro`/`selo-aviso`, e `selo-info` para "Em andamento"); estilos novos só se necessário em `automacoes/static/automacoes/css/automacoes.css`, com o vocabulário de `docs/DESIGN.md`
- [X] T031 [US1] Rodar `uv run pytest tests/test_visao_geral.py tests/test_pagina_catalogo.py tests/test_saude.py`

**Checkpoint**: a visão geral responde "algum robô precisa de mim?" com uma olhada.

---

## Phase 6: User Story 4 - Um histórico só, com filtros (Priority: P2)

**Goal**: na visão geral, o histórico com as execuções de todos os robôs, filtros recolhíveis do
painel (busca, robô, situação, período), paginação de 20 e "Ver histórico" nas abas.

**Independent Test**: com execuções dos quatro robôs, filtrar por "Estoque" e "Falhou" deixa só a
falha do estoque; recarregar o endereço mantém os filtros; "Ver histórico" na aba Lançamento abre a
lista filtrada por `robo=lancamento`.

### Tests for User Story 4

- [X] T032 [P] [US4] Escrever `tests/test_historico_automacoes.py` (funções puras, sem banco além de criar os registros): `linha_de_importacao` e `linha_de_execucao` montam `LinhaHistorico` com `robo`, `modo` ("Simulação"/"Lançamento real"; cadastro com `periodo_de`/`periodo_ate` → "Só os novos (dd/mm a dd/mm)"; cadastro sem período → "Recarga completa"; saídas → "Período dd/mm a dd/mm"; estoque → "Saldos"; de/para → "Carga da planilha"), `duracao`, `selo` e `situacao` pelo mapa de `research.md` R6 (Importacao `SUCESSO` sem avisos → `concluida`/"Concluída"; com avisos → `com_avisos`/"Com avisos"; `FALHA` → `falhou`; `ANDAMENTO` no conjunto em andamento → `andamento`, fora → `interrompida`; ExecucaoRobo `ATENCAO` → `com_avisos`/"Com pendências"); erro com `resumo_do_erro`/`erro_tecnico` (importação) e `andamento.explicar_falha` (lançamento)
- [X] T033 [P] [US4] Escrever em `tests/test_historico_automacoes.py` os testes de consulta (banco real): intercala `Importacao` e `ExecucaoRobo` por `inicio` decrescente (empate: lançamento antes, depois `pk` decrescente); `robo=estoque` só traz importações de estoque e `robo=lancamento` só execuções; cada `situacao` (`concluida`, `com_avisos`, `falhou`, `interrompida`, `andamento`) filtra os dois modelos, inclusive "sem avisos" com `avisos=[]` no MySQL/MariaDB; `de`/`ate` pelos limites do dia local (`ate` inclui o dia inteiro); `q` acha texto no `erro`, nos `avisos` e no `log`, sem diferença de maiúsculas; valor desconhecido em `robo`/`situacao` é ignorado; `SequenciaHistorico.count()` soma as duas contagens e a fatia `[20:40]` devolve a segunda página certa com 25 + 25 registros
- [X] T034 [P] [US4] Acrescentar a `tests/test_automacoes.py`: a visão geral tem `form.filtros-recolhiveis[data-filtros]` com `hx-target="#historico"`, `hx-push-url="true"`, `input type="hidden" name="aba" value="visao-geral"` e `action` = `reverse("automacoes:pagina")`; `GET ?robo=estoque&situacao=falhou` mostra só a falha e "1 execução" com indicação de filtro; filtro sem resultado mostra "Nenhuma execução corresponde aos filtros." e o link "Limpar filtros" para `?aba=visao-geral#historico`; `HX-Target: div#historico` devolve só `id="historico"` com a paginação (`interface/_paginacao.html`, `parametro="pagina"`); cada aba de robô e a de lançamento têm "Ver histórico" para `?aba=visao-geral&robo=<chave>#historico` (`lancamento`, `cadastro`, `estoque`, `saidas`); os cartões antigos "Histórico" e "Últimas execuções" não aparecem mais; com uma `Importacao` de saídas em andamento e `GET ?aba=visao-geral&robo=saidas&pagina=2`, o `hx-get` de `#historico` contém `robo=saidas` e `pagina=2` (o acompanhamento não perde filtros nem página), e sem nada em andamento `#historico` não tem `hx-trigger`

### Implementation for User Story 4

- [X] T035 [US4] Expor em `pedidos/consultas.py` o `_inicio` como `inicio_do_dia(dia: date) -> datetime` (mantendo os usos atuais) para o filtro de período
- [X] T036 [US4] Criar `automacoes/historico.py`: `FiltrosHistorico` (form GET no molde de `pedidos.consultas.FiltrosPainel`: `q` com `placeholder="Erro, aviso ou registro"`; `robo` com choices `("", "Todos"), ("lancamento", "Lançamento no SCPI"), ("cadastro", "Cadastro"), ("estoque", "Estoque"), ("saidas", "Saídas"), ("depara", "Pares de/para")`; `situacao` com `("", "Todas"), ("concluida", "Concluída"), ("com_avisos", "Com avisos"), ("falhou", "Falhou"), ("interrompida", "Interrompida"), ("andamento", "Em andamento")`; `de`/`ate` `DateField` `type="date"`; widgets com `class="campo-entrada"`; `filtros()` devolve só os valores válidos, ignorando o desconhecido), a dataclass `LinhaHistorico` (campos de `data-model.md`), `linha_de_importacao`/`linha_de_execucao` puras (T032)
- [X] T037 [US4] Em `automacoes/historico.py`, criar `consultas(filtros, agora) -> tuple[QuerySet | None, QuerySet | None]` (filtros em SQL por modelo; ids de `Importacao.em_andamento(agora)` e `ExecucaoRobo.em_andamento(agora)` calculados uma vez; "sem avisos" com `Cast("avisos", CharField())` igual a `"[]"`; `q` com `icontains` em `erro`, no `Cast` dos `avisos` e em `log`; período com `inicio_do_dia`) e `SequenciaHistorico` (`count()`, `__len__` e `__getitem__(slice)` que busca `stop` linhas de cada consulta ordenada por `-inicio`, intercala e converte em `LinhaHistorico`), servindo ao `Paginator(…, 20)`
- [X] T038 [US4] Criar `automacoes/templates/automacoes/_filtros_historico.html` copiando a marcação de filtros de `pedidos/templates/pedidos/painel.html` (`filtros-recolhiveis`, `filtros-barra` com busca, `filtros-alternar` com `filtros-contagem` e `filtros-seta`, `filtros-limpar` para `?aba=visao-geral#historico`, `filtros-chips`, `filtros-painel` com `filtros-grade` para robô e situação e `filtros-periodo` para de/até, botão "Filtrar"), com `hx-get="{% url 'automacoes:pagina' %}" hx-target="#historico" hx-push-url="true" hx-trigger="change, input delay:400ms, submit"` e o campo escondido `aba=visao-geral`
- [X] T039 [US4] Criar `automacoes/templates/automacoes/_historico.html` (`<div id="historico">`): total ("N execuções", com "filtradas" quando há filtro ativo), tabela `tabela` dentro de `tabela-rolagem` com colunas Robô (com o modo embaixo, `texto-secundario`), Início (`tabela-data`), Duração, Situação (selo com texto) e Resumo (com o erro em frase e o detalhe técnico num `<details>`, como em `catalogo/_situacao.html` hoje), estado vazio com "Nenhuma execução corresponde aos filtros." e "Limpar filtros", e `{% include "interface/_paginacao.html" with pagina=pagina parametro="pagina" rotulo="Paginação do histórico" rotulo_item="execução" rotulo_item_plural="execuções" htmx_alvo="#historico" htmx_indicador="#historico" %}`; quando `acompanhar_catalogo` ou `acompanhar_lancamento`, a div leva `hx-get` para a página com a query atual, `hx-trigger="every 5s"` e `hx-swap="outerHTML"`
- [X] T040 [US4] Em `automacoes/views.py`, montar `filtros_historico` e `pagina_historico` no contexto (página do `?pagina=`), acrescentar `"div#historico": "automacoes/_historico.html"` a `REGIOES`; em `automacoes/templates/automacoes/pagina.html`, colocar na aba Visão geral, depois de `_situacao.html` e fora dele, um cartão "Histórico" com `_filtros_historico.html` e `_historico.html`
- [X] T041 [US4] Acrescentar o link "Ver histórico" (`botao botao-texto` com o ícone `seta-direita`) para `{% url 'automacoes:pagina' %}?aba=visao-geral&robo=<chave>#historico` em `catalogo/templates/catalogo/_robo.html` (chave do robô) e em `pedidos/templates/pedidos/_lancamentos.html` (`lancamento`), com `data-abrir-aba="visao-geral"` para o `abas.js` trocar de aba sem recarregar
- [X] T042 [US4] Rodar `uv run pytest tests/test_historico_automacoes.py tests/test_automacoes.py`

**Checkpoint**: um histórico só, com o mesmo filtro do painel.

---

## Phase 7: User Story 5 - Links internos levam direto a Automações (Priority: P2)

**Goal**: nenhum link interno leva a página apagada.

**Independent Test**: atalhos do painel e o link do detalhe do pedido abrem a aba certa de
Automações; os endereços antigos dão 404.

- [X] T043 [P] [US5] Adaptar `tests/test_painel.py` (atalho "Lançar no SCPI" envia para `automacoes:lancar`; "para conferir" aponta para `?aba=lancamento#travas`; "Ver automações" para `automacoes:pagina`) e conferir que o teste do link "Resolver em Automações" no detalhe do pedido, adaptado em T012 em `tests/test_pagina_lancamentos.py`, aponta para `?aba=lancamento#travas`
- [X] T044 [P] [US5] Adaptar `tests/test_rotas.py` (tirar `pedidos:lancamentos` e `catalogo:situacao`; acrescentar `("automacoes:pagina", [], "/painel/automacoes/")`, `("automacoes:lancar", [], "/painel/automacoes/lancar/")`, `("automacoes:atualizar", [], "/painel/automacoes/atualizar/")`), `tests/test_acesso.py` (a lista de rotas que exigem login troca `pedidos:lancamentos` e `catalogo:situacao` por `automacoes:pagina`) e `tests/test_prefixo.py` (idem na lista de rotas conferidas com o prefixo)
- [X] T045 [US5] Rodar `grep -rn "painel/catalogo/\"\|painel/lancamentos\|Lançamentos SCPI\|catalogo:situacao\|pedidos:lancamentos" --include=*.py --include=*.html --include=*.js .` (fora de `specs/` e `.venv/`) e corrigir o que sobrar; rodar `uv run pytest tests/test_painel.py tests/test_rotas.py tests/test_acesso.py tests/test_prefixo.py`

---

## Phase 8: User Story 6 - Um destino só na barra lateral (Priority: P2)

**Goal**: "Automações" no lugar de "Catálogo" e "Lançamentos SCPI", marcado em todas as abas (o
item já foi trocado em T010).

**Independent Test**: logado, a barra lateral tem "Painel", "Saída avulsa", "Automações", "Curva
ABC" e (equipe) "Cadastros"; em `?aba=lancamento` e `?aba=estoque`, "Automações" tem
`aria-current`.

- [X] T046 [P] [US6] Acrescentar a `tests/test_automacoes.py` (ou ao teste de menu existente, `tests/test_pagina_catalogo.py::test_menu_tem_catalogo_entre_painel_e_cadastros`, renomeado para `test_menu_tem_automacoes_entre_saida_avulsa_e_curva` e movido para `tests/test_automacoes.py`): a ordem dos itens, a ausência de "Catálogo" e "Lançamentos SCPI" e o item atual marcado em `?aba=visao-geral`, `?aba=lancamento` e `?aba=estoque` (com `item_atual` de `tests/test_pagina_catalogo.py`)

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T047 Atualizar `CLAUDE.md`: novo item da arquitetura para o app `automacoes` (página, abas, regiões por `HX-Target`, ações movidas, histórico combinado com os filtros do painel); nos itens de `catalogo` e do lançamento, trocar "página Almoxarifado › Catálogo" e "Almoxarifado › Lançamentos SCPI" por "Automações" e as rotas e views citadas pelas novas; na lista do `interface`, citar que `filtros.js` também serve o histórico
- [X] T048 [P] Atualizar `deploy/VIRADA.md` (passos que citam `painel/catalogo/` e "Lançamentos SCPI" passam a citar `painel/automacoes/` e as abas) e `docs/DESIGN.md` (só se surgiu classe nova em `automacoes.css`)
- [X] T049 Conferir a página no navegador (preview `django` de `.claude/launch.json`) pelos cenários de `specs/004-pagina-automacoes/quickstart.md`: desktop e 375 px sem rolagem horizontal, sem JavaScript (abas empilhadas, "Filtrar" e paginação por links), acompanhamento com execução em andamento sem perder o que foi digitado; screenshot das abas Visão geral e Lançamento; ajustes de UI com `clean-design`/`docs/DESIGN.md`, `ui-ux-pro-max` e `frontend-design`
- [X] T050 Rodar os portões: `uv run pytest`, `uv run ruff check . && uv run ruff format --check .` e `uv run python manage.py makemigrations --check --dry-run`, todos limpos

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** → histórias.
- **US2 (3)** e **US3 (4)** dependem só da Fase 2 e podem andar em paralelo (tocam arquivos
  diferentes, exceto `automacoes/views.py`, `automacoes/urls.py` e `pedidos/templates/pedidos/painel.html`:
  em paralelo, combinar as edições nesses três).
- **US1 (5)** depende de US3 (mexe em `_situacao.html` já sem o histórico e com as rotas novas).
- **US4 (6)** depende de US2 e US3 (os históricos antigos saem nelas) e de US1 apenas pela posição
  do cartão na aba Visão geral.
- **US5 (7)** depende de US2 e US3 (os links foram trocados nelas; aqui ficam os testes e a varredura).
- **US6 (8)** depende só da Fase 2 (T010).
- **Polish (9)** depois de todas.

### Within Each User Story

- Teste antes, falhando; depois a implementação; por fim a rodada de testes da história.
- Mover a view e trocar os templates antes de apagar as rotas antigas (o `{% url %}` de uma rota
  apagada quebra a renderização de todas as páginas que a citam).

### Parallel Opportunities

- T013 e T020 (testes de 404) em paralelo com a adaptação dos testes da mesma história.
- T026 e T027 em paralelo; T032, T033 e T034 em paralelo.
- T043, T044 e T046 em paralelo.
- US2 e US3 inteiras em paralelo, por duas pessoas, combinando `automacoes/views.py`/`urls.py`.

---

## Parallel Example: User Story 4

```bash
# Testes primeiro, juntos:
Task: "T032 Testes puros de LinhaHistorico em tests/test_historico_automacoes.py"
Task: "T033 Testes de consulta e paginação em tests/test_historico_automacoes.py"
Task: "T034 Testes da página com o histórico em tests/test_automacoes.py"
```

## Parallel Example: User Story 2 e User Story 3

```bash
Task: "T012 Adaptar tests/test_pagina_lancamentos.py e tests/test_lancamento_real.py"
Task: "T019 Adaptar tests/test_pagina_catalogo.py e tests/test_robos_avulsos.py"
```

---

## Implementation Strategy

### MVP First

1. Fases 1 e 2: a página Automações já mostra as duas páginas em abas.
2. Fases 3 e 4 (US2 e US3): todas as ações vivem em Automações e as páginas antigas somem. Este é o
   MVP: nada se perdeu, um destino só.
3. **Parar e validar**: quickstart, cenários 3, 4 e 6.

### Incremental Delivery

1. MVP (US2 + US3) → validar.
2. US1 (visão geral com as quatro automações) → validar.
3. US4 (histórico combinado) → validar.
4. US5 e US6 (varredura de links e menu) → Polish → pull request.

### Notes

- Um commit por tarefa ou grupo lógico, em pt-BR.
- Nenhuma migration nova: `makemigrations --check` precisa continuar limpo.
- As regras dos robôs, as travas e o `LANCAMENTO_REAL` não mudam: se um teste de serviço ou de
  disparo quebrar, a mudança foi longe demais.

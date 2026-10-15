---

description: "Tarefas da clareza e segurança da página Lançamentos SCPI"
---

# Tasks: Clareza e segurança da página Lançamentos SCPI

**Input**: documentos de design em `specs/003-lancamentos-scpi-clareza/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R8), data-model.md,
contracts/pagina-lancamentos.md, quickstart.md

**Tests**: obrigatórios (Princípio V): funções puras sem banco (`tests/test_andamento.py`,
`tests/test_scpi_requisicoes.py`), página pelo `client` contra MySQL/MariaDB, nunca navegador. Em
cada fase, escreva os testes primeiro e confira que falham. O que só o navegador mostra (dica por
toque, foco, 375 px) fecha a fase pelo passo correspondente do roteiro manual do `quickstart.md`.

**Organization**: tarefas agrupadas pelas histórias da spec (US1 a US7). As histórias mexem no
mesmo template (`pedidos/templates/pedidos/_lancamentos.html`), então rodam **em sequência**; o
paralelismo fica entre testes puros, CSS e testes de arquivos diferentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem depender de tarefa pendente)
- **[Story]**: a história da spec (US1 a US7)
- Caminhos relativos à raiz do repositório

## Convenções que valem para todas as tarefas

- Textos, nomes de código e commits em pt-BR.
- **Nada do lançamento muda** (FR-022, Princípio III): `scpi/lancamento.py`, `scpi/disparo.py`,
  `servicos.resolver_lote`, as travas, o `LANCAMENTO_REAL` e as mensagens das resoluções
  ("Lote … marcado para não lançar no SCPI.") ficam como estão. Nenhum modelo nem migration.
- O trecho `<section id="lancamentos">` só leva `hx-trigger="every 3s"` com execução em andamento,
  e os formulários de resolução só aparecem sem execução em andamento (FR-011); manter esse
  invariante em toda mudança do template.
- Ordem das seções na página (R8): ação → fila → andamento → travas → histórico.
- Design system Clean: referência fixa `docs/DESIGN.md` + skill `clean-design`, conferida com
  `ui-ux-pro-max` (usabilidade e acessibilidade) e `frontend-design` (hierarquia e screenshot),
  como manda o `CLAUDE.md`. Só tema claro, ícones de `interface/templates/interface/_icone.html`
  (`robo`, `cadeado`, `alerta`, `olho`), estado nunca só por cor, números de pedido em `.mono`.
- Nenhum caminho fixo em template (`{% url %}`/`{% static %}`; `tests/test_prefixo.py`). Scripts
  só no `<head>` com `defer`.

---

## Phase 1: Setup

**Purpose**: partir de uma base verde.

- [X] T001 Rodar `uv run pytest tests/test_pagina_lancamentos.py tests/test_lancamento_real.py tests/test_painel.py tests/test_scpi_requisicoes.py tests/test_resolver_travas.py` e confirmar que passam antes de qualquer mudança

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: o módulo puro de apresentação da execução, usado por US4, US5 e US6.

### Testes (escrever primeiro)

- [X] T002 [P] Criar `tests/test_andamento.py` (sem banco: usar `ExecucaoRobo(...)` não salvo ou `SimpleNamespace` com `simulacao`, `inicio`, `fim`, `situacao`, `resumo`, `log`, `erro`) com os casos de data-model.md: `feitas` (simulação → `resumo["simuladas"]`, real → `resumo["lancadas"]`); `n_de_m` → `"3 de 3"`, `"2 de 3"`, e `None` com `resumo == {}` ou `requisicoes == 0` (nunca `"0 de 0"`); `duracao(inicio, fim)` → `"45 s"`, `"2 min 5 s"`, `"1 h 3 min"`, `"—"` com `fim=None`; `momento(inicio, agora)` → `"hoje, 13:25"`, `"ontem, 13:25"`, `"07/10, 13:25"`, calculado na hora local (`timezone.localtime`), incluindo um caso em que UTC e hora local caem em dias diferentes

### Implementação

- [X] T003 Criar `pedidos/andamento.py` (puro: nada de ORM nem `connection`; docstring do módulo dizendo que transforma uma `ExecucaoRobo` em texto de tela) com `feitas`, `n_de_m`, `duracao` e `momento` conforme T002; ler o `resumo` sempre com `.get(chave, 0)` porque ele pode ser `{}`

**Checkpoint**: `uv run pytest tests/test_andamento.py` verde.

---

## Phase 3: User Story 1 - A ação possível em destaque (Priority: P1) 🎯 MVP

**Goal**: "Simular" em destaque com o lançamento real bloqueado, "Lançar no SCPI" com cadeado e
dica; o inverso com ele liberado; um formulário só com o limite (R1).

**Independent Test**: com `LANCAMENTO_REAL` desligado, "Simular" é o único `botao-primario` e
"Lançar no SCPI" é `type="button"` com a dica; ligado, o inverso.

### Testes (escrever primeiro)

- [X] T004 [P] [US1] Em `tests/test_pagina_lancamentos.py`, com um lote `PENDENTE` (`criar_pedido(atendido=True, linhas=[("PENDENTE", "")])`) e `settings.LANCAMENTO_REAL = False`: exatamente um `botao-primario` na seção de ação e é o "Simular"; o botão "Lançar no SCPI" tem `type="button"`, `aria-disabled="true"`, `aria-describedby="dica-lancamento-real"` e o ícone de cadeado; existe `<span class="dica-flutuante-texto" role="tooltip" id="dica-lancamento-real">Lançamento real bloqueado até a virada: só a simulação roda.</span>`; com `settings.LANCAMENTO_REAL = True`, o primário é "Lançar no SCPI" (`type="submit" name="modo" value="lancar"`) e "Simular" é `botao-secundario`
- [X] T005 [P] [US1] Em `tests/test_pagina_lancamentos.py`: a página não tem mais "Executar com opções" nem `type="radio"`; tem um único `<form>` para `pedidos:lancar` contendo o campo `name="limite"` (`min="1"`, `max="10000"`) e os botões `name="modo" value="simular"` e (liberado) `value="lancar"`; com execução em andamento (`ExecucaoRobo.objects.create()`), os dois botões e o `limite` têm `disabled`, nenhum é `botao-primario` e aparece "Há uma execução em andamento."; sem nenhum lote pendente, os botões e o `limite` têm `disabled` e aparece "Nada aguardando o robô."; ajustar `test_em_andamento_desabilita_botoes_esconde_resolucao_e_acompanha` se a regex do botão desabilitado deixar de casar
- [X] T006 [P] [US1] Em `tests/test_pagina_lancamentos.py`: `client.post(reverse("pedidos:lancar"), {"modo": "simular", "limite": "2"})` chama `iniciar_lancamento` com `simulacao=True, limite=2` (monkeypatch como em `test_lancar_inicia_e_avisa`); `{"modo": "simular", "limite": "0"}` é recusado com a mensagem do `min_value` e não inicia; os testes de `tests/test_lancamento_real.py` (`{}` e `{"modo": "lancar"}` recusados com `LANCAMENTO_BLOQUEADO`, `{"simulacao": "1"}` aceito) continuam passando sem mudança

### Implementação

- [X] T007 [US1] Em `pedidos/forms.py`, tirar o `widget=forms.RadioSelect` e o `initial` do campo `modo` (o template não renderiza o formulário; o modo vem do botão clicado) e atualizar a docstring do módulo; manter `clean_modo` (recusa `lancar` com `LANCAMENTO_BLOQUEADO`) e `da_requisicao` (compatível com `simulacao=1`) iguais
- [X] T008 [US1] Em `pedidos/views/lancamentos.py`, acrescentar ao contexto `pode_executar = pendentes > 0 and not em_andamento` (com `pendentes` ainda vindo de `lotes_pendentes()`; a US2 o troca pela fila) e manter as demais chaves
- [X] T009 [US1] Em `pedidos/templates/pedidos/_lancamentos.html`, trocar o primeiro cartão (os dois `<form>`, o `<details class="executar-opcoes">` e os `campo-dica`) por um único `<form method="post" action="{% url 'pedidos:lancar' %}">` com `{% csrf_token %}`: campo `limite` com rótulo "Só as primeiras" + entrada `type="number" min="1" max="10000" inputmode="numeric" placeholder="todas"` + "requisições" (`disabled` sem `pode_executar`), e os botões: "Simular" (`type="submit" name="modo" value="simular"`, ícone `olho`) e "Lançar no SCPI" (ícone `robo`) copiando o padrão do cartão do painel (`pedidos/templates/pedidos/painel.html`, linhas do `dica-flutuante`): bloqueado → `type="button" aria-disabled="true" aria-describedby="dica-lancamento-real"`, ícone `cadeado` e a dica "Lançamento real bloqueado até a virada: só a simulação roda."; liberado → `type="submit" name="modo" value="lancar"`, `disabled` sem `pode_executar`. `botao-primario` só no botão da ação possível (Simular bloqueado, Lançar liberado) e só com `pode_executar`; o outro é `botao-secundario`. Ao lado, o motivo em texto: "Há uma execução em andamento." ou "Nada aguardando o robô.". Embaixo, um `campo-dica`: "A simulação preenche cada requisição no SCPI e não salva: nenhuma linha muda de estado." e, bloqueado, "O lançamento real é liberado pelo LANCAMENTO_REAL no .env."
- [X] T010 [P] [US1] Em `pedidos/static/pedidos/css/pedidos.css`, apagar as regras de `.executar-opcoes` e acrescentar o layout do formulário de ação (limite em linha com os botões no desktop, quebrando em pilha abaixo de 640 px, sem rolagem horizontal em 375 px); a `.dica-flutuante` vem de `componentes.css`, sem cópia
- [X] T011 [US1] Passos 1, 2 e 5 do roteiro manual do `quickstart.md` (dica por Tab, cursor e toque em 375 px; Enter no botão bloqueado não envia). Se o toque não mostrar a dica (a `.dica-flutuante` é só CSS, `:hover`/`:focus-within`, e o Safari do iPhone não foca `<button>` no toque), corrigir em `interface/static/interface/css/componentes.css` ou com um ouvinte de toque que dê foco ao botão, de modo que valha também para o cartão do painel, e registrar a correção no `docs/DESIGN.md`

**Checkpoint**: US1 entregue sozinha; `uv run pytest tests/test_pagina_lancamentos.py tests/test_lancamento_real.py` verde.

---

## Phase 4: User Story 2 - Ver o que vai ser lançado antes de disparar (Priority: P1)

**Goal**: lista das requisições na fila do robô, com a regra do robô, até 20 e o total (R2, R3).

**Independent Test**: duas requisições pendentes e um lote travado → "2 requisições aguardando o
robô", duas linhas com Nº (link), data, recebedor, centro de custo e materiais; o travado não
aparece na lista.

### Testes (escrever primeiro)

- [X] T012 [P] [US2] Em `tests/test_scpi_requisicoes.py`, testes de `requisicoes.agrupar(linhas)` (puro, com as linhas falsas que o arquivo já usa): devolve `(grupos, travados)` com os grupos na ordem da primeira linha `PENDENTE`; lote com linha `EM_LANCAMENTO`, `VERIFICAR` ou `ERRO`, ou `PENDENTE` com `requisicao_scpi` preenchido, vai para `travados` e não para `grupos`; `LANCADA` e `NAO_LANCAR` são ignoradas; e `selecionar(linhas, centros).requisicoes` tem os mesmos lotes, na mesma ordem, que `agrupar(linhas)[0]` — os testes existentes de `selecionar` continuam passando sem mudança
- [X] T013 [P] [US2] Criar `tests/test_consultas_fila.py` (com banco): montar lotes em todos os casos (só `PENDENTE`; `PENDENTE` + `VERIFICAR`; `PENDENTE` + `ERRO`; `PENDENTE` + `EM_LANCAMENTO`; `PENDENTE` com `requisicao_scpi`; só `LANCADA`; só `NAO_LANCAR`; `PENDENTE` + `LANCADA`) e conferir que os lotes de `consultas.fila_do_robo(limite=100).requisicoes` são exatamente os grupos de `requisicoes.agrupar(list(LinhaSaida.objects.filter(status__in=(PENDENTE, *ESTADOS_TRAVA)).order_by("id")))`, na mesma ordem, e que `total` e `lotes_pendentes()` dão esse número; conferir `data`, `recebedor` e `centro_custo` da primeira linha `PENDENTE` e `materiais` = número de linhas `PENDENTE` do lote; com 3 lotes e `limite=2`, `len(requisicoes) == 2`, `total == 3` e `fora == 1`; conferir com `django_assert_max_num_queries(3)` que a consulta não cresce com o número de lotes
- [X] T014 [P] [US2] Em `tests/test_pagina_lancamentos.py`: com dois lotes `PENDENTE` e um `VERIFICAR`, a página mostra "2 requisições aguardando o robô", uma linha por lote com o Nº em `<a class="mono" href="{% url 'pedidos:detalhe' lote %}">`, a data `d/m/Y`, o recebedor, o centro de custo e o número de materiais, e o lote travado não está na tabela da fila (só nas travas); com 21 lotes `PENDENTE`, 20 linhas e "e mais 1 requisição"; atualizar `test_pagina_mostra_pendentes_travas_e_formulario` (hoje espera "1 lote(s) aguardando o robô.") para "1 requisição aguardando o robô"
- [X] T015 [P] [US2] Em `tests/test_painel.py`, um lote com uma linha `PENDENTE` e outra `VERIFICAR` não conta como aguardando o robô no cartão de lançamentos (o "Simular lançamento" fica desabilitado se for o único) e continua contando "1 para conferir"; o cartão diz "1 requisição aguardando o robô" / "2 requisições aguardando o robô" e, sem nenhuma, "Nada aguardando o robô.", sem "lote" (FR-023); atualizar `test_painel_mostra_cartao_de_lancamentos` em `tests/test_pagina_lancamentos.py` (hoje espera "lote aguardando o robô") e as asserções de `tests/test_painel.py` que citem o texto antigo

### Implementação

- [X] T016 [US2] Em `scpi/requisicoes.py`, extrair de `selecionar` a função pura `agrupar(linhas) -> tuple[dict[str, Requisicao], list[str]]` (o laço que separa `grupos` e `travados` e o filtro `lote not in travados`), com docstring dizendo que é a regra única de "o que está na fila do robô"; `selecionar` passa a chamar `agrupar` e só valida, com o mesmo resultado
- [X] T017 [US2] Em `pedidos/consultas.py`, criar as dataclasses `RequisicaoNaFila(lote, data, recebedor, centro_custo, materiais)` e `Fila(total, requisicoes)` com a propriedade `fora`, e `fila_do_robo(limite=20) -> Fila`: subconsulta `Exists` das linhas do mesmo lote (`OuterRef("lote")`) com `status__in=ESTADOS_TRAVA` ou (`status=PENDENTE` e `requisicao_scpi` diferente de vazio); lotes = `LinhaSaida.objects.filter(status=PENDENTE).exclude(Exists(...)).values("lote").annotate(primeira=Min("id"), materiais=Count("id")).order_by("primeira")`; `total = lotes.count()`; das `limite` primeiras, buscar as linhas `id__in=[primeira…]` numa consulta só para data, recebedor e centro de custo; com `limite=0`, não buscar linhas; docstring dizendo que repete `requisicoes.agrupar` em SQL e que `tests/test_consultas_fila.py` confere que concordam. Importar `ESTADOS_TRAVA` de `scpi.requisicoes` (ou repetir a tupla com o mesmo comentário, se o import criar ciclo)
- [X] T018 [US2] Em `pedidos/consultas.py`, `lotes_pendentes()` passa a devolver `fila_do_robo(limite=0).total`, com a docstring atualizada ("lotes que o robô lançaria agora, pela regra de `requisicoes.agrupar`")
- [X] T019 [US2] Em `pedidos/templates/pedidos/painel.html`, no `atalho-rotulo` do cartão de lançamentos, trocar o `pluralize:"lote aguardando o robô,lotes aguardando o robô"` por `pluralize:"requisição aguardando o robô,requisições aguardando o robô"` e "Nenhum lote aguardando o robô." por "Nada aguardando o robô." (FR-023); o número já vem de `lotes_pendentes()` (T018)
- [X] T020 [US2] Em `pedidos/views/lancamentos.py`, trocar `"pendentes": lotes_pendentes()` por `"fila": fila_do_robo()` e calcular `pode_executar` com `fila.total`
- [X] T021 [US2] Em `pedidos/templates/pedidos/_lancamentos.html`, logo abaixo do formulário de ação, o bloco da fila: `<h2 class="cartao-titulo">Fila do robô</h2>`, a frase `{{ fila.total }} {{ fila.total|pluralize:"requisição aguardando o robô,requisições aguardando o robô" }}` (ou "Nada aguardando o robô." com zero, sem tabela), e com itens uma `tabela` dentro de `tabela-rolagem` com as colunas Nº, Data, Recebedor, Centro de custo, Materiais (`tabela-data` nas datas e números); com `fila.fora`, a linha "e mais {{ fila.fora }} {{ fila.fora|pluralize:"requisição,requisições" }}"
- [X] T022 [P] [US2] Em `pedidos/static/pedidos/css/pedidos.css`, ajustar a tabela da fila para não criar rolagem horizontal na página em 375 px (a rolagem fica dentro da `tabela-rolagem`)
- [X] T023 [US2] Passos 3 e 4 do roteiro manual do `quickstart.md`

**Checkpoint**: US1 + US2 entregues; `uv run pytest tests/test_consultas_fila.py tests/test_scpi_requisicoes.py tests/test_pagina_lancamentos.py tests/test_painel.py` verde.

---

## Phase 5: User Story 3 - Confirmar antes de tirar uma requisição do lançamento (Priority: P1)

**Goal**: "Não lançar" em dois passos, também sem JavaScript, com recusa no servidor sem a
confirmação (R7).

**Independent Test**: num lote travado, POST de `acao=nao_lancar` sem `confirmado` não grava;
com `confirmado=1` grava e mostra a mensagem de sempre.

### Testes (escrever primeiro)

- [X] T024 [P] [US3] Em `tests/test_pagina_lancamentos.py`: num lote `VERIFICAR`, `client.post(reverse("pedidos:resolver", args=[lote]), {"acao": "nao_lancar"}, follow=True)` mostra "Confirme antes de marcar para não lançar." e as linhas continuam `VERIFICAR` com a `mensagem` intacta; com `{"acao": "nao_lancar", "confirmado": "1"}`, as linhas viram `NAO_LANCAR` e aparece "Lote {lote} marcado para não lançar no SCPI." (texto de `resolver_lote`, sem mudança); `acao=liberar` e `acao=lancada` continuam funcionando sem `confirmado`
- [X] T025 [P] [US3] Em `tests/test_pagina_lancamentos.py`: sem execução em andamento, cada trava tem um `<details class="confirmar-nao-lancar">` cujo `<summary>` contém "Não lançar" e, dentro, um `<form>` próprio para `pedidos:resolver` com `{% csrf_token %}`, `<input type="hidden" name="acao" value="nao_lancar">`, `<input type="hidden" name="confirmado" value="1">` e o botão "Confirmar: não lançar", e o aviso "A requisição de {lote} não será lançada no SCPI."; o formulário de resolução ("Informar requisição", "Liberar para relançar") não tem mais nenhum botão `value="nao_lancar"`; e toda resposta que contém `confirmar-nao-lancar` não contém `every 3s` (FR-011)

### Implementação

- [X] T026 [US3] Em `pedidos/views/lancamentos.py`, na view `resolver`: se `request.POST.get("acao") == "nao_lancar"` e `request.POST.get("confirmado") != "1"`, `messages.error(request, "Confirme antes de marcar para não lançar.")` e redirecionar para `pedidos:lancamentos` sem chamar `resolver_lote`; o resto igual
- [X] T027 [US3] Em `pedidos/templates/pedidos/_lancamentos.html`, dentro do bloco `{% else %}` (sem execução em andamento) de cada trava: tirar o botão "Não lançar" do formulário de resolução e, depois dele, acrescentar `<details class="confirmar-nao-lancar">` com `<summary class="botao botao-texto botao-perigo">Não lançar…</summary>` e um painel com `div.aviso.aviso-atencao` ("A requisição de <span class="mono">{{ trava.lote }}</span> não será lançada no SCPI. As linhas ficam marcadas como Não lançar.") e o `<form method="post" action="{% url 'pedidos:resolver' trava.lote %}">` com `{% csrf_token %}`, os dois `hidden` (`acao=nao_lancar`, `confirmado=1`), o botão `type="submit" class="botao botao-perigo"` "Confirmar: não lançar" e um `<button type="button" class="botao botao-texto" data-desistir hidden>Desistir</button>`; atualizar o `{% comment %}` do topo dizendo que a confirmação também fica fora da recarga
- [X] T028 [US3] Em `pedidos/static/pedidos/js/pedidos.js`, um ouvinte de clique **no `document`** (delegação) para `[data-desistir]` que fecha o `<details>` mais próximo (`open = false`) e devolve o foco ao seu `<summary>`; uma função que mostra (`hidden = false`) todos os `[data-desistir]`, chamada no `DOMContentLoaded` **e** no `htmx:after:swap` — quando a execução termina, a recarga do HTMX traz as travas novas, e elas precisam do botão visível também (mesmo padrão de `sincronizarCentro`/`aplicarLembrado`); sem JavaScript, desistir é fechar pelo próprio `summary`; em `pedidos/templates/pedidos/lancamentos.html`, `{% block extra_head %}<script src="{% static 'pedidos/js/pedidos.js' %}" defer></script>{% endblock %}`; conferir que o restante do `pedidos.js` não quebra numa página sem os elementos dos formulários (ele já roda em `detalhe.html` e `recibos.html`)
- [X] T029 [P] [US3] Em `tests/test_pagina_lancamentos.py`, teste no estilo do projeto que lê `finders.find("pedidos/js/pedidos.js")` e confere o gancho `data-desistir`, o fechamento do `details` e que a função que revela o botão está registrada no `htmx:after:swap`
- [X] T030 [P] [US3] Em `pedidos/static/pedidos/css/pedidos.css`, estilo de `.confirmar-nao-lancar` (summary sem o marcador padrão, com o estilo de botão de texto perigoso e foco visível; painel aberto separado por borda, botões em linha que quebram no celular)
- [X] T031 [US3] Passos 10 e 11 do roteiro manual do `quickstart.md` (com e sem JavaScript)

**Checkpoint**: as três histórias P1 entregues.

---

## Phase 6: User Story 4 - Entender uma execução que falhou e o que fazer (Priority: P2)

**Goal**: falha em português, até onde chegou, próximo passo, detalhe técnico recolhido e
"Simular de novo" só na simulação (R5).

**Independent Test**: execução `FALHA` com `erro="Falha inesperada: You cannot call this from an
async context"` → frase em português, `role="alert"`, "Detalhe técnico" fechado com o texto
original, "Simular de novo" na simulação e nenhum atalho no lançamento real.

### Testes (escrever primeiro)

- [X] T032 [P] [US4] Em `tests/test_andamento.py`, `explicar_falha(execucao)` em cada ramo de R5, nos dois modos: `erro == LANCAMENTO_BLOQUEADO` e `"Outro lançamento já está em andamento."` → `frase` igual ao erro, `tecnico=False`; `"Falha inesperada: …"` → "O robô parou por um erro do sistema.", `tecnico=True`; `"Falha inesperada: Timeout 30000ms exceeded…"` → "O SCPI demorou demais para responder e o robô parou."; `log=""`, `resumo={}` e erro qualquer (falha do disparo) → "O robô não chegou a iniciar.", `tecnico=True`; frase de `FalhaCritica` de uma linha → como vem, `tecnico=False`; `ate_onde` → "Chegou a processar 2 de 5 requisições." com `processadas=2, requisicoes=5`, e "Parou antes de começar." com resumo vazio ou `requisicoes=0`; simulação → `proximo_passo` contém "simular de novo" e "Nenhuma linha mudou de estado.", `simular_de_novo=True`; real → `proximo_passo` "Confira as travas abaixo antes de lançar de novo.", `simular_de_novo=False`
- [X] T033 [P] [US4] Em `tests/test_pagina_lancamentos.py`: com a última execução `ExecucaoRobo.objects.create(simulacao=True, situacao="FALHA", fim=agora, erro="Falha inesperada: You cannot call this from an async context", resumo={"requisicoes": 3, "processadas": 1}, log="…")`, a página tem `class="aviso aviso-erro" role="alert"` com "O robô parou por um erro do sistema." e "Chegou a processar 1 de 3 requisições.", o selo escrito "Falhou", um `<details>` sem `open` com "Detalhe técnico" contendo o texto original, e um `<form>` para `pedidos:lancar` com `name="modo" value="simular"` e o botão "Simular de novo"; com `simulacao=False`, não há "Simular de novo" nem outro botão `value="lancar"` além do da ação principal, e há o link `href="#travas"` e um elemento com `id="travas"` na página

### Implementação

- [X] T034 [US4] Em `pedidos/andamento.py`, a dataclass `Falha(frase, ate_onde, proximo_passo, tecnico, simular_de_novo)` e `explicar_falha(execucao) -> Falha | None` (`None` se a situação não é `FALHA`), na ordem de R5; reaproveitar `catalogo.saude.PREFIXO_FALHA_INESPERADA` e o critério de "Timeout" de `resumo_do_erro`, e `scpi.lancamento.LANCAMENTO_BLOQUEADO`, sem mudar nenhum deles
- [X] T035 [US4] Em `pedidos/views/lancamentos.py`, acrescentar `"falha": explicar_falha(execucao) if execucao else None` ao contexto
- [X] T036 [US4] Em `pedidos/templates/pedidos/_lancamentos.html`, no cartão de andamento, trocar o `{% if execucao.erro %}` atual por: com `falha`, `div.aviso.aviso-erro` com `role="alert"`, ícone `alerta`, `falha.frase`, `falha.ate_onde` e `falha.proximo_passo`; com `falha.simular_de_novo`, um `<form method="post" action="{% url 'pedidos:lancar' %}">` com `{% csrf_token %}` e `<button type="submit" name="modo" value="simular" class="botao botao-secundario">Simular de novo</button>` (`disabled` com execução em andamento); sem `simular_de_novo`, um link "Ver as travas" para `#travas`; para o link nunca ficar sem destino, pôr já aqui `id="travas"` no cartão "Travas para conferir" e no `<p class="vazio">` do `{% empty %}`; com `falha.tecnico`, `<details class="detalhe-tecnico"><summary>Detalhe técnico</summary>` com o `execucao.erro` e o `log_recente` num `<pre class="log-execucao mono">`
- [X] T037 [P] [US4] Em `pedidos/static/pedidos/css/pedidos.css`, `.detalhe-tecnico pre` com `white-space: pre-wrap` e `overflow-wrap: anywhere` (erro longo quebra linha e não cria rolagem horizontal)
- [X] T038 [US4] Passos 8 e 9 do roteiro manual do `quickstart.md`

**Checkpoint**: falha legível; `uv run pytest tests/test_andamento.py tests/test_pagina_lancamentos.py` verde.

---

## Phase 7: User Story 5 - Andamento resumido numa frase (Priority: P2)

**Goal**: a última execução numa frase, quem iniciou e a duração, só contadores diferentes de
zero, atalho para as travas, progresso "requisição N de M" (R4).

**Independent Test**: simulação concluída de 3 → "Simulação de hoje, HH:MM, concluída: 3 de 3
requisições preenchidas.", só "3 simuladas", sem "Falhas 0".

### Testes (escrever primeiro)

- [X] T039 [P] [US5] Em `tests/test_andamento.py`: `contadores(resumo, simulacao)` devolve só os ≠ 0, na ordem lançadas/simuladas, "com erro" (`falhas`), "para verificar" (`verificar`), "deixadas de fora" (`ignoradas`), com singular/plural ("1 lançada", "3 simuladas", "1 para verificar"); tudo zero → `[]`; `precisa_conferir` → `True` com `falhas` ou `verificar` > 0 ou falha de lançamento real, `False` para falha de simulação sem pendências; `frase(execucao, agora, interrompida)` em cada caso de R4: concluída ("Simulação de hoje, 13:25, concluída: 3 de 3 requisições preenchidas."), com pendências ("Lançamento de hoje, 13:25, concluído com pendências: 1 de 2 requisições lançadas."), nada a lançar ("… concluída: nada a lançar."), em andamento com total ("Simulação em andamento: requisição 2 de 5." com `processadas=1`, nunca passando de `requisicoes`), em andamento sem total ("… em andamento: preparando a fila."), interrompida ("… interrompida: o robô parou sem registrar o fim."), falha (começa pelo modo e momento e diz "falhou")
- [X] T040 [P] [US5] Em `tests/test_pagina_lancamentos.py`: com uma simulação `SUCESSO` com `resumo={"requisicoes": 3, "processadas": 3, "simuladas": 3}` e `fim` 2 min depois do `inicio`, a página mostra a frase, "Iniciada por" com o nome, a duração "2 min", "3 simuladas", e não mostra "Falhas", "Ignoradas", "Lançadas" nem a `<dl>` antiga de nove itens; com um lançamento `ATENCAO` (`lancadas=1, verificar=1`), mostra "1 lançada", "1 para verificar" e o link `href="#travas"`; com execução em andamento (`resumo={"requisicoes": 5, "processadas": 1}`), "requisição 2 de 5" e `hx-trigger="every 3s"`; com uma execução antiga sem fim e sem a trava (como em `test_execucao_longa_com_a_trava_segue_acompanhada_e_sem_trava_e_interrompida`), a frase diz "interrompida"; ajustar as asserções existentes que dependiam da `<dl>` antiga (o registro recente continua na página)

### Implementação

- [X] T041 [US5] Em `pedidos/andamento.py`, `contadores`, `precisa_conferir` e `frase` conforme T039 (o particípio vem do modo: "preenchidas" na simulação, "lançadas" no real; "Simulação … concluída" / "Lançamento … concluído")
- [X] T042 [US5] Em `pedidos/views/lancamentos.py`, montar no contexto um objeto/dicionário `andamento` com `frase(execucao, agora, execucao.interrompida)`, `contadores(...)`, `duracao(...)`, `precisa_conferir(...)` (só com `execucao`), sem consultar a trava mais de uma vez por pedido além do que já se faz
- [X] T043 [US5] Em `pedidos/templates/pedidos/_lancamentos.html`, reescrever o cartão "Andamento": a linha de selos (situação escrita e modo, como hoje), a `andamento.frase` em destaque, uma linha `texto-secundario` "Iniciada por {nome ou linha de comando} · {duração}", os contadores como uma lista em linha (`<ul class="contadores">` com um `<li class="selo selo-neutro">` por contador; estado escrito no texto, não na cor; a revisão de UI do T056 pode trocar a classe se o DESIGN.md pedir) só quando houver, o link "Ver as travas" (`#travas`) com `precisa_conferir` (sem duplicar o da falha), e o registro recente num `<details>` "Registro da execução" (com `open` enquanto em andamento; com falha técnica, o registro fica só no "Detalhe técnico"); apagar a `<dl class="dados">` de nove itens
- [X] T044 [P] [US5] Em `pedidos/static/pedidos/css/pedidos.css`, estilo da frase e dos contadores (em linha, quebrando sem rolagem horizontal; o cartão inteiro cabe numa tela de 375 × 812)
- [X] T045 [US5] Passos 6, 7 e 14 do roteiro manual do `quickstart.md`

**Checkpoint**: andamento resumido; US1–US5 entregues.

---

## Phase 8: User Story 6 - Histórico que conta o que cada execução fez (Priority: P3)

**Goal**: colunas "Requisições" (N de M) e "Duração" no histórico (R6).

**Independent Test**: uma simulação de 3 de 3 e um lançamento de 2 de 3 → "3 de 3" e "2 de 3";
execução sem fim → duração "—".

### Testes (escrever primeiro)

- [X] T046 [P] [US6] Em `tests/test_pagina_lancamentos.py`: com uma simulação `SUCESSO` (`requisicoes=3, simuladas=3`, 45 s) e um lançamento `ATENCAO` (`requisicoes=3, lancadas=2`), o cabeçalho da tabela "Últimas execuções" tem "Requisições" e "Duração" e não tem "Lançadas", "Falhas" nem "Verificar"; as linhas mostram "3 de 3" com "45 s" e "2 de 3"; uma execução sem `fim` mostra "—" na duração; o modo continua escrito ("Simulação" / "Lançamento real")

### Implementação

- [X] T047 [US6] Em `pedidos/views/lancamentos.py`, passar ao template, para cada execução do histórico, `n_de_m` e `duracao` (lista de pares ou atributos anexados aos objetos, sem consulta nova)
- [X] T048 [US6] Em `pedidos/templates/pedidos/_lancamentos.html`, na tabela "Últimas execuções", trocar as colunas Lançadas/Falhas/Verificar por Requisições (`n_de_m` ou "—") e Duração (`tabela-data`), e ajustar o `colspan` da linha vazia

**Checkpoint**: histórico legível.

---

## Phase 9: User Story 7 - Textos na língua do almoxarifado (Priority: P3)

**Goal**: "requisição" no lugar de "lote", plural certo, sem rótulo repetido, travas vazias numa
linha, página vazia sem cartões vazios (R8).

**Independent Test**: com 1 e com 2 requisições na fila e sem travas, nenhum "lote(s)" na
página, sem rótulo "SCPI", e só "Nenhuma trava para conferir".

### Testes (escrever primeiro)

- [X] T049 [P] [US7] Em `tests/test_pagina_lancamentos.py`, num cenário com fila, uma trava e uma execução concluída **com `log=""`** (o registro é escrito pelo robô e cita lotes; fica fora da regra, FR-020) e sem mensagem de resolução na sessão: a página inteira não contém `lote(s)`, `lote ` nem `Lote ` (comparação sem diferenciar maiúsculas, descontando o `{% comment %}` que não é renderizado) nem `<p class="rotulo-secao">SCPI</p>`; sem travas, contém `Nenhuma trava para conferir` com `id="travas"` e não contém o título "Travas para conferir"; com uma trava, o cartão tem `id="travas"` e o Nº do pedido em `.mono`; sem execução e com fila vazia, contém "Nada aguardando o robô." e "Nenhuma execução ainda." e não contém os títulos "Andamento" nem "Últimas execuções"; `POST pedidos:lancar` com `limite=1` mostra "Limite: 1 requisição." e com `limite=2` "Limite: 2 requisições."

### Implementação

- [X] T050 [US7] Em `pedidos/templates/pedidos/lancamentos.html`, apagar o `{% block rotulo %}SCPI{% endblock %}` (como nas páginas do catálogo)
- [X] T051 [US7] Em `pedidos/templates/pedidos/_lancamentos.html`: sem travas, só `<p class="texto-secundario" id="travas">Nenhuma trava para conferir.</p>` fora de cartão (o `id="travas"` já existe desde a US4; manter nos dois casos); sem execução registrada, um único `<p class="texto-secundario">Nenhuma execução ainda.</p>` no lugar dos cartões "Andamento" e "Últimas execuções"; revisar os textos restantes trocando "lote" por "requisição" ("Lançamento em andamento" → "Há uma execução em andamento.", "Lote N de M" já trocado na US5)
- [X] T052 [US7] Em `pedidos/views/lancamentos.py`, na view `lancar`, trocar `f" Limite: {limite} requisição(ões)."` por plural certo ("requisição" com 1, "requisições" com mais), nos dois ramos
- [X] T053 [US7] Passos 12, 13 e 15 do roteiro manual do `quickstart.md`

**Checkpoint**: todas as histórias entregues.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T054 Atualizar `CLAUDE.md`, no parágrafo do lançamento no SCPI: a página Lançamentos SCPI tem um formulário só (modo pelo botão, limite à vista, sem "Executar com opções"; com o bloqueio, "Simular" é a ação principal e "Lançar no SCPI" mostra a dica, como o cartão do painel), a fila do robô (`consultas.fila_do_robo`, SQL que repete `requisicoes.agrupar`, conferido por teste; `lotes_pendentes` segue a mesma regra), o "Não lançar" em dois passos (`<details>` com formulário próprio e `confirmado=1`; a view recusa sem ele) e `pedidos/andamento.py` (puro: frase, contadores, duração, "N de M", explicação da falha com o detalhe técnico recolhido e "Simular de novo" só na simulação)
- [X] T055 [P] Conferir que `tests/test_prefixo.py` cobre a página (nenhum caminho fixo nos templates alterados) e rodar `uv run pytest tests/test_prefixo.py tests/test_acesso.py tests/test_rotas.py`
- [X] T056 Revisão de UI com as três skills (`clean-design` + `docs/DESIGN.md`, `ui-ux-pro-max`, `frontend-design`): screenshots da página em desktop e em 375 px nos estados bloqueado com fila, em andamento, falha de simulação, trava com a confirmação aberta e vazia; corrigir o que divergir do DESIGN.md (contraste, foco visível, alvos de toque de 44 px, hierarquia de um só primário)
- [X] T057 Rodar os portões: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run python manage.py makemigrations --check --dry-run`, todos limpos

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup; bloqueia US4, US5 e US6 (usam `pedidos/andamento.py`). US1, US2 e US3 não dependem dela e podem começar logo depois do Setup.
- **Histórias**: todas mexem em `_lancamentos.html` e `views/lancamentos.py`, então rodam **em sequência**, na ordem de prioridade: US1 → US2 → US3 → US4 → US5 → US6 → US7.
- **Polish (Phase 10)**: depois das histórias que forem entregues.

### User Story Dependencies

- **US1 (P1)**: nenhuma; usa `lotes_pendentes()` como está até a US2.
- **US2 (P1)**: depois da US1 (troca `pendentes` por `fila` no `pode_executar`).
- **US3 (P1)**: independente das outras no comportamento; em sequência só pelo template.
- **US4 (P2)**: Phase 2. Cria o link `#travas` e o `id="travas"` que ele aponta (T036); a US5 e a US7 reaproveitam.
- **US5 (P2)**: Phase 2 e US4 (o cartão de andamento é reescrito por cima da falha).
- **US6 (P3)**: Phase 2.
- **US7 (P3)**: depois das demais (revisa os textos finais e os estados vazios).

### Within Each User Story

- Testes primeiro, falhando; depois a lógica pura, a view, o template, o CSS; por fim o passo do roteiro manual.

### Parallel Opportunities

- T002 (testes puros) em paralelo com T004–T006 (testes da US1).
- Dentro de cada história, os testes marcados [P] estão em arquivos ou trechos independentes e podem ser escritos juntos; o CSS [P] pode ser feito junto do template.
- T012, T013, T014 e T015 (testes da US2) em quatro arquivos diferentes.
- T032 e T039 (testes puros da US4 e da US5) podem ser escritos juntos em `tests/test_andamento.py` antes das duas fases.

---

## Parallel Example: User Story 2

```text
Juntos:
  T012 testes de requisicoes.agrupar em tests/test_scpi_requisicoes.py
  T013 concordância SQL × agrupar em tests/test_consultas_fila.py
  T014 fila na página em tests/test_pagina_lancamentos.py
  T015 contagem do cartão em tests/test_painel.py
Depois, em sequência: T016 → T017 → T018 → T019 → T020 → T021 (T022 junto do T021)
```

## Parallel Example: User Story 4

```text
Juntos:
  T032 explicar_falha em tests/test_andamento.py
  T033 falha na página em tests/test_pagina_lancamentos.py
Depois: T034 → T035 → T036 (T037 junto do T036)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (base verde).
2. US1: a ação possível em destaque e o formulário único — resolve o primeiro problema da auditoria
   (o destaque num botão morto) sem depender de mais nada.
3. **Parar e validar** com os passos 1, 2 e 5 do quickstart.

### Incremental Delivery

1. US1 → US2 → US3: as três P1 juntas fecham a segurança (ver a fila antes de disparar; "Não
   lançar" com confirmação). É o ponto mínimo recomendado para abrir o PR, se for dividir.
2. Phase 2 → US4 → US5: falha e andamento legíveis.
3. US6 → US7: histórico e textos.
4. Phase 10: `CLAUDE.md`, revisão de UI e portões.

Cada história termina com a suíte da página verde; nenhuma deixa a página quebrada para a seguinte.

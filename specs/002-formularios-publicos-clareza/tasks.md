---

description: "Tarefas da clareza e facilidade de uso dos formulários públicos de pedido"
---

# Tasks: Clareza e facilidade de uso dos formulários públicos de pedido

**Input**: documentos de design em `specs/002-formularios-publicos-clareza/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/telas-publicas.md,
quickstart.md

**Tests**: obrigatórios para o que roda no servidor (Princípio V): templates e contexto pelo
`client`, regras e `buscar` sem banco. Em cada fase, escreva os testes primeiro e confira que
falham. O `pedidos.js` é testado como o projeto já faz (`test_gaveta_segue_a_largura…` em
`tests/test_carrinho.py`): lendo o arquivo-fonte por `finders.find("pedidos/js/pedidos.js")` e
conferindo os ganchos e as chamadas essenciais, sem abrir navegador. Cada história com JS também
termina pelo passo correspondente do roteiro manual do `quickstart.md`.

**Organization**: tarefas agrupadas pelas histórias da spec (US1 a US8), cada uma implementável
e testável sozinha depois da fase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem depender de tarefa pendente)
- **[Story]**: a história da spec (US1 a US8)
- Caminhos relativos à raiz do repositório

## Convenções que valem para todas as tarefas

- Textos, nomes de código e commits em pt-BR.
- **Nenhum texto de erro muda** (FR-008); nenhuma regra, limite, numeração ou gravação muda
  (FR-028). `registrar_pedido` é chamado igual.
- Formulário enviável sem JavaScript; o que é só do JS fica escondido (`hidden`) até o JS mostrar.
- Design system Clean (`docs/DESIGN.md`, skill `clean-design`): só tema claro, ícones de
  `interface/templates/interface/_icone.html`, classes do vocabulário (`campo-com-erro`,
  `campo-erro`, `aviso-erro`, `botao-primario`, `botao-secundario`, `visually-hidden`). Estado
  nunca só por cor.
- Nenhum caminho fixo em template (`{% url %}`/`{% static %}`), por causa do prefixo
  `/almoxarifado` (`tests/test_prefixo.py`).
- `pedidos.js`: ES5, dentro do IIFE existente, ouvintes delegados no `document`, como o resto do
  arquivo. Acesso ao `localStorage` sempre em `try/catch`.
- Fonte das decisões: `research.md` (R1–R12), `data-model.md`, `contracts/telas-publicas.md`.

---

## Phase 1: Setup

**Purpose**: partir de uma base verde e saber os nomes de evento do HTMX 4.

- [X] T001 Rodar `uv run pytest`, `uv run ruff check .` e `uv run ruff format --check .` na branch `002-formularios-publicos-clareza` e registrar que a base está verde (se algo falhar, parar e avisar o João).
- [X] T002 Conferir se a branch `feat/busca-rola-celular` já entrou no `main` (`git log origin/main --oneline | grep "painel da busca entra no fluxo"`); se entrou, trazer o `main` para esta branch antes de mexer em `pedidos/static/pedidos/js/pedidos.js`; se não, avisar o João que haverá conflito provável no `pedidos.js` e seguir.
- [X] T003 Ler o HTMX vendorizado (procurar o arquivo em `interface/static/interface/js/`) e anotar no topo da seção nova do `pedidos.js` os nomes exatos dos eventos usados: antes da requisição (`htmx:before:request`?), depois do swap (`htmx:after:swap`, já usado) e como obter o elemento que disparou a requisição no `detail` do evento (research R9).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: o `campo` dos erros e o contexto `erros_por_campo`, de que US2 depende e que mudam
`regras.py`/`servicos.py`/`views/publico.py`, arquivos tocados por várias histórias.

**⚠️ CRITICAL**: terminar antes das histórias, para não haver conflito nesses três arquivos.

### Testes (escrever primeiro)

- [X] T004 [P] Em `tests/test_regras_pedidos.py`, acrescentar testes de que `validar_pedido_limpeza` e `validar_pedido_ab` devolvem `Erro(None, "Informe o nome completo.", campo="solicitante")`, os dois erros de destino com `campo="destino"` ("Escolha o destino dos materiais na lista de centros de custo." e 'Destino "…" não está na lista de centros de custo.') e "Adicione ao menos um material ao pedido." com `campo=None`; e que erros de material têm `campo=None` (data-model, tabela "Quem preenche `campo`").
- [X] T005 [P] Em `tests/test_registrar_pedido.py`, acrescentar teste de que os erros de tamanho de `servicos.erros_de_tamanho` têm `campo` `"solicitante"` (rótulo "Nome completo"), `"destino"` ("Destino") e `"obs"` ("Observação"), e o de excesso de materiais tem `campo=None`.
- [X] T006 [P] Em `tests/test_formularios_publicos.py`, acrescentar teste de que o envio recusado por nome vazio e destino vazio põe no contexto `erros_por_campo == {"solicitante": ["Informe o nome completo."], "destino": ["Escolha o destino dos materiais na lista de centros de custo."]}` (usar `r.context`).

### Implementação

- [X] T007 Em `pedidos/regras.py`, acrescentar a `Erro` o campo `campo: str | None = None` (depois de `texto`, para `Erro(codigo, texto)` continuar valendo) e, em `validar_pedido_limpeza` e `validar_pedido_ab`, trocar o auxiliar `campo(t)` por um que receba o nome do campo: nome → `"solicitante"`, destino → `"destino"`, pedido vazio → `None`. Nenhum texto muda.
- [X] T008 Em `pedidos/servicos.py`, fazer `erros_de_tamanho` preencher `campo` a partir do rótulo (`{"Nome completo": "solicitante", "Destino": "destino", "Observação": "obs"}`; rótulo fora do mapa → `None`, o que mantém a saída avulsa como está) e deixar o erro de excesso de materiais com `campo=None`.
- [X] T009 Em `pedidos/views/publico.py`, no `de_volta` do envio recusado, montar `erros_por_campo` (`{campo: [texto, ...]}` dos erros com `campo`) e passá-lo ao contexto; em `_contexto`, incluir `erros_por_campo: {}` como padrão.
- [X] T010 Rodar os testes de T004–T006 e a suíte de pedidos (`uv run pytest tests/test_regras_pedidos.py tests/test_registrar_pedido.py tests/test_formularios_publicos.py tests/test_revisao_pedidos.py`) e confirmar verde.

**Checkpoint**: erros sabem a qual campo pertencem; nada visível mudou.

---

## Phase 3: User Story 1 - Enviar o pedido pela gaveta no celular (Priority: P1) 🎯 MVP

**Goal**: no celular, a gaveta envia; a barra diz o próximo passo; com o pedido vazio, não convida
a abrir.

**Independent Test**: quickstart, passo 2 e parte do 3 (celular, enviar pela gaveta).

### Testes (escrever primeiro)

- [X] T011 [US1] Em `tests/test_carrinho.py`, atualizar `test_carrinho_tem_barra_e_gaveta` e `test_botoes_do_pedido_tem_icone` e acrescentar testes pelo endpoint `pedidos:carrinho` (contrato, tabela "Barra e gaveta"): sem linhas → texto "Nenhum material adicionado", sem `data-carrinho-abrir` e sem `data-carrinho-enviar`; com 1 linha → "Seu pedido · 1 material", botão `data-carrinho-abrir` "Revisar e enviar", `data-carrinho-enviar` `type="button"` "Enviar pedido" com classe `botao-primario`, `data-carrinho-continuar` "Adicionar mais materiais" com classe `botao-secundario`; com 2 linhas → "2 materiais". Saída avulsa (endpoint `pedidos:avulsa_carrinho`, com login): barra e gaveta como hoje ("Ver pedido", "Continuar pedindo"), sem `data-carrinho-enviar` (FR-029). Teste de fonte do `pedidos.js`: contém `data-carrinho-enviar` e `requestSubmit`.

### Implementação

- [X] T012 [US1] Em `pedidos/templates/pedidos/_carrinho.html`, só com `fluxo.publico` (a saída avulsa mantém a barra de hoje, FR-029), refazer a `.carrinho-barra`: com linhas, ícone + "Seu pedido · N material/materiais" (`pluralize`) + botão `data-carrinho-abrir` "Revisar e enviar" (mantendo `aria-haspopup`, `aria-controls`, `aria-expanded`); sem linhas, só "Nenhum material adicionado". Manter o selo "Corrigir" quando há `codigos_erro`.
- [X] T013 [US1] Em `pedidos/templates/pedidos/_carrinho.html`, no fim da gaveta (só com `fluxo.publico` e com linhas), pôr `<button type="button" class="botao botao-primario botao-bloco carrinho-so-gaveta" data-carrinho-enviar>` com ícone `enviar` e "Enviar pedido", e trocar o `data-carrinho-continuar` para `botao-secundario` com o texto "Adicionar mais materiais" (sem linhas, o continuar fica como único botão). Na avulsa, o "Continuar pedindo" fica como hoje. Atualizar o comentário do topo do arquivo.
- [X] T014 [US1] Em `pedidos/static/pedidos/css/pedidos.css`, ajustar a barra para o estado vazio (texto sem botão, mesma altura, para a folga da busca não mudar) e o espaçamento entre "Enviar pedido" e "Adicionar mais materiais" na gaveta; os botões da gaveta só aparecem com `[data-gaveta]` (classe `carrinho-so-gaveta`, como hoje).
- [X] T015 [US1] Em `pedidos/static/pedidos/js/pedidos.js`, no ouvinte de clique da gaveta: `[data-carrinho-enviar]` → fechar a gaveta (`fecharGaveta`) e chamar `form.requestSubmit(botaoFinal)`, onde `form` é `[data-formulario-pedido]` e `botaoFinal` é `.acoes-final button[type=submit]` (research R2). Em `abrirGaveta`, copiar o texto do `botaoFinal` para o `[data-carrinho-enviar]` (preservando o ícone), para o rótulo divergente aparecer igual. O botão não existe na saída avulsa (T013), cujo `<form>` não tem `data-formulario-pedido`; se `form` ou `botaoFinal` não forem achados, o JS ignora o clique.
- [X] T016 [US1] Rodar `uv run pytest tests/test_carrinho.py tests/test_formularios_publicos.py` e conferir no navegador o passo 2 do `quickstart.md` (celular 375 px: barra vazia, barra com 1 material, gaveta com os dois botões, envio pela gaveta chega ao sucesso; caso divergente mostra o rótulo longo na gaveta).

**Checkpoint**: no celular, o pedido termina pela gaveta.

---

## Phase 4: User Story 2 - Ver cada erro junto do campo (Priority: P1)

**Goal**: resumo focável com links no topo e mensagem embaixo de cada campo com erro.

**Independent Test**: quickstart, passo 3.

### Testes (escrever primeiro)

- [X] T017 [US2] Em `tests/test_formularios_publicos.py`, acrescentar testes do envio recusado com nome e destino vazios (contrato, "Envio recusado"): resumo com `data-resumo-erros`, `role="alert"`, `tabindex="-1"`, título "Faltam 2 coisas para enviar", a mensagem "Corrija os itens abaixo e envie de novo.", links `href="#solicitante"` e `href="#destino"` com os textos de hoje; `#solicitante` e `#destino` com `aria-invalid="true"` e `aria-describedby` contendo `solicitante-erro`/`destino-erro`; `<p id="solicitante-erro" class="campo-erro">` com o texto e o ícone de alerta; o `.campo` com `campo-com-erro`. Outro teste: com 1 erro, título "Falta 1 coisa para enviar". Outro: erro de material (quantidade inválida) aparece no resumo sem link e a linha mantém o selo "Corrigir" (ajustar `test_erros_mantem_o_preenchido_e_marcam_o_item` se preciso). Outro: mensagem sem lista (token expirado, `MENSAGEM_EXPIRADO`) mostra só a mensagem, sem título de contagem. Teste de fonte do `pedidos.js`: contém `data-resumo-erros`, `preventScroll` e `aria-invalid`.

### Implementação

- [X] T018 [US2] Em `pedidos/templates/pedidos/_formulario.html`, trocar o bloco `{% if mensagem %}` pelo resumo do contrato: `div.aviso.aviso-erro[role=alert][tabindex=-1][data-resumo-erros]`, com título de contagem só quando há `erros` ("Falta 1 coisa para enviar" / "Faltam N coisas para enviar"), a `mensagem` e a lista (`erro.campo` → `<a href="#{{ erro.campo }}">`; sem campo → texto).
- [X] T019 [US2] Em `pedidos/templates/pedidos/_formulario.html`, nos campos `#solicitante`, `#destino` e `#obs`: com `erros_por_campo.<campo>`, acrescentar `campo-com-erro` ao `.campo`, `aria-invalid="true"` ao controle, `<campo>-erro` ao `aria-describedby` e, abaixo do controle, `<p id="<campo>-erro" class="campo-erro">` com `_icone.html` `alerta` e os textos. Usar um template tag/filtro simples se o acesso por chave no template ficar repetitivo (em `pedidos/templatetags/pedidos_extras.py`). O `#obs` hoje usa `aria-labelledby="obs-titulo"`; manter.
- [X] T020 [US2] Em `pedidos/static/pedidos/css/pedidos.css` (ou só reaproveitar `componentes.css`), estilizar o título do resumo, os links do resumo (sublinhados, cor do erro) e o ícone na `campo-erro`; conferir que `.campo-com-erro .campo-entrada` vale também para o `textarea` e para o combo do `dropdown.js` (o `<input>` continua sendo o controle).
- [X] T021 [US2] Em `pedidos/static/pedidos/js/pedidos.js`: depois do `htmx:after:swap` em `#formulario`, se houver `[data-resumo-erros]`, dar `focus({preventScroll: true})` nele; no `input`/`change` de um controle com `aria-invalid="true"` dentro de `[data-formulario-pedido]`, remover `aria-invalid` e a classe `campo-com-erro` do `.campo` pai (a mensagem fica). Para links do resumo apontando para o destino, garantir que o foco vai para o `<input>` do combo (a âncora já faz isso; só conferir).
- [X] T022 [US2] Rodar `uv run pytest tests/test_formularios_publicos.py` e conferir no navegador o passo 3 do `quickstart.md` (gaveta fecha, foco no resumo, link leva ao campo, borda some ao digitar; e o passo 10 sem JavaScript: erros nos campos e no topo).

**Checkpoint**: MVP completo (US1 + US2): pedido enviável e erros compreensíveis no celular.

---

## Phase 5: User Story 3 - Escolher o formulário certo pela página inicial (Priority: P2)

**Goal**: títulos pelo conteúdo, com exemplos, sem "Formulário 1/2" nem "AB" nas telas públicas.

**Independent Test**: quickstart, passo 1.

- [X] T023 [US3] Em `tests/test_formularios_publicos.py`, atualizar `test_inicio_mostra_os_dois_formularios` e acrescentar: a página inicial não contém "Formulário 1", "Formulário 2" nem "Materiais AB"; contém "Limpeza, copa e escritório" e "Ferramentas, peças e materiais", uma linha de exemplos em cada cartão e "Mostra o estoque de cada material."; `GET /pedido/ab/` tem `<title>` e `<h1>` "Ferramentas, peças e materiais" e o rótulo "Pedido de materiais"; `GET /pedido/limpeza/` tem "Limpeza, copa e escritório". Conferir que `tests/test_painel.py` e `tests/test_telegram.py` continuam esperando "Materiais AB" (nome interno não muda).
- [X] T024 [US3] Em `pedidos/fluxos.py`, trocar o `titulo` de limpeza para "Limpeza, copa e escritório" e o de AB para "Ferramentas, peças e materiais", e remover o campo `formulario` do `Fluxo` (e dos três `Fluxo(...)` em `FLUXOS`). Não mexer em `pedidos/models.py` (`Origem`) nem em `pedidos/telegram.py`.
- [X] T025 [US3] Em `pedidos/templates/pedidos/formulario.html`, trocar `{{ fluxo.formulario }}` no bloco `rotulo` por "Pedido de materiais".
- [X] T026 [US3] Em `pedidos/templates/pedidos/inicio.html`, refazer os dois cartões (contrato, "GET /"): sem "Formulário N"; título igual ao `Fluxo.titulo`; linha de exemplos ("Ex.: detergente, café, papel A4, caneta" e "Ex.: luva, fita veda-rosca, lâmpada, cano" — conferir com uma busca no catálogo local que esses materiais existem em cada formulário e trocar o exemplo que não existir); no AB, "Mostra o estoque de cada material.". Manter o aviso final.
- [X] T027 [US3] Rodar `uv run pytest tests/test_formularios_publicos.py tests/test_painel.py tests/test_telegram.py` e conferir o passo 1 do `quickstart.md` no celular e no desktop.

---

## Phase 6: User Story 4 - Nome e destino lembrados no aparelho (Priority: P2)

**Goal**: o aparelho lembra nome e destino do último pedido registrado, com "Não é você? Limpar".

**Independent Test**: quickstart, passos 6 e 7.

- [X] T028 [US4] Em `tests/test_formularios_publicos.py`, acrescentar testes: o formulário tem `[data-esquecer-solicitante]` com `hidden` e o texto "Não é você? Limpar"; a tela de sucesso (e a de reenvio) tem `data-lembrar-solicitante` com o nome e `data-lembrar-destino` com o destino como está no cadastro (usar o caso de `test_destino_digitado_e_gravado_como_esta_no_cadastro`); o envio recusado não tem `data-lembrar-*`. Teste de fonte do `pedidos.js`: contém `almoxarifado.solicitante`, `localStorage` só dentro de `try` (conferir que todo `localStorage` aparece em linha precedida por um `try {` no mesmo bloco, ou ao menos que há `try` e `catch` na seção), `data-lembrar-solicitante` e `data-esquecer-solicitante`.
- [X] T029 [US4] Em `pedidos/templates/pedidos/_formulario.html`, no passo 1, acrescentar o `<button type="button" class="botao botao-texto" data-esquecer-solicitante hidden>` "Não é você? Limpar" (perto do nome).
- [X] T030 [US4] Em `pedidos/templates/pedidos/_sucesso.html`, pôr `data-lembrar-solicitante="{{ resposta.pedido.solicitante }}"` e `data-lembrar-destino="{{ resposta.pedido.destino }}"` na `section.sucesso-pedido`.
- [X] T031 [US4] Em `pedidos/static/pedidos/js/pedidos.js`, seção "dados lembrados" (research R5, data-model "Dados lembrados no navegador"): chave `almoxarifado.solicitante`, valor JSON `{"solicitante": string, "destino": string}`, tudo em `try/catch`. (a) No `DOMContentLoaded` e no `htmx:after:swap`, se houver `[data-lembrar-solicitante]`, gravar. (b) No `DOMContentLoaded` e no `htmx:after:swap` de um formulário novo (`[data-formulario-pedido]` sem `[data-resumo-erros]`), preencher `#solicitante` e `#destino` só se estiverem vazios; o destino só se o valor estiver entre os `option` de `#destinos`; disparar `input` e `change` nos campos preenchidos (para o `dropdown.js`); se preencheu algo, tirar o `hidden` de `[data-esquecer-solicitante]`. (c) Clique em `[data-esquecer-solicitante]`: esvaziar os dois campos (com `input`/`change`), remover a chave e esconder o botão. Leitura com JSON inválido → tratar como nada lembrado.
- [X] T032 [US4] Rodar `uv run pytest tests/test_formularios_publicos.py` e conferir os passos 6 e 7 do `quickstart.md` (inclusive "Fazer outro pedido" já preenchido, destino removido do cadastro fica vazio, aba anônima sem erro).

---

## Phase 7: User Story 5 - Não perder o pedido sem querer (Priority: P2)

**Goal**: sair com materiais no pedido pede confirmação.

**Independent Test**: quickstart, passo 5.

- [X] T033 [US5] Em `pedidos/static/pedidos/js/pedidos.js`, ouvinte `beforeunload` (research R6): se existir `[data-formulario-pedido] .carrinho-linha[data-codigo]` e não houver envio em curso, `e.preventDefault()` e `e.returnValue = ""`. Marcar "envio em curso" no evento `submit` do `[data-formulario-pedido]` (envio sem HTMX). Não registrar na saída avulsa: só quando a página tem `[data-formulario-pedido]` (o `<form>` de `avulsa.html` não tem esse atributo, então a saída avulsa não ganha o aviso).
- [X] T034 [US5] Em `tests/test_formularios_publicos.py`, teste de fonte do `pedidos.js`: contém `beforeunload` e `.carrinho-linha[data-codigo]`; e teste de que `avulsa.html` renderizado não tem `data-formulario-pedido`. Depois, conferir o passo 5 do `quickstart.md` (com material: "Trocar tipo de material" e voltar pedem confirmação; sem material e na tela de sucesso: não) e o passo 11 (saída avulsa não pede).

---

## Phase 8: User Story 6 - Campos e destino mais simples (Priority: P3)

**Goal**: sem asteriscos, observações "(opcional)", dica curta do destino com "O que pôr aqui?".

**Independent Test**: quickstart, passo 8.

- [X] T035 [US6] Em `tests/test_formularios_publicos.py`, atualizar `test_destino_fica_junto_do_nome_com_a_orientacao` e `test_formulario_em_tres_passos` e acrescentar: rótulos "Nome completo" e "Destino dos materiais" sem `*`; título do passo 3 "Observações (opcional)"; `#destino-dica` com "Setor, posto, viatura ou placa."; `<details class="campo-ajuda">` com `<summary>O que pôr aqui?</summary>` e a explicação de hoje dentro.
- [X] T036 [US6] Em `pedidos/templates/pedidos/_formulario.html`, tirar os `*` dos dois rótulos, mudar o `h2#obs-titulo` para "Observações <span class=\"texto-secundario\">(opcional)</span>", trocar a dica do destino pela curta e mover a explicação longa para o `<details class="campo-ajuda">` logo abaixo; manter `aria-describedby="destino-dica"` (mais o `destino-erro` da T019).
- [X] T037 [P] [US6] Em `pedidos/static/pedidos/css/pedidos.css`, estilo do `.campo-ajuda` (summary como link discreto com seta, texto em `campo-dica`, área de toque ≥ 44 px de altura).
- [X] T038 [US6] Rodar `uv run pytest tests/test_formularios_publicos.py` e conferir os passos 8 e 10 do `quickstart.md`.

---

## Phase 9: User Story 7 - Busca e carrinho mais claros (Priority: P3)

**Goal**: pedíveis primeiro, "disponíveis", unidade ao lado da quantidade, "Adicionado", sem
código no carrinho público.

**Independent Test**: quickstart, passos 2 e 4.

### Testes (escrever primeiro)

- [X] T039 [P] [US7] Em `tests/test_carrinho.py`, acrescentar teste puro de `fluxos.buscar` no fluxo AB: com um material sem estoque antes de dois com estoque no catálogo, os com estoque vêm primeiro e os bloqueados no fim, mantendo a ordem relativa; e teste de que, com mais de 50 achados e os pedíveis além do 50º, os pedíveis entram nos 50 (a ordenação é antes do corte, research R7).
- [X] T040 [P] [US7] Em `tests/test_carrinho.py`, atualizar os testes que esperam "Estoque: 10 UN" (`test_endpoint_de_busca_ab` e o da linha ~246) para "10 UN disponíveis"; acrescentar: o resultado pedível mostra `<span class="quantidade-unidade">UN</span>` depois do controle; o carrinho do formulário público não mostra o código do material (`016.002.098` ou o do cenário) e o da saída avulsa mostra (endpoint `pedidos:avulsa_carrinho`, com login); a página do formulário tem uma única `[data-anuncio-adicionado]` com `role="status"`, fora de `#resultados`. Teste de fonte do `pedidos.js`: contém `data-anuncio-adicionado` e `Adicionado`.

### Implementação

- [X] T041 [US7] Em `pedidos/fluxos.py`, em `buscar`, ordenar os achados com `sorted(..., key=lambda i: bool(motivo_bloqueio(fluxo, i)))` (estável) antes de cortar em `LIMITE_RESULTADOS` (import local de `pedidos.carrinho.motivo_bloqueio`, como em `resultados`); em `resultados`, o `info` do AB passa a `f"{i.disponivel} {i.unidade} disponíveis"` (sem unidade: `f"{i.disponivel} disponíveis"`). Atualizar a docstring de `buscar`.
- [X] T042 [US7] Em `pedidos/templates/pedidos/_resultados.html`, depois do `div.quantidade`, `{% if r.item.unidade %}<span class="quantidade-unidade texto-secundario">{{ r.item.unidade }}</span>{% endif %}`.
- [X] T043 [US7] Em `pedidos/templates/pedidos/_carrinho.html`, mostrar o `<span class="mono …">{{ linha.codigo }}</span>` só com `{% if not fluxo.publico %}`.
- [X] T044 [US7] Em `pedidos/templates/pedidos/_materiais.html`, depois do `#resultados` (fora dele), `<p class="visually-hidden" role="status" data-anuncio-adicionado></p>`.
- [X] T045 [US7] Em `pedidos/static/pedidos/css/pedidos.css`, alinhar `.quantidade-unidade` ao lado do controle e o estado "Adicionado" do botão (ícone + texto, sem mudar a largura de forma que empurre o layout).
- [X] T046 [US7] Em `pedidos/static/pedidos/js/pedidos.js` (research R9, com os nomes de evento anotados na T003): ao iniciar a requisição de um botão com `hx-vals` contendo `adicionar`, guardar o botão; depois do swap do `#carrinho`, se não há `#carrinho [data-carrinho-alerta].aviso-erro`, trocar o conteúdo do botão por ícone de check + "Adicionado" por 2 s e restaurar o conteúdo original; escrever "<nome do material> adicionado ao pedido." no `[data-anuncio-adicionado]` (nome tirado de `.material-titulo strong` do mesmo `li`).
- [X] T047 [US7] Rodar `uv run pytest tests/test_carrinho.py` e conferir os passos 2, 4 e 11 do `quickstart.md`.

---

## Phase 10: User Story 8 - Página pública mais limpa e sucesso conferível (Priority: P3)

**Goal**: cabeçalho público sem link interno; sucesso com destino e lista de materiais.

**Independent Test**: quickstart, passos 6 e 9.

- [X] T048 [US8] Em `tests/test_formularios_publicos.py`, acrescentar: o cabeçalho (`header.publico-topo`) da página inicial e do formulário não tem "Área do almoxarifado", e o rodapé tem; a tela de sucesso mostra o destino e cada material com quantidade e unidade (pedido com 2 materiais); o reenvio mostra a mesma lista. Conferir `test_sucesso_no_estilo_clean` e `test_envio_valido_mostra_o_numero`.
- [X] T049 [P] [US8] Em `interface/templates/interface/base_publico.html`, tirar o link "Área do almoxarifado" do `header.publico-topo` (manter no rodapé) e atualizar o comentário do topo.
- [X] T050 [US8] Em `pedidos/views/publico.py`, no sucesso, passar `itens` (os itens de `resposta.pedido`, na ordem gravada, com material, quantidade e unidade; ver em `pedidos/models.py` os nomes dos campos do item e reaproveitar a formatação pt-BR de quantidade já usada nos recibos ou no detalhe, sem criar formatação nova).
- [X] T051 [US8] Em `pedidos/templates/pedidos/_sucesso.html`, depois do número, mostrar o destino ("Destino: …") e a lista (`ul` com nome, quantidade e unidade); manter avisos e botões de hoje.
- [X] T052 [US8] Rodar `uv run pytest tests/test_formularios_publicos.py` e conferir os passos 6 e 9 do `quickstart.md`.

- [X] T057 [US7] Adicionar em dois passos nos formulários públicos (FR-030, pedido do João na revisão): em `tests/test_carrinho.py`, testes da estrutura (`data-adicionar`, abrir, área `qtd-area-N`, confirmar com `hx-post` dizendo "Adicionar" sem JavaScript, cancelar), da saída avulsa sem os dois passos e da fonte do `pedidos.js`; em `pedidos/templates/pedidos/_resultados.html`, a estrutura do contrato; em `pedidos/static/pedidos/js/pedidos.js`, abrir/fechar (uma por vez), "Confirmar"/"Atualizar" (este troca a linha do pedido pelo `change`, na captura do clique), Esc, rótulo "Alterar" e o "Adicionado"/"Atualizado" no botão de abrir; em `pedidos/static/pedidos/css/pedidos.css`, os estados fechado e aberto.
- [X] T058 [US7] Alterar a quantidade do pedido em dois passos nos formulários públicos (FR-031, pedido do João na revisão): testes em `tests/test_carrinho.py` (estrutura, `hx-trigger="confirmar-quantidade"`, avulsa com `change`, fonte do `pedidos.js`); `_carrinho.html` com texto, "Alterar", área do − / + com "Confirmar" e ✕; `pedidos.js` com abrir/confirmar/cancelar, Enter, Esc sem fechar a gaveta, e a alteração aberta desfeita no envio; `pedidos.css` com os dois estados.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T053 Atualizar o `CLAUDE.md` (seção de arquitetura de `pedidos` e `interface`): a gaveta envia pelo botão final (`requestSubmit`); `Erro.campo` e `erros_por_campo`; nome e destino lembrados no `localStorage` (`almoxarifado.solicitante`), só depois de pedido registrado; aviso `beforeunload` com pedido em montagem; títulos públicos dos formulários ("Limpeza, copa e escritório", "Ferramentas, peças e materiais") enquanto o nome interno continua "Materiais AB"; resultados com pedíveis primeiro, antes do corte de 50.
- [X] T054 Se `docs/DESIGN.md` listar classes por componente, acrescentar `campo-ajuda` e `quantidade-unidade`.
- [X] T055 Rodar os quatro portões do `quickstart.md` (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python manage.py makemigrations --check --dry-run`) e confirmar tudo limpo.
- [ ] T056 Percorrer o roteiro manual completo do `quickstart.md` (passos 1–12) no celular (375 px) e no desktop, nos dois formulários e na saída avulsa, incluindo teclado e sem JavaScript; anotar e corrigir o que divergir do contrato.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sem dependência.
- **Foundational (fase 2)**: depois do Setup; bloqueia as histórias (mexe em `regras.py`,
  `servicos.py` e `views/publico.py`).
- **US1 a US8 (fases 3–10)**: depois da fase 2. Ordem recomendada: prioridade (P1 → P2 → P3).
- **Polish (fase 11)**: depois das histórias escolhidas.

### User Story Dependencies

- **US1 (P1)**: só a fase 2.
- **US2 (P1)**: fase 2 (usa `erros_por_campo`). A gaveta fechar no envio recusado vem da US1
  (T015); sem ela, US2 continua testável pelo botão do fim.
- **US3 (P2)**: independente.
- **US4 (P2)**: independente; o "Não é você?" mora no passo 1, ao lado do que a US2 e a US6 mexem
  (mesmo arquivo, fazer em sequência).
- **US5 (P2)**: independente (só JS).
- **US6 (P3)**: independente; a T036 soma o `destino-erro` da T019 ao `aria-describedby`, então
  fazer depois da US2.
- **US7 (P3)**: independente.
- **US8 (P3)**: independente.

### Arquivos compartilhados (evitar paralelo)

- `pedidos/templates/pedidos/_formulario.html`: T018, T019, T029, T036 — em sequência.
- `pedidos/templates/pedidos/_carrinho.html`: T012, T013, T043 — em sequência.
- `pedidos/static/pedidos/js/pedidos.js`: T015, T021, T031, T033, T046 — em sequência.
- `pedidos/static/pedidos/css/pedidos.css`: T014, T020, T037, T045 — em sequência (a T037 só é [P]
  se nenhuma outra tarefa de CSS estiver em andamento).
- `tests/test_formularios_publicos.py` e `tests/test_carrinho.py`: testes de histórias diferentes
  no mesmo arquivo — escrever em sequência.

### Parallel Opportunities

- Fase 2: T004, T005, T006 (arquivos de teste diferentes).
- US7: T039 e T040 juntos (mesmo arquivo, mas blocos novos independentes; se houver conflito,
  em sequência); T041 em paralelo com T042/T043/T044 (arquivos diferentes).
- US8: T049 em paralelo com T050.
- Entre histórias, com mais de uma pessoa: US3 (`fluxos.py`, `inicio.html`, `formulario.html`) e
  US8 (`base_publico.html`, `_sucesso.html`, `views/publico.py`) não se cruzam com US1/US2.

## Parallel Example: User Story 7

```text
Task: "T039 teste de buscar (pedíveis primeiro, antes do corte) em tests/test_carrinho.py"
Task: "T041 ordenação e texto 'disponíveis' em pedidos/fluxos.py"
Task: "T042 unidade ao lado da quantidade em pedidos/templates/pedidos/_resultados.html"
Task: "T044 região de anúncio em pedidos/templates/pedidos/_materiais.html"
```

## Implementation Strategy

### MVP First (US1 + US2)

1. Fase 1 (Setup) e fase 2 (Foundational).
2. Fase 3 (US1) e fase 4 (US2).
3. **Parar e validar**: passos 2, 3 e 10 do `quickstart.md`. Já resolve os dois problemas de
   prioridade alta; dá para abrir o PR aqui, se o João quiser entregar em partes.

### Incremental Delivery

1. MVP (US1 + US2).
2. US3 + US4 + US5 (P2): entendimento e conveniência.
3. US6 + US7 + US8 (P3): acabamento.
4. Polish (fase 11) antes do merge.

---

description: "Tarefas da implementação do de/para de códigos e da curva ABC consolidada"
---

# Tasks: De/para de códigos e curva ABC consolidada

**Input**: documentos de design em `specs/001-depara-curva-abc/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios. O Princípio V da constituição exige teste automatizado para toda mudança de
comportamento. Em cada fase, escreva os testes primeiro e confira que falham antes de implementar.

**Organization**: tarefas agrupadas por história da spec, para cada uma ser implementada e testada
sozinha.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem depender de tarefa pendente)
- **[Story]**: a história da spec (US1 a US4)
- Caminhos relativos à raiz do repositório (projeto Django único; testes em `tests/`)

## Convenções que valem para todas as tarefas

- Nomes de código, textos, mensagens e commits em português (pt-BR).
- Códigos comparados por `norm_u` (`pedidos/regras.py`); quantidades e valores em `Decimal`.
- Funções de `catalogo/depara.py` e `catalogo/curva.py` são puras: sem ORM, sem `django.db`.
- Testes rodam contra MySQL/MariaDB (`uv run pytest`), nunca SQLite, e nunca abrem o navegador.
- Interface no design system Clean (`docs/DESIGN.md`, skill `clean-design`); classe e situação
  sempre com texto; códigos com a classe `.mono`.
- Fonte das regras: `spec.md` (FR-001 a FR-022), `research.md` (D1 a D12), `data-model.md` e
  `contracts/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: partir de uma base verde e confirmar a regra das migrations.

- [X] T001 Rodar `uv run pytest`, `uv run ruff check .` e `uv run ruff format --check .` no branch `001-depara-curva-abc` e registrar que a base está verde antes de qualquer mudança (se algo falhar, parar e avisar).
- [X] T002 Confirmar em `deploy/VIRADA.md` e com o João que o passo 3 (importação das planilhas no servidor) não foi feito; com isso, toda mudança de modelo desta funcionalidade regenera `catalogo/migrations/0001_initial.py` (research D11). Não criar migration `0002`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelos, regras puras de consolidação e a agregação das saídas, de que todas as
histórias dependem.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

### Testes da fundação (escrever primeiro)

- [X] T003 [P] Escrever `tests/test_depara.py` (parte pura, sem banco), cobrindo `validar_par`:
  - formato `000.000.000` nos dois códigos;
  - antigo ≠ novo;
  - fator "maior que 0";
  - cada mensagem de erro.

  E cobrindo `resolver_canonicos`:
  - código sem par é canônico de si mesmo com fator 1;
  - cadeia A → N → M dá M;
  - fator acumulado é o produto (5 × 2 = 10);
  - ciclo levanta erro citando os códigos;
  - comparação por `norm_u`.

  E `consolidar`: soma ocorrências e valor sem mudança e multiplica a quantidade pelo fator.
- [X] T004 [P] Escrever `tests/test_curva.py` (parte pura) para `periodo(hoje, meses)`:
  - `inicio = max(date(2026, 1, 1), hoje − meses)` e `fim = hoje`;
  - devolve se o início foi limitado a 01/01/2026;
  - dias contados de forma inclusiva: `(fim − inicio).days + 1`.
- [X] T005 [P] Escrever em `tests/test_modelos_curva.py` (com banco):
  - `ConfiguracaoCurva.atual()` cria a linha com os padrões 12, 30 e 90 e devolve sempre a mesma;
  - `ParDePara` recusa `antigo` repetido no banco;
  - `ParametroReposicao` recusa prazo e cobertura vazios ao mesmo tempo.

### Implementação da fundação

- [X] T006 Em `catalogo/models.py`, criar `ParDePara` como em `data-model.md`:
  - `antigo` texto (30), obrigatório, formato `000.000.000`, **único** (sem 1:N, FR-003);
  - `novo` texto (30), obrigatório, formato `000.000.000`, diferente de `antigo`;
  - `fator` decimal (10,4), padrão 1, maior que 0;
  - `observacao` texto (255), opcional;
  - `origem` com as escolhas `PLANILHA` e `SISTEMA`;
  - `atualizado_em` automático.

  O `clean` chama as funções de `catalogo/depara.py` e confere ciclo contra os pares gravados.
  `verbose_name` "par de/para".
- [X] T007 Em `catalogo/models.py`, criar `ConfiguracaoCurva`, de linha única:
  - `janela_meses` padrão 12, ≥ 1;
  - `prazo_entrega_dias` padrão 30, ≥ 1;
  - `cobertura_alvo_dias` padrão 90, ≥ 1;
  - classmethod `atual()`, que cria a linha com os padrões se faltar.
- [X] T008 Em `catalogo/models.py`, criar `ParametroReposicao` e ajustar o resto:
  - `material` `OneToOneField(Material, on_delete=PROTECT)`;
  - `prazo_entrega_dias` e `cobertura_alvo_dias` inteiros opcionais, ≥ 1, vazio = valor geral;
  - `clean` exige pelo menos um dos dois.

  Acrescentar `DEPARA = "DEPARA", "Pares de/para"` a `Importacao.Tipo`. Trocar a docstring de
  `SaidaSCPI` para dizer que ela equivale à aba `Saídas` da planilha (FR-022).
- [X] T009 Regenerar `catalogo/migrations/0001_initial.py`:
  - apagar e rodar `uv run python manage.py makemigrations catalogo`;
  - recriar o banco local (`migrate catalogo zero` + `migrate`);
  - conferir `makemigrations --check --dry-run` limpo.
- [X] T010 [P] Criar `catalogo/depara.py` (puro):
  - `FORMATO_CODIGO` (regex `^\d{3}\.\d{3}\.\d{3}$`);
  - `validar_par(antigo, novo, fator) -> list[str]`;
  - `resolver_canonicos(pares) -> dict[str, tuple[str, Decimal]]`, que leva o código normalizado a
    (canônico, fator acumulado) e levanta `CicloDePara`;
  - `consolidar(linhas, canonicos) -> list[LinhaConsolidada]`, dataclass com canônico,
    ocorrências, qtd e valor.

  Fazer passar o `tests/test_depara.py` (T003).
- [X] T011 [P] Criar `catalogo/curva.py` com `INICIO_DADOS_CONFIAVEIS = date(2026, 1, 1)` e
  `periodo(hoje, meses) -> Periodo` (dataclass com inicio, fim, dias, limitado). Fazer passar o
  `tests/test_curva.py` (T004).
- [X] T012 Criar `catalogo/consultas_curva.py` (com ORM):
  - `canonicos()` lê os `ParDePara` numa consulta e chama `resolver_canonicos`;
  - `saidas_por_codigo(periodo)` agrega `SaidaSCPI` por `cadpro` entre `inicio` e `fim` (`Count`,
    `Sum("qtd")`, `Sum("valor")`) numa consulta;
  - `consolidado(periodo)` devolve as linhas consolidadas e a reconciliação (ocorrências e valor
    antes e depois, códigos antes e canônicos depois).

  Testar em `tests/test_modelos_curva.py` que os totais antes e depois são iguais (SC-003).

**Checkpoint**: a fundação está pronta, e as histórias podem começar.

---

## Phase 3: User Story 1 - Manter o de/para e ver o formulário AB consolidado (Priority: P1) 🎯 MVP

**Goal**: pares mantidos no admin, com validação; o formulário AB mostra cada material uma vez, pelo
canônico, ordenado pelas ocorrências consolidadas.

**Independent Test**: com saídas nos códigos `A` e `N`, cadastrar `A → N` no admin e conferir que o
catálogo AB mostra só `N`, na posição da soma das saídas.

### Testes da história 1 (escrever primeiro)

- [X] T013 [P] [US1] Em `tests/test_catalogos.py`, cobrir os cenários 1, 2 e 5 da história 1 da spec:
  - 30 saídas em A e 20 em N, com o par `A → N`: um item N com 50, sem A;
  - cadeia A → N → M;
  - remover o par volta a separar.

  E também:
  - o saldo mostrado é o do canônico (FR-014);
  - as exclusões atuais continuam (sem cadastro, oculto, grupo oculto, na limpeza);
  - só saídas dentro do período contam;
  - o limite de `django_assert_max_num_queries` em `test_ab_nao_faz_uma_consulta_por_material`
    sobe de 5 para 7 (configuração e pares; feito assim na implementação).
- [X] T014 [P] [US1] Em `tests/test_depara.py` (parte com banco), cobrir o admin de pares pelo
  `client` logado como equipe. Recusas, com a mensagem de cada uma:
  - formato inválido;
  - antigo igual ao novo;
  - segundo destino para o mesmo antigo, com a mensagem citando o destino atual (cenário 3);
  - ciclo (cenário 4);
  - fator 0 ou negativo.

  E também:
  - aviso (não bloqueia) quando `novo` não tem `Material`;
  - origem vira `SISTEMA` ao criar ou alterar;
  - existe `LogEntry` da alteração.
- [X] T015 [P] [US1] Em `tests/test_saude.py`, cobrir:
  - código canônico sem cadastro aparece como problema;
  - código antigo com par não aparece mais como "sem cadastro".

### Implementação da história 1

- [X] T016 [US1] Em `catalogo/admin.py`, registrar `ParDePara`:
  - `list_display` antigo, novo, nome do novo (do `Material`, se houver), fator, origem,
    atualizado em;
  - `search_fields` antigo e novo; `list_filter` origem; `origem` só leitura;
  - `save_model` grava `origem=SISTEMA` e, se o novo não existe em `Material`, chama
    `messages.warning` com "O código {novo} ainda não está no cadastro do SCPI.".

  A validação vem do `clean` do modelo (T006).
- [X] T017 [US1] Em `catalogo/catalogos.py`, reescrever `catalogo_ab()`:
  - período de `periodo(hoje, ConfiguracaoCurva.atual().janela_meses)`;
  - ranking de `consultas_curva.consolidado(periodo)`, ordenado por ocorrências decrescentes e
    código;
  - um item por canônico, com o `Material` do canônico e o saldo dele;
  - mesmas exclusões e contadores de `CatalogoAB` (`codigos`, `na_limpeza`, `ocultos`,
    `sem_cadastro`).

  Atualizar a docstring do módulo. Fazer passar o T013.
- [X] T018 [US1] Em `catalogo/saude.py`, fazer a lista de "sem cadastro" e as contagens do
  formulário AB virem do `catalogo_ab()` consolidado. Fazer passar o T015.

**Checkpoint**: a história 1 funciona sozinha. O formulário AB já está correto, mesmo sem a carga
da planilha.

---

## Phase 4: User Story 2 - Trazer os pares da planilha (Priority: P1)

**Goal**: o comando `importar_depara` carrega os pares da planilha exportada, com ensaio, relatório e
travas (`contracts/importar_depara.md`).

**Independent Test**: carregar um `.xlsx` de exemplo num banco sem pares e conferir o total, os
fatores, as correções e o relatório dos recusados.

### Testes da história 2 (escrever primeiro)

- [X] T019 [P] [US2] Criar `tests/depara_exemplo.py` com `abas_depara()` e reaproveitar o
  `salvar_xlsx` de `tests/planilha_exemplo.py`. As abas:
  - "Planilha de mapeamento depara", com as colunas "Nome", "Código Antigo" e "Código Novo";
  - `DEPARA`, com "Código Antigo", "Código Novo", "Código Canônico" e "Fator p/ Qtd".

  As linhas cobrem: par válido, "PRODUTO NOVO", traço, vazio, antigo repetido, antigo = novo,
  ciclo, correção na `DEPARA` que vence o espelho e fator 5.
- [X] T020 [P] [US2] Escrever `tests/test_importar_depara.py`, cobrindo os cenários 1 a 4 da
  história 2 e cada item de `contracts/importar_depara.md`:
  - aceita o nome de aba com barra;
  - aba ou coluna ausente: erro sem gravar;
  - recusados vão para o relatório com linha, aba e motivo;
  - primeira ocorrência vence, com aviso;
  - `--dry-run` não grava nem cria `Importacao`;
  - a carga substitui todos os pares com origem `PLANILHA` e cria `Importacao` `DEPARA` com
    `linhas` e `avisos`.

  E as recusas, sem alterar nada:
  - com par de origem `SISTEMA`;
  - com `LogEntry` de par depois do fim da última carga bem-sucedida;
  - com a trava ocupada.

  Recusa sai com código de saída diferente de zero (`CommandError`).

### Implementação da história 2

- [X] T021 [US2] Em `implantacao/planilha.py`, acrescentar o parâmetro `abas: dict[str, tuple[str, ...]] = ABAS` a `ler_xlsx`, sem mudar o comportamento atual. Os testes existentes (`tests/test_planilha_leitura.py`) precisam continuar passando.
- [X] T022 [US2] Criar `implantacao/depara.py`, sem banco:
  - `ler_pares(caminho) -> CargaDePara` lê as duas abas, aceitando "Planilha de mapeamento depara"
    ou "Planilha de mapeamento de/para";
  - aplica as regras 1 a 4 do contrato, com `validar_par` e `resolver_canonicos` de
    `catalogo/depara.py`;
  - devolve os pares aceitos e a lista de avisos (com aba, linha e motivo).
- [X] T023 [US2] Criar `implantacao/management/commands/importar_depara.py`:
  - opções `--arquivo` (obrigatória) e `--dry-run`;
  - trava com `scpi.execucao.trava(trava_importacao("DEPARA"))`;
  - recusa se houver `ParDePara` com origem `SISTEMA` ou `LogEntry` do content type de `ParDePara`
    depois do `fim` da última `Importacao` `DEPARA` com sucesso;
  - grava numa transação: apaga todos os pares e cria os aceitos com origem `PLANILHA`;
  - cria a `Importacao` `DEPARA` com `linhas`, `avisos`, `inicio`, `fim` e `situacao`;
  - no `--dry-run`, roda a gravação dentro de `transaction.atomic()` com `set_rollback(True)` e não
    cria `Importacao`;
  - imprime o relatório do contrato; recusa vira `CommandError`.

  Fazer passar o T020.

**Checkpoint**: as histórias 1 e 2 funcionam. O sistema pode receber os ~400 pares da planilha.

---

## Phase 5: User Story 3 - Consultar as curvas ABC consolidadas (Priority: P2)

**Goal**: página Curva ABC com as abas Frequência, Valor e Pendentes, o período e a reconciliação
(`contracts/paginas.md`).

**Independent Test**: com saídas e pares conhecidos, conferir a ordem, os percentuais e a classe
contra um cálculo à mão.

### Testes da história 3 (escrever primeiro)

- [X] T024 [P] [US3] Em `tests/test_curva.py` (parte pura), cobrir `curva(linhas, chave)`:
  - ordem decrescente pela chave, com desempate pelo código;
  - percentual e acumulado;
  - classe A com acumulado ≤ 0,78, B com ≤ 0,95 e C no restante, incluindo os valores exatos de
    fronteira;
  - total zero dá lista vazia.

  E `pendentes(...)`: código com saída, sem par, com material oculto ou sem cadastro, ordenado
  por valor decrescente.
- [X] T025 [P] [US3] Criar `tests/test_pagina_curva.py`, cobrindo:
  - login obrigatório;
  - as abas `?aba=frequencia|valor|pendentes`;
  - `?meses=N` válido e inválido (volta ao padrão, com mensagem);
  - o aviso "Os dados anteriores a 01/01/2026 não entram nos cálculos.";
  - a reconciliação na página;
  - "Nenhuma saída no período.";
  - o link para criar o par na aba Pendentes só para `is_staff`;
  - o item "Curva ABC" no menu.

### Implementação da história 3

- [X] T026 [US3] Em `catalogo/curva.py`, implementar `curva(linhas, chave) -> list[LinhaCurva]` (posição, canônico, ocorrências, qtd, valor, percentual, acumulado, classe) e `pendentes(...)` (research D5, D10). Fazer passar o T024.
- [X] T027 [US3] Em `catalogo/consultas_curva.py`, acrescentar `descricoes(codigos)` (nome e unidade do `Material`, numa consulta) e `pendentes_do_periodo(periodo)` (pares, saídas e materiais ocultos ou ausentes).
- [X] T028 [US3] Em `catalogo/admin.py`, registrar `ConfiguracaoCurva`, sem incluir quando já existe linha e sem excluir.
- [X] T029 [US3] Em `catalogo/views.py` e `catalogo/urls.py`, criar a view `curva` (`login_required`), rota `path("curva/", views.curva, name="curva")`:
  - lê `aba` e `meses`;
  - monta período, reconciliação e a tabela da aba (a de reposição fica para a US4).
- [X] T030 [P] [US3] Criar os templates, sobre `base_almoxarifado.html`, com as abas pelo
  `abas.js` como a página Catálogo:
  - `catalogo/templates/catalogo/curva.html`;
  - `_curva_tabela.html`, para Frequência e Valor;
  - `_curva_pendentes.html`.

  Colunas, cabeçalho e textos de `contracts/paginas.md`. Classe em texto, códigos `.mono`.
- [X] T031 [P] [US3] Em `interface/templates/interface/_icone.html`, acrescentar o ícone Lucide
  `grafico` (bar-chart). Em `interface/navegacao.py`, acrescentar
  `ItemMenu("Curva ABC", "catalogo:curva", "grafico")` depois de "Catálogo". Fazer passar o T025.

**Checkpoint**: as curvas e os pendentes podem ser consultados. A planilha já não é necessária para
a curva ABC.

---

## Phase 6: User Story 4 - Saber o que repor (Priority: P3)

**Goal**: aba Reposição com consumo, estoque, estoque de segurança, ponto de pedido, quanto pedir,
cobertura e situação; prazo e cobertura ajustáveis por material.

**Independent Test**: para um material com consumo e saldo conhecidos, conferir os valores contra a
FR-019; mudar o prazo de entrega do material muda o estoque de segurança e o ponto de pedido.

### Testes da história 4 (escrever primeiro)

- [X] T032 [P] [US4] Em `tests/test_curva.py` (parte pura), cobrir `reposicao(...)` com os
  cenários 1 a 4 da história 4 da spec:
  - consumo 600 em 300 dias, saldo 100, prazo 30 e cobertura 90 dão estoque de segurança 60, ponto
    de pedido 120, quanto pedir 240, cobertura 50 e "comprar";
  - prazo 45 dá estoque de segurança 90 e ponto de pedido 180;
  - saldo 0 dá "esgotado";
  - fator 5.

  E também: arredondamento meio para cima no estoque de segurança e no ponto de pedido, teto no
  quanto pedir, e "em estoque" acima do ponto de pedido.
- [X] T033 [P] [US4] Em `tests/test_pagina_curva.py`, cobrir a aba `?aba=reposicao`:
  - colunas;
  - estoque = saldo do canônico + saldos dos antigos que apontam para ele;
  - prazo e cobertura do `ParametroReposicao` marcados como próprios do material;
  - situação em texto.

### Implementação da história 4

- [X] T034 [US4] Em `catalogo/curva.py`, implementar `reposicao(consolidada, estoque, prazo, cobertura, dias) -> LinhaReposicao` com as fórmulas da FR-019 e da research D6 e a situação da FR-020. Fazer passar o T032.
- [X] T035 [US4] Em `catalogo/consultas_curva.py`, acrescentar `estoques_por_canonico(canonicos)` (saldo do canônico + saldos dos antigos, numa consulta) e `parametros_por_material()` (numa consulta).
- [X] T036 [US4] Em `catalogo/admin.py`, registrar `ParametroReposicao` (`autocomplete_fields = ["material"]`, `list_display` material, prazo, cobertura, `search_fields` código e nome do material).
- [X] T037 [US4] Na view `curva` (`catalogo/views.py`), ligar a aba `reposicao` e criar `catalogo/templates/catalogo/_curva_reposicao.html` com as colunas de `contracts/paginas.md`. Fazer passar o T033.

**Checkpoint**: todas as histórias funcionam sozinhas.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: documentação, portões da constituição e validação final.

- [X] T038 [P] Em `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`:
  - trocar "substitui `MOV_NORM`" por "equivale à aba `Saídas`" na linha da `SaidaSCPI`;
  - atualizar a linha "Curva ABC" da tabela para citar a consolidação pelo de/para (FR-022).
- [X] T039 [P] Em `deploy/VIRADA.md`:
  - acrescentar, depois da carga inicial do catálogo, o passo "exportar a planilha MAPEAMENTO
    DE/PARA CONSOLIDADO e rodar `importar_depara --dry-run`, depois sem `--dry-run`";
  - registrar que a planilha de mapeamento não é desativada até a carga ser conferida (FR-022);
  - trocar "primeiro dia do histórico que a curva ABC usa" por 01/01/2026.
- [X] T040 [P] Atualizar o `CLAUDE.md`:
  - em `catalogo`: de/para, `depara.py`, `curva.py`, `consultas_curva.py`, página Curva ABC,
    `ConfiguracaoCurva` e `ParametroReposicao`;
  - em `implantacao`: `importar_depara` e a trava contra pares editados;
  - o comando novo na seção de comandos.
- [X] T041 Rodar os portões: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run python manage.py makemigrations --check --dry-run`; todos limpos.
- [X] T042 Seguir as seções 2, 3, 5 e 6 do `specs/001-depara-curva-abc/quickstart.md` no banco local e lembrar o João de fazer a seção 4 (conferência com a `ABC_FREQ_CONSOL`, SC-002) com o `.xlsx` real.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sem dependências.
- **Foundational (fase 2)**: depende da fase 1 e bloqueia todas as histórias. O T009 (migration)
  depende de T006 a T008; o T012 depende de T009, T010 e T011.
- **Histórias (fases 3 a 6)**: dependem da fase 2.
- **Polish (fase 7)**: depende das histórias que forem entregues.

### User Story Dependencies

- **US1 (P1)**: só da fundação.
- **US2 (P1)**: só da fundação. Usa `validar_par` e `resolver_canonicos` (T010) e o modelo
  `ParDePara` (T006); independe do admin da US1.
- **US3 (P2)**: só da fundação. Usa `consolidado` (T012).
- **US4 (P3)**: depende da US3 (a view e a página com abas, T029 e T030).

### Within Each User Story

- Testes escritos primeiro e falhando.
- Funções puras antes das consultas, consultas antes de views e templates.
- `catalogo/admin.py`, `catalogo/curva.py`, `catalogo/consultas_curva.py` e `catalogo/views.py` são
  tocados por mais de uma história: as tarefas que mexem no mesmo arquivo não são [P] entre si.

### Parallel Opportunities

- T003, T004 e T005 (testes da fundação), e depois T010 e T011 (módulos puros diferentes).
- Na US1: T013, T014 e T015 (arquivos de teste diferentes).
- Na US2: T019 e T020; a US2 inteira pode andar ao lado da US1 depois da fundação.
- Na US3: T024 e T025; depois T030 e T031 (templates e navegação).
- No polish: T038, T039 e T040.

---

## Parallel Example: User Story 1

```bash
# Testes da história 1, juntos:
Task: "Cenários do formulário AB consolidado em tests/test_catalogos.py"
Task: "Admin de pares (recusas, aviso, origem, LogEntry) em tests/test_depara.py"
Task: "Saúde com canônico em tests/test_saude.py"
```

## Parallel Example: User Story 3

```bash
Task: "curva() e pendentes() em tests/test_curva.py"
Task: "Página Curva ABC em tests/test_pagina_curva.py"
# depois da view (T029):
Task: "Templates curva.html, _curva_tabela.html, _curva_pendentes.html"
Task: "Ícone grafico e item de menu Curva ABC"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1 e 2.
2. Fase 3 (US1): o formulário AB deixa de mostrar o material fatiado ou repetido.
3. **Parar e validar**: seção 3 do `quickstart.md` com pares digitados no admin.

### Incremental Delivery

1. Fundação, depois a US1: o defeito do formulário AB corrigido (MVP).
2. US2: os ~400 pares da planilha entram de uma vez.
3. US3: curvas e pendentes; a planilha deixa de ser necessária para a curva ABC.
4. US4: reposição; a planilha deixa de ser necessária de vez.

Cada história é um commit (ou grupo de commits) testado, sem quebrar as anteriores.

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente.
- Commit em português ao fim de cada tarefa ou grupo lógico.
- A migration é regenerada uma única vez (T009). Se uma história posterior precisar mudar um
  modelo, regenerar de novo, nunca criar `0002` (research D11).
- O T042 inclui o lembrete pedido pelo João: a conferência com a planilha real é dele.

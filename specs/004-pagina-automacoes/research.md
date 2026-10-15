# Research: Página única de automações

Decisões tomadas a partir do código atual (`catalogo/views.py`, `pedidos/views/lancamentos.py`,
`pedidos/views/almoxarifado.py`, `interface/static/interface/js/abas.js` e `filtros.js`, HTMX 4.0.0
vendorizado). Nenhum ponto ficou como NEEDS CLARIFICATION.

## R1. Onde a página mora

- **Decision**: app novo `automacoes`, sem modelos nem migrations, só composição e apresentação:
  `urls.py`, `views.py`, `historico.py` e `templates/automacoes/`. Rota `painel/automacoes/`
  (nome `automacoes:pagina`), incluída em `config/urls.py` antes de `painel/`. As views das ações
  (`atualizar`, `importar`, `lancar`, `resolver`) mudam para o app novo, com os mesmos corpos
  (clarificação de 2026-10-15: o sistema não está em produção e os endereços antigos são apagados).
- **Rationale**: a página junta dois apps (`catalogo` e `pedidos`); pôr a página num deles faria um
  depender da apresentação do outro. O app novo não grava nada por conta própria: as views das ações
  só validam e chamam `servicos.resolver_lote` e `scpi.disparo`, como hoje (Princípio II). Modelos,
  serviços, consultas e regras ficam em `catalogo`, `pedidos` e `scpi`.
- **Alternatives considered**: a página dentro de `catalogo` (o lançamento é de `pedidos`, e o
  `catalogo` passaria a importar views de `pedidos`); dentro de `interface` (que, pelo `CLAUDE.md`, é
  só apresentação comum, sem telas de negócio).

## R2. Contexto de cada parte sem duplicar as views atuais

- **Decision**: levar para `automacoes/views.py` o contexto das duas views atuais, como funções:
  `contexto_catalogo(request, aba, formularios=None)` (o atual `catalogo.views._contexto`, com a
  carência do disparo, sem o histórico) e `contexto_lancamento(request)` (o corpo atual de
  `pedidos.views.lancamentos.lancamentos`, sem as últimas execuções); o `catalogo/views.py` fica só
  com a curva e `pedidos/views/lancamentos.py` é apagado. A view de Automações junta os dois dicionários, o
  histórico e as abas.
- **Rationale**: o comportamento (botões, carência do disparo, fila, andamento, travas) fica
  exatamente o de hoje e os parciais existentes (`catalogo/_situacao.html`, `catalogo/_robo.html`,
  `pedidos/_lancamentos.html`) são reaproveitados como estão, trocando só as URLs que eles chamam.
- **Alternatives considered**: reescrever os contextos no app novo (duplicação e risco de
  divergência); renderizar cada aba por HTMX ao abri-la (quebra o "sem JavaScript, todas as partes
  alcançáveis" e o endereço direto de cada aba).

## R3. Várias regiões HTMX numa página só

- **Decision**: uma view só (`automacoes:pagina`) que, com `HX-Request` (e sem
  `HX-History-Restore-Request`), devolve só a região pedida, escolhida pelo cabeçalho `HX-Target`:
  `section#situacao-catalogo` → `catalogo/_situacao.html`; `section#lancamentos` →
  `pedidos/_lancamentos.html`; `div#historico` → `automacoes/_historico.html`. Alvo desconhecido
  devolve a página inteira. `Vary: HX-Request, HX-Target, HX-History-Restore-Request`.
- **Rationale**: o HTMX 4.0.0 vendorizado manda `HX-Target` no formato `tag#id` (conferido no
  código: `${tagName}#${id}`). Com uma URL só, o `hx-push-url` dos filtros e da paginação do
  histórico grava um endereço que, aberto direto, mostra a página inteira com os mesmos filtros
  (FR-020), sem parâmetro técnico na URL.
- **Alternatives considered**: um parâmetro `parte=` na query (iria parar no endereço gravado pelo
  `hx-push-url`); uma URL parcial por região (o `hx-push-url` gravaria a URL parcial, ou exigiria
  montar a URL da página no cliente).

## R4. Acompanhamento das execuções em andamento

- **Decision**: manter os dois laços de hoje, cada um na sua região: a situação do catálogo recarrega
  a cada 5 s e o lançamento a cada 3 s, só enquanto há algo em andamento, agora com `hx-get` para
  `automacoes:pagina`. A visão geral ganha a linha do lançamento dentro de `_situacao.html` (dados
  de `lotes_pendentes`, `lotes_travados` e `ExecucaoRobo.em_andamento`), e passa a acompanhar também
  quando o lançamento está em andamento. O histórico recarrega junto com a situação, por um
  `hx-trigger` próprio que segue o mesmo `acompanhar` (só sem filtros sendo digitados: o formulário
  de filtros fica fora da região recarregada, como no painel).
- **Rationale**: as regras de quando acompanhar e quando parar já estão testadas; os formulários
  continuam fora das regiões recarregadas (não perdem o que foi digitado, FR-009).
- **Alternatives considered**: um laço só para a página inteira (recarregaria formulários) ou SSE
  (dependência nova, contra o Princípio VI e sem ganho para dois ou três usuários).

## R5. Histórico combinado: consulta, filtros e paginação

- **Decision**: `automacoes/historico.py` com:
  - `FiltrosHistorico` (form GET no molde de `pedidos.consultas.FiltrosPainel`): `q`, `robo`
    (`lancamento`, `cadastro`, `estoque`, `saidas`, `depara`), `situacao` (`concluida`,
    `com_avisos`, `falhou`, `interrompida`, `andamento`), `de`, `ate`; valor desconhecido é
    descartado pelo próprio `ChoiceField` (o form fica válido sem ele).
  - duas consultas, uma por modelo (`Importacao` e `ExecucaoRobo`), cada uma filtrada no banco;
    `robo` escolhe uma só delas quando aponta para um modelo.
  - `SequenciaHistorico`: objeto com `count()` (soma dos dois `count()`) e `__getitem__(slice)` que
    busca `fim` linhas de cada consulta ordenada por `-inicio`, intercala em Python e corta a fatia.
    Serve direto ao `Paginator` de 20, com o `interface/_paginacao.html` de sempre.
- **Rationale**: as duas tabelas têm `inicio` indexável e ordenação `-inicio`; o volume é de
  centenas a poucos milhares de linhas, e a página N só lê `20·N` linhas de cada tabela. Mantém os
  filtros em SQL, como `consultas.py` faz no painel.
- **Alternatives considered**: `UNION` em SQL (colunas incompatíveis: `avisos`/`linhas` contra
  `resumo`/`log`, e o ORM perde os objetos); tabela nova de execuções (contraria a spec: nenhum
  registro novo; e seria uma migração de dados).

## R6. Situação unificada

- **Decision**: o vocabulário do filtro e do selo junta os dois modelos assim:

  | Filtro | `Importacao` | `ExecucaoRobo` |
  |---|---|---|
  | Em andamento | `ANDAMENTO` e na `em_andamento()` | `ANDAMENTO` e na `em_andamento()` |
  | Interrompida | `ANDAMENTO` fora da `em_andamento()` | `ANDAMENTO` fora da `em_andamento()` |
  | Concluída | `SUCESSO` sem avisos | `SUCESSO` |
  | Com avisos | `SUCESSO` com avisos | `ATENCAO` (selo: "Com pendências") |
  | Falhou | `FALHA` | `FALHA` |

  "Em andamento" e "Interrompida" usam os ids de `em_andamento()` calculados uma vez por pedido (as
  travas `IS_USED_LOCK` são consultadas uma vez por tipo, não por linha). "Sem avisos" é
  `Cast(avisos, CharField) == "[]"`, que vale no MySQL 8 e no MariaDB (o teste roda no banco real,
  Princípio V).
- **Rationale**: reaproveita as regras de "em andamento" que já existem e o rótulo que o operador já
  vê em cada página.
- **Alternatives considered**: `avisos=[]` direto (a comparação de JSON difere entre MySQL e MariaDB).

## R7. Busca e modo

- **Decision**: `q` procura (sem diferença de maiúsculas) no `erro` dos dois modelos, no texto dos
  `avisos` da importação e no `log` da execução do robô. O modo mostrado vem do que já é registrado:
  lançamento → "Simulação" ou "Lançamento real"; cadastro com `periodo_de`/`periodo_ate` → "Só os
  novos (dd/mm a dd/mm)" (o incremental e o parcial sempre gravam o período; só a recarga completa
  não grava); cadastro sem período → "Recarga completa"; saídas → "Período dd/mm a dd/mm"; estoque
  → "Saldos"; de/para → "Carga da planilha".
- **Rationale**: a spec pede a busca no erro, nos avisos e no registro da execução; o resumo de uma execução do robô é montado
  do `resumo` (contadores) e do `log`, e o da importação dos `avisos` e das `linhas`. Nada novo
  precisa ser gravado para saber o modo.
- **Alternatives considered**: gravar o modo em campo novo (mudaria modelo e os robôs, fora do
  escopo).

## R8. Período

- **Decision**: `de`/`ate` filtram `inicio` pelos limites do dia local, como o painel
  (`criado_em__gte=_inicio(de)` e `__lt=_inicio(ate + 1 dia)`), extraindo o `_inicio` de
  `pedidos/consultas.py` para reuso.
- **Rationale**: `__date` com `USE_TZ` exige as tabelas de fuso do MySQL; os limites calculados em
  Python não.

## R9. Abas e endereços

- **Decision**: abas `visao-geral` (padrão), `lancamento`, `cadastro`, `estoque`, `saidas`, pelo
  componente comum `[data-abas]` (`interface/js/abas.js`, `?aba=`). As rotas antigas são apagadas,
  sem redirecionamento: `catalogo:situacao`, `catalogo:atualizar`, `catalogo:importar`,
  `pedidos:lancamentos`, `pedidos:lancar` e `pedidos:resolver`, junto com
  `catalogo/situacao.html` e `pedidos/lancamentos.html`. As ações ganham rotas sob a página:
  `automacoes:atualizar`, `automacoes:importar <robo>`, `automacoes:lancar` e
  `automacoes:resolver <lote>`, que redirecionam para a aba de origem (atualizar → `visao-geral`;
  importar → a aba do robô; lançar e resolver → `lancamento`). O formulário inválido de importação
  renderiza Automações na aba do robô. `catalogo:curva` continua em `/painel/catalogo/curva/`.
- **Rationale**: o sistema não está em produção (clarificação de 2026-10-15); redirecionamentos e
  rotas duplicadas só seriam código a manter.
- **Alternatives considered**: redirecionamento 301 dos endereços antigos (desnecessário sem
  usuários); manter as POSTs nos apps de origem (deixaria a página com ações espalhadas em três
  prefixos de URL).

## R10. Histórico e lançamento: o que sai de cada parte

- **Decision**: saem o cartão "Histórico" de `catalogo/_situacao.html` e "Últimas execuções" de
  `pedidos/_lancamentos.html`. Cada aba de robô e a de lançamento ganham "Ver histórico", que leva a
  `?aba=visao-geral&robo=<chave>#historico`. O detalhe técnico do erro usa os mesmos
  `resumo_do_erro`/`erro_tecnico` (importação) e `andamento.explicar_falha` (lançamento).
- **Rationale**: FR-017 e FR-022; um histórico só, com a mesma forma de explicar falhas de hoje.

## R11. Filtros: o padrão do painel sem variação

- **Decision**: o formulário de filtros do histórico usa a mesma marcação do painel
  (`form.filtros-recolhiveis[data-filtros]`, `filtros-barra`, `filtros-alternar` com contagem,
  `filtros-chips`, `filtros-painel`, `filtros-grade`, `filtros-periodo`, `filtros-limpar`) e o mesmo
  `filtros.js`, com `hx-get` para `automacoes:pagina`, `hx-target="#historico"`,
  `hx-push-url="true"` e `hx-trigger="change, input delay:400ms, submit"`. O formulário leva
  `aba=visao-geral` escondido, para o endereço gravado abrir a aba certa. O estado aberto/fechado do
  painel usa a mesma chave do painel de pedidos (comportamento atual do `filtros.js`).
- **Rationale**: pedido do usuário; o `filtros.js` já é genérico por `form[data-filtros]`.
- **Alternatives considered**: chave de `localStorage` própria por formulário (mudaria o
  `filtros.js`; fica para quando alguém pedir).

## R12. Menu

- **Decision**: `ITENS_MENU` troca "Catálogo" e "Lançamentos SCPI" por
  `ItemMenu("Automações", "automacoes:pagina", "robo")`, na posição do antigo "Catálogo" (depois de
  "Saída avulsa", antes de "Curva ABC"). Como a página tem um nome de rota só, o item fica marcado
  em todas as abas sem mudar `menu()`.

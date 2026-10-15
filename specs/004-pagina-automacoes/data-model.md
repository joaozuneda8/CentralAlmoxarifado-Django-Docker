# Data Model: Página única de automações

Nenhum modelo, campo ou migration muda. A página lê os registros que já existem e monta, em memória,
as estruturas abaixo.

## Fontes (existentes, só leitura)

### `catalogo.Importacao`

`tipo` (CADASTRO, ESTOQUE, SAIDAS, DEPARA), `inicio`, `fim`, `situacao` (ANDAMENTO, SUCESSO, FALHA),
`linhas`, `avisos` (lista JSON), `erro`, `periodo_de`, `periodo_ate`. "Em andamento" de verdade:
`Importacao.em_andamento(agora)`; interrompida: `esta_interrompida(agora)`.

### `pedidos.ExecucaoRobo`

`simulacao`, `iniciada_por`, `inicio`, `fim`, `situacao` (ANDAMENTO, SUCESSO, ATENCAO, FALHA),
`resumo` (contadores JSON), `log`, `erro`. "Em andamento": `ExecucaoRobo.em_andamento(agora)`;
interrompida: `interrompida`.

## Estruturas da página (em memória)

### `Aba`

| Campo | Descrição |
|---|---|
| `chave` | `visao-geral`, `lancamento`, `cadastro`, `estoque`, `saidas` |
| `rotulo` | "Visão geral", "Lançamento no SCPI", "Cadastro", "Estoque", "Saídas" |
| `selo` | texto e nível do selo de atenção, ou nada (importação: o da `Fonte`; lançamento: "N para conferir" com travas, "Em andamento" com execução) |

Regra: `?aba=` desconhecida ou ausente → `visao-geral`; `situacao` (endereço antigo) → `visao-geral`.

### `LinhaAutomacao` (visão geral)

Uma por automação, na ordem: lançamento no SCPI, cadastro, estoque, saídas.

| Campo | Descrição |
|---|---|
| `automacao` | chave da aba de destino |
| `nivel` | `ok`, `andamento`, `aviso`, `erro` (o mesmo de `saude.Fonte.nivel`) |
| `selo` | estado em texto ("Em dia", "Em andamento", "Com avisos", "Falhou", "Interrompida"; "Sem dados" na importação que nunca rodou; no lançamento, "Sem execuções" quando nunca rodou e "N para conferir" com travas) |
| `quando` | última execução, com "há quanto tempo" |
| `resumo` | uma frase (importação: o resumo da `Fonte`; lançamento: "N aguardando o robô" e a última execução) |
| `acao` | rótulo e destino do caminho para resolver ("Tentar de novo" → aba do robô; "Conferir travas" → aba do lançamento, âncora das travas), ou nada |

As linhas das importações vêm de `situacao_do_catalogo().fontes` (como hoje); a do lançamento é
montada de `lotes_pendentes()`, `lotes_travados()` e da última `ExecucaoRobo`.

### `FiltrosHistorico` (form GET)

| Campo | Valores | Regra |
|---|---|---|
| `q` | texto | busca sem diferença de maiúsculas em `erro`, texto dos `avisos` (importação) e `log` (lançamento) |
| `robo` | `""`, `lancamento`, `cadastro`, `estoque`, `saidas`, `depara` | `lancamento` lê só `ExecucaoRobo`; os demais só `Importacao` do tipo |
| `situacao` | `""`, `concluida`, `com_avisos`, `falhou`, `interrompida`, `andamento` | mapa em research.md (R6) |
| `de`, `ate` | datas | limites do dia local sobre `inicio`; `ate` inclui o dia inteiro |

Valor desconhecido num `ChoiceField` é ignorado (o filtro some, a lista não quebra). A contagem de
filtros ativos e os chips são os do `filtros.js`.

### `LinhaHistorico`

| Campo | Descrição |
|---|---|
| `robo` | rótulo ("Lançamento no SCPI", "Cadastro", "Estoque", "Saídas", "Pares de/para") |
| `modo` | research.md (R7) |
| `inicio` | data e hora local |
| `duracao` | de `inicio` a `fim`; vazio em andamento |
| `situacao` | chave do vocabulário unificado (R6) |
| `selo` | texto do estado ("Concluída", "Com avisos", "Com pendências", "Falhou", "Interrompida", "Em andamento") |
| `resumo` | importação: linhas e avisos agrupados (`agrupar_avisos`); lançamento: `andamento.n_de_m` e contadores |
| `erro` | frase (`resumo_do_erro` ou `andamento.explicar_falha`) |
| `erro_tecnico` | texto técnico recolhido (`erro_tecnico`), quando houver |
| `iniciada_por` | quem iniciou (só lançamento; importação não registra) |

Construção: uma função pura recebe o registro e os conjuntos de ids em andamento e devolve a linha
(testável sem banco além da carga do registro).

### `SequenciaHistorico`

Objeto que o `Paginator` consome: `count()` = soma das contagens filtradas dos dois modelos;
`[a:b]` busca as `b` primeiras de cada consulta (ordem `-inicio`), intercala por `inicio`
decrescente (empate: lançamento antes de importação, depois `pk` decrescente) e devolve
`LinhaHistorico` de `a` a `b`. Página de 20.

## Transições de estado

Nenhuma nova. Os estados das execuções e das linhas de saída continuam mudando só pelos robôs e por
`servicos.resolver_lote`, como hoje.

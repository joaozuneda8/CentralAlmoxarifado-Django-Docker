# Data Model: Clareza e segurança da página Lançamentos SCPI

Nenhum modelo, campo ou migration novo. Tudo sai de `ExecucaoRobo` e `LinhaSaida` como estão; as
estruturas abaixo são de apresentação, montadas a cada pedido da página.

## Fontes (inalteradas)

### `LinhaSaida` (`pedidos/models.py`)

Campos lidos: `id`, `lote`, `status`, `requisicao_scpi`, `data`, `recebedor`, `centro_custo`.

Regra da fila (dona: `scpi/requisicoes.agrupar`, extraída de `selecionar` sem mudar o resultado):

- um lote está **na fila** se tem alguma linha `PENDENTE` e nenhuma linha em `ESTADOS_TRAVA`
  (`EM_LANCAMENTO`, `VERIFICAR`, `ERRO`) nem `PENDENTE` com `requisicao_scpi` preenchido;
- um lote com alguma dessas linhas é **travado** e aparece só em "Travas para conferir" se tiver
  linha em `ESTADOS_TRAVA` (o `PENDENTE` com requisição fica de fora das duas, como hoje);
- a ordem é a do `id` da primeira linha `PENDENTE` do lote (a ordem em que o robô percorre).

### `ExecucaoRobo` (`pedidos/models.py`)

Campos lidos: `simulacao`, `iniciada_por`, `inicio`, `fim`, `situacao`, `resumo`, `log`, `erro`,
e as propriedades `interrompida` e `em_andamento`.

`resumo` (gravado por `scpi/lancamento.Resumo`, todas as contagens em requisições):
`requisicoes`, `processadas`, `lancadas`, `simuladas`, `falhas`, `verificar`, `ignoradas`. Pode
estar vazio (`{}`) quando a execução falhou antes de começar.

## Estruturas de apresentação (novas)

### `Fila` (`pedidos/consultas.py`)

| Campo | Tipo | Origem |
|---|---|---|
| `total` | `int` | número de lotes na fila (sempre exibido) |
| `requisicoes` | `list[RequisicaoNaFila]` | os primeiros `limite` (20) lotes, na ordem do robô |
| `fora` | `int` (propriedade) | `total - len(requisicoes)`, "e mais N requisições" |

### `RequisicaoNaFila`

| Campo | Tipo | Origem |
|---|---|---|
| `lote` | `str` | `LinhaSaida.lote` (número do pedido ou da saída avulsa; link `pedidos:detalhe`) |
| `data` | `date` | primeira linha `PENDENTE` do lote |
| `recebedor` | `str` | idem |
| `centro_custo` | `str` | idem |
| `materiais` | `int` | número de linhas `PENDENTE` do lote |

### `Falha` (`pedidos/andamento.py`)

| Campo | Tipo | Regra |
|---|---|---|
| `frase` | `str` | o que aconteceu, em português (R5: conhecido → como vem; "Falha inesperada:" → erro do sistema ou demora do SCPI; sem registro → "não chegou a iniciar") |
| `ate_onde` | `str` | "Chegou a processar N de M requisições." ou "Parou antes de começar." |
| `proximo_passo` | `str` | simulação: simular de novo; lançamento real: conferir as travas |
| `tecnico` | `bool` | se há "Detalhe técnico" a mostrar (texto original + registro) |
| `simular_de_novo` | `bool` | só na simulação |

### Funções puras de `pedidos/andamento.py`

| Função | Entrada | Saída | Casos de teste |
|---|---|---|---|
| `feitas` | execução | `simuladas` ou `lancadas` | os dois modos |
| `n_de_m` | execução | "N de M" ou `None` | 3 de 3; 2 de 3; resumo vazio; `requisicoes` 0 |
| `duracao` | `inicio`, `fim` | "45 s", "2 min 5 s", "1 h 3 min", "—" | sem fim; < 1 min; < 1 h; ≥ 1 h |
| `momento` | `inicio`, `agora` | "hoje, 13:25", "ontem, 13:25", "07/10, 13:25" | três dias; virada do dia no fuso local |
| `contadores` | `resumo`, `simulacao` | textos prontos ("3 simuladas"), só os ≠ 0 | tudo zero; 1 lançada + 1 para verificar; plural |
| `frase` | execução, `agora`, `interrompida` | uma frase | concluída, com pendências, nada a lançar, em andamento (com e sem total), interrompida, falha |
| `precisa_conferir` | execução | `bool` | `falhas`/`verificar` > 0; falha de lançamento real; falha de simulação (não) |
| `explicar_falha` | execução | `Falha`, ou `None` se a situação não é `FALHA` | cada ramo de R5 nos dois modos |

## Transições de estado

Nenhuma nova. A única ação que grava continua sendo `servicos.resolver_lote`; a confirmação do
"Não lançar" só acrescenta, na view, a recusa de `acao=nao_lancar` sem `confirmado=1` antes de
chamá-lo.

# Data Model: Clareza e facilidade de uso dos formulários públicos de pedido

Nenhum modelo do banco muda e não há migration. As mudanças de dados são só em estruturas em
memória e no armazenamento do navegador.

## `regras.Erro` (dataclass, `pedidos/regras.py`)

| Campo | Tipo | Antes | Depois |
|---|---|---|---|
| `codigo` | `str \| None` | código do material, ou `None` | igual |
| `texto` | `str` | mensagem | igual (mesmos textos, Princípio I) |
| `campo` | `str \| None` | — | **novo**, padrão `None`: `"solicitante"`, `"destino"` ou `"obs"` quando o erro é desse campo |

Quem preenche `campo`:

| Origem | Texto | `campo` |
|---|---|---|
| `validar_pedido_limpeza` / `validar_pedido_ab` | "Informe o nome completo." | `solicitante` |
| idem | "Escolha o destino dos materiais na lista de centros de custo." / 'Destino "…" não está na lista de centros de custo.' | `destino` |
| idem | "Adicione ao menos um material ao pedido." | `None` (só no resumo) |
| `servicos.erros_de_tamanho` | "Nome completo: no máximo 200 caracteres." | `solicitante` |
| idem | "Destino: no máximo 200 caracteres." | `destino` |
| idem | "Observação: no máximo 200 caracteres." | `obs` |
| idem | "O pedido pode ter no máximo 40 materiais. …" | `None` |
| erros de material | (vários) | `None` (têm `codigo`) |

`erros_de_tamanho` também é usado por `registrar_saida_avulsa` (área interna); lá o `campo` é
preenchido do mesmo jeito e simplesmente não é usado pelo template da avulsa.

## Contexto do formulário público (view → template)

| Chave | Novo? | Conteúdo |
|---|---|---|
| `erros` | não | lista de `Erro` |
| `erros_por_campo` | **sim** | `{campo: [texto, ...]}` montado dos erros com `campo` |
| `codigos_erro` | não | códigos dos materiais com erro |

## Contexto da tela de sucesso

| Chave | Novo? | Conteúdo |
|---|---|---|
| `resposta`, `n_itens`, `fluxo` | não | como hoje |
| `itens` | **sim** | itens do pedido gravado (nome, quantidade formatada pt-BR, unidade), na ordem gravada |

O destino já está em `resposta.pedido.destino`.

## `Fluxo` (`pedidos/fluxos.py`)

| Campo | Mudança |
|---|---|
| `titulo` | limpeza: "Limpeza, copa e escritório"; AB: "Ferramentas, peças e materiais"; avulsa: igual |
| `formulario` | **removido** (era "Formulário 1/2", só usado no rótulo do formulário público) |

## Dados lembrados no navegador (`localStorage`)

- Chave: `almoxarifado.solicitante`
- Valor: JSON `{"solicitante": string, "destino": string}`
- Escrita: só ao exibir a tela de sucesso de um pedido registrado (ou reenvio confirmado).
- Leitura: ao abrir um formulário público; preenche só campos vazios; destino só se existir nas
  opções atuais.
- Remoção: "Não é você? Limpar".
- Falha de acesso (bloqueado, anônimo): ignorada; o formulário funciona como hoje.

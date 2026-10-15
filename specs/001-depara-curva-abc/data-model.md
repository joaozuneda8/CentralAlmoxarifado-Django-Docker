# Modelo de dados: De/para de códigos e curva ABC consolidada

Todos os modelos novos ficam no app `catalogo`. Códigos são texto no formato `000.000.000`,
comparados por `norm_u` (a collation `utf8mb4_unicode_ci` do banco).

## ParDePara (novo)

Um código antigo e o código para o qual ele aponta.

| Campo | Tipo | Regras |
|---|---|---|
| `antigo` | texto (30) | obrigatório; formato `000.000.000`; **único** (sem 1:N, FR-003) |
| `novo` | texto (30) | obrigatório; formato `000.000.000`; diferente de `antigo` |
| `fator` | decimal (10,4) | padrão 1; maior que 0 (FR-001) |
| `observacao` | texto (255) | opcional |
| `origem` | escolha | `PLANILHA` (veio da carga) ou `SISTEMA` (criado ou alterado no admin) |
| `atualizado_em` | data e hora | automático a cada gravação |

**Validação** (no `clean`, que chama as funções puras de `catalogo/depara.py`):
- formato dos dois códigos e antigo ≠ novo (FR-002);
- `antigo` sem outro par (FR-003), com a mensagem citando o destino atual;
- o par não pode fechar um ciclo, considerando os pares já gravados (FR-004);
- `fator` maior que zero.

**Aviso, sem bloquear** (FR-007): `novo` sem `Material` no cadastro.

N:1 é permitido: vários `antigo` com o mesmo `novo`. Quem fez cada alteração e quando fica no
histórico do admin (`LogEntry`, FR-005).

## ConfiguracaoCurva (novo, linha única)

| Campo | Tipo | Padrão | Regras |
|---|---|---|---|
| `janela_meses` | inteiro | 12 | ≥ 1 (FR-015) |
| `prazo_entrega_dias` | inteiro | 30 | ≥ 1 (FR-021) |
| `cobertura_alvo_dias` | inteiro | 90 | ≥ 1 (FR-021) |

`ConfiguracaoCurva.atual()` devolve a linha e a cria com os padrões se ela faltar. O admin não
permite criar uma segunda linha nem apagar a existente.

## ParametroReposicao (novo)

Substitui os valores gerais para um material.

| Campo | Tipo | Regras |
|---|---|---|
| `material` | `Material` (1:1) | obrigatório; o código canônico do material |
| `prazo_entrega_dias` | inteiro | opcional; ≥ 1; vazio = valor geral |
| `cobertura_alvo_dias` | inteiro | opcional; ≥ 1; vazio = valor geral |

Pelo menos um dos dois precisa estar preenchido.

## Importacao (alterado)

`Importacao.Tipo` ganha `DEPARA` ("Pares de/para"). Cada carga da planilha cria uma `Importacao`
desse tipo com `linhas` (pares gravados), `avisos` (pares recusados e o motivo de cada um) e `erro`
(D8 de `research.md`).

## SaidaSCPI (alterado)

- A docstring muda: ela equivale à aba `Saídas` da planilha, não à `MOV_NORM` (FR-022).
- Ganha `item` (inteiro, padrão 1) e a chave única passa a (`id_requi`, `cadpro`, `item`).
  A mesma requisição pode ter o mesmo material em mais de uma linha (outra placa, outro
  destino); antes só a primeira era guardada, e as outras se perdiam com a quantidade e o
  valor (48 linhas na carga de 2026). O relatório do SCPI não numera os itens: `item` é a
  ordem da linha entre as do mesmo material na requisição. Com isso as ocorrências contam
  linhas, como a planilha.

## Valores calculados (não guardados)

Produzidos pelas funções puras de `catalogo/depara.py` e `catalogo/curva.py`:

- **Canônico**: para cada código, o destino final da cadeia de pares e o fator acumulado (produto
  dos fatores). Código sem par é canônico de si mesmo, com fator 1.
- **Linha consolidada**: canônico, ocorrências, quantidade convertida e valor, somados no período.
- **Linha da curva**: linha consolidada mais descrição, percentual, percentual acumulado e classe
  (A, B ou C).
- **Linha de reposição**: canônico, descrição, unidade, consumo total, consumo diário, estoque
  (canônico + antigos), prazo de entrega e cobertura alvo usados, estoque de segurança, ponto de
  pedido, quanto pedir, cobertura em dias e situação.
- **Pendente**: código com saída no período, sem par, cujo material está oculto ou fora do cadastro,
  com ocorrências e valor.
- **Reconciliação**: ocorrências e valor totais antes e depois da consolidação, e número de códigos
  antes e de canônicos depois.

## Relações

```text
ParDePara.antigo ──(texto)──▶ Material.codigo   (pode não existir: código já inativado)
ParDePara.novo   ──(texto)──▶ Material.codigo   (pode faltar: aviso)
ParametroReposicao.material ──(1:1)──▶ Material
SaidaSCPI.cadpro ──(texto)──▶ canônico ──▶ Material (formulário AB, curvas, reposição)
```

As ligações por texto seguem o padrão atual (`SaidaSCPI.cadpro` também não é chave estrangeira):
saídas e pares podem citar códigos que o cadastro ainda não tem.

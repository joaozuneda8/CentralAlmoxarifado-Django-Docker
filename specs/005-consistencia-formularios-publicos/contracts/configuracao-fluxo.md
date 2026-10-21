# Contrato: o que um formulário informa (`Fluxo`)

Cada formulário, atual ou novo, é uma entrada de `FLUXOS` em `pedidos/fluxos.py`. O núcleo
(busca, carrinho, envio, proteções, recibo, atendimento) lê só isto. Criar um formulário novo deve
exigir **esta entrada, uma função de catálogo e (fora desta funcionalidade) um valor novo de origem**,
sem alterar o núcleo (FR-041, SC-007).

| Campo | Obrigatório | Significado | limpeza | AB | avulsa |
|---|---|---|---|---|---|
| `nome` | sim | Parte da URL (`/pedido/<nome>/`) e do nome das rotas | `limpeza` | `ab` | `avulsa` |
| `origem` | sim | Valor gravado em `Pedido.origem` | `LIMPEZA` | `AB` | `AVULSA` |
| `titulo` | sim | Nome mostrado ao funcionário | Limpeza, copa e escritório | Ferramentas, peças e materiais | Saída avulsa |
| `publico` | sim | Sem login e com proteções, ou área do almoxarifado | sim | sim | não |
| `regra_quantidade` | sim | `por_unidade` (fração só em unidade fracionável) ou `livre` | `por_unidade` | `por_unidade` | `livre` |
| `catalogo` | sim | Função sem argumentos que devolve a lista de `ItemCatalogo` ou `None` (indisponível) | `catalogo_limpeza` (com saldo importado) | `catalogo_ab().itens` | `catalogo_avulsa` |
| `exemplo_busca` | sim | Texto do exemplo no campo de busca | Ex.: detergente, café | Ex.: luva, fita veda rosca | Ex.: luva, fita veda rosca, 016.005.010 |
| `limite` | não | Função própria do teto da quantidade; ausente = `maximo_pedivel(estoque, fracionavel)` | — | — | — |
| rótulos do carrinho e do envio | derivados de `publico` | "Seu pedido / Revisar e enviar / Enviar pedido" ou "Materiais da saída / Revisar e registrar / Registrar saída" | derivados | derivados | derivados |

## Regras de contrato

1. **Catálogo.** Devolve `None` quando o formulário está indisponível (saldo nunca importado ou
   nenhum item); devolve lista não vazia caso contrário. Não retorna lista vazia.
2. **Regra de quantidade.** O núcleo nunca pergunta pelo nome ou pela origem do formulário; só por
   `regra_quantidade`.
3. **Texto.** Nenhum modelo de página escolhe texto por `fluxo.nome`; tudo o que muda por formulário
   está nesta entrada.
4. **Cabeçalho.** Solicitante, destino (centro de custo cadastrado) e observação; igual para todos.
5. **Lançamento.** O lançamento no SCPI não depende do formulário; só o centro de custo, que vem do
   destino, muda.
6. **Origem pública.** Toda origem diferente de `AVULSA` é pública (`origem_publica`), sujeita ao
   limite por nome e à conferência de reenvio.

## Fora desta funcionalidade

Criar a origem nova (migration de `choices` em `Pedido.Origem`), os destinos aceitos de cada
formulário futuro e um limite próprio (campo `limite`) são tratados na especificação de cada
formulário novo.

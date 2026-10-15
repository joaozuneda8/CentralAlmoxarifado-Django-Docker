# Contrato: páginas da área interna

Todas exigem login (`login_required`), como as demais páginas do almoxarifado, e seguem o design
system Clean (`docs/DESIGN.md`). Códigos em fonte mono; classe e situação sempre com texto, nunca só
com cor.

## Menu

`interface/navegacao.py` ganha `ItemMenu("Curva ABC", "catalogo:curva", <ícone>)`, depois de
"Catálogo". O ícone é um Lucide novo em `_icone.html` (gráfico de barras), porque nenhum dos atuais
serve.

## `GET /painel/catalogo/curva/` → `catalogo:curva`

Uma página com abas (`abas.js`, como a página Catálogo):

| Aba | Parâmetro | Conteúdo |
|---|---|---|
| Frequência | `?aba=frequencia` (padrão) | curva por ocorrências (FR-016, FR-017) |
| Valor | `?aba=valor` | curva por valor |
| Reposição | `?aba=reposicao` | tabela de reposição (FR-019, FR-020) |
| Pendentes | `?aba=pendentes` | códigos pendentes de mapeamento (FR-006) |

**Parâmetro de período**: `?meses=N` (inteiro ≥ 1; padrão `ConfiguracaoCurva.janela_meses`). Valor
inválido volta ao padrão, com mensagem.

**Cabeçalho comum** a todas as abas:
- o período efetivo ("de dd/mm/aaaa a dd/mm/aaaa");
- o aviso "Os dados anteriores a 01/01/2026 não entram nos cálculos." quando a janela pediria
  uma data anterior;
- a reconciliação (FR-018): ocorrências e valor antes e depois, que precisam ser iguais, e o número
  de códigos antes e de canônicos depois.

**Colunas**:
- Frequência e Valor: posição, código canônico, descrição, ocorrências, quantidade, valor,
  % do total, % acumulado, classe.
- Reposição: código, descrição, unidade, consumo no período, consumo diário, estoque, prazo de
  entrega, cobertura alvo, estoque de segurança, ponto de pedido, quanto pedir, cobertura (dias),
  situação. O prazo e a cobertura vindos de `ParametroReposicao` aparecem marcados como próprios
  do material.
- Pendentes: código, descrição (se houver cadastro), motivo ("oculto no cadastro" ou "sem
  cadastro"), ocorrências, valor; com um link para criar o par no admin, só para quem é da equipe
  (`is_staff`).

**Vazio**: sem saídas no período, cada aba mostra "Nenhuma saída no período." no lugar da tabela.

## Admin (`/admin/` → Cadastros)

- **Pares de/para**:
  - lista com antigo, novo, nome do novo, fator, origem e atualizado em;
  - busca por código; filtro por origem;
  - formulário com as validações do `data-model.md`; o aviso de "novo sem cadastro" sai como
    mensagem de alerta depois de salvar.
- **Configuração da curva**: uma linha, sem incluir nem excluir.
- **Parâmetros de reposição**: material com `autocomplete`, prazo e cobertura.

## Formulário AB (`/pedido/<fluxo>/` do AB, sem mudança de rota)

Mesma página e mesmo fluxo. Muda só o catálogo: um item por código canônico, na ordem das
ocorrências consolidadas no período (FR-013), com o saldo do canônico (FR-014).

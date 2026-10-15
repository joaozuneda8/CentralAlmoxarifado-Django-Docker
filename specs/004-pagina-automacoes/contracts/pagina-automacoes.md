# Contrato: página Automações

Interface HTTP da área interna (todas as rotas exigem login; sem login → `/painel/entrar/?next=…`).
Os caminhos abaixo são relativos ao prefixo (`PREFIXO_URL`, `/almoxarifado` no servidor).

## GET `/painel/automacoes/` — `automacoes:pagina`

### Parâmetros

| Parâmetro | Valores | Efeito |
|---|---|---|
| `aba` | `visao-geral` (padrão), `lancamento`, `cadastro`, `estoque`, `saidas`; `situacao` = `visao-geral` | aba aberta; desconhecido → `visao-geral` |
| `q`, `robo`, `situacao`, `de`, `ate` | ver data-model.md (`FiltrosHistorico`) | filtros do histórico |
| `pagina` | inteiro | página do histórico (20 por página) |

### Respostas

| Pedido | Resposta |
|---|---|
| sem `HX-Request`, ou com `HX-History-Restore-Request` | página inteira (`automacoes/pagina.html`): título "Automações", abas, as cinco regiões |
| `HX-Request` + `HX-Target: section#situacao-catalogo` | só a visão geral recarregável (`catalogo/_situacao.html`) |
| `HX-Request` + `HX-Target: section#lancamentos` | só o lançamento recarregável (`pedidos/_lancamentos.html`) |
| `HX-Request` + `HX-Target: div#historico` | só a lista do histórico com a paginação (`automacoes/_historico.html`) |
| `HX-Request` com outro alvo | página inteira |

Toda resposta leva `Vary: HX-Request, HX-Target, HX-History-Restore-Request`.

### Marcação que os testes e os scripts usam

- `[data-abas]` com `role="tablist"`; abas `#aba-<chave>`, painéis `#painel-<chave>`.
- `section#situacao-catalogo[data-em-andamento]` (o `importacoes.js` segue esse atributo) e, enquanto
  há importação ou lançamento em andamento, `hx-get` para esta rota e `hx-trigger="every 5s"`.
- `section#lancamentos`, com `hx-trigger="every 3s"` enquanto há execução do lançamento.
- `form.filtros-recolhiveis[data-filtros]` com `hx-target="#historico"`, `hx-push-url="true"`,
  campo escondido `aba=visao-geral` e `action` = esta rota (funciona sem JavaScript).
- `div#historico`: total ("N execuções", e "filtradas" com filtro ativo), lista, estado vazio com
  "Limpar filtros" e `interface/_paginacao.html` (`parametro="pagina"`, `htmx_alvo="#historico"`).
- Em cada aba de robô e na de lançamento: link "Ver histórico" para
  `?aba=visao-geral&robo=<chave>#historico`.

## Ações (POST)

| Rota | Sucesso, recusa ou erro de negócio | Form inválido |
|---|---|---|
| `/painel/automacoes/atualizar/` (`automacoes:atualizar`) | mensagem + 302 para `?aba=visao-geral` | — |
| `/painel/automacoes/importar/<robo>/` (`automacoes:importar`) | mensagem + 302 para `?aba=<robo>` | 200 com Automações na aba do robô, erros no formulário |
| `/painel/automacoes/lancar/` (`automacoes:lancar`) | mensagem + 302 para `?aba=lancamento` | mensagem de erro + 302 para `?aba=lancamento` |
| `/painel/automacoes/lancamento/<lote>/resolver/` (`automacoes:resolver`) | mensagem + 302 para `?aba=lancamento` | idem |

O corpo de cada ação (o que grava, recusa e dispara) é o de hoje (FR-015). O atalho "Lançar no
SCPI" do painel envia para `automacoes:lancar`.

## Rotas apagadas

`/painel/catalogo/` (`catalogo:situacao`), `/painel/catalogo/atualizar/`,
`/painel/catalogo/importar/<robo>/`, `/painel/lancamentos/` (`pedidos:lancamentos`),
`/painel/lancamentos/iniciar/` (`pedidos:lancar`) e `/painel/lancamentos/<lote>/resolver/`
(`pedidos:resolver`) respondem 404. `/painel/catalogo/curva/` continua.

## Menu

`ITENS_MENU`: "Painel", "Saída avulsa", "Automações" (`automacoes:pagina`), "Curva ABC",
"Cadastros". Sem "Catálogo" nem "Lançamentos SCPI".

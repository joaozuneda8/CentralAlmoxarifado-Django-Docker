# Implementation Plan: Página única de automações

**Branch**: `004-pagina-automacoes` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-pagina-automacoes/spec.md`

## Summary

Juntar as páginas Catálogo e Lançamentos SCPI numa página Automações (`/painel/automacoes/`), com
abas Visão geral, Lançamento no SCPI, Cadastro, Estoque e Saídas, e um histórico único das execuções
de todos os robôs, com os filtros recolhíveis do painel de pedidos. A abordagem é de composição: um
app novo `automacoes`, sem modelos, reaproveita os contextos e os parciais que já existem (extraídos
das duas views atuais), escolhe a região que o HTMX recarrega pelo cabeçalho `HX-Target` e monta o
histórico intercalando `Importacao` e `ExecucaoRobo` num objeto paginável. Como o sistema não está
em produção, as páginas e as rotas antigas são apagadas e as views das ações mudam para o app novo
com os mesmos corpos; as regras dos robôs e as travas não mudam.

## Technical Context

**Language/Version**: Python `>=3.13,<3.14`

**Primary Dependencies**: Django 6.x, HTMX 4.0.0 (vendorizado); nenhuma dependência nova

**Storage**: MySQL 8 / MariaDB; nenhuma mudança de modelo nem migration

**Testing**: pytest + pytest-django contra MySQL/MariaDB (`config.settings_test`), cliente de teste
do Django; sem navegador

**Target Platform**: servidor Windows (waitress atrás do Apache em `/almoxarifado`); navegadores de
desktop e celular

**Project Type**: aplicação web Django renderizada no servidor (área interna)

**Performance Goals**: página e regiões HTMX respondem no tempo das páginas atuais; o histórico lê no
máximo `20 × página` linhas de cada tabela por pedido

**Constraints**: funciona sem JavaScript (abas empilhadas, filtros por "Filtrar", paginação por
links); nada de CDN; 375 px sem rolagem horizontal; acompanhamento não apaga o que foi digitado

**Scale/Scope**: poucos usuários simultâneos; centenas a poucos milhares de execuções registradas;
uma página nova, quatro views POST movidas, seis rotas e duas páginas apagadas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Verificação | Situação |
|---|---|---|
| I. Regras puras e fiéis | Nenhuma regra de negócio muda. A conversão de registro em `LinhaHistorico` e o mapa de situações são funções puras com teste próprio. | Passa |
| II. Uma porta de gravação | A página só lê. As gravações continuam em `servicos.resolver_lote`, nos disparos (`scpi.disparo`) e nos robôs; as views POST movidas só validam, chamam essas funções e redirecionam. | Passa |
| III. Nunca lançar duas vezes | `automacoes:lancar` e `automacoes:resolver` levam o corpo de hoje sem mudança (formulário, confirmação do "Não lançar", `LANCAMENTO_REAL`, recusa com execução em andamento); os testes atuais do lançamento continuam, com as rotas novas. | Passa |
| IV. Dados importados não se perdem | Importações intocadas; o histórico mostra todas as execuções registradas (inclui de/para), sem apagar nem resumir nada. | Passa |
| V. Testes no banco real, sem navegador | Testes novos de página, regiões HTMX (por cabeçalho), ações movidas, rotas antigas com 404, menu e histórico (filtros, intercalação, paginação, `Cast` de `avisos` no MySQL/MariaDB). Nenhum abre navegador. | Passa |
| VI. pt-BR, acessível, sem dependências | Textos em pt-BR; estado em texto nos selos; abas WAI-ARIA do componente comum; filtros e paginação já acessíveis; nada externo. Ajustes de UI com `clean-design` + `docs/DESIGN.md`, `ui-ux-pro-max` e `frontend-design`. | Passa |
| Fluxo | Branch própria, spec e plano antes do código, `CLAUDE.md` atualizado no mesmo PR (arquitetura de `catalogo`, lançamento e o app novo). | Passa |

Sem exceções. **Reverificação depois da Fase 1**: o desenho (research R1–R12, contrato, modelo) não
introduz gravação, modelo novo nem dependência; continua passando.

## Project Structure

### Documentation (this feature)

```text
specs/004-pagina-automacoes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pagina-automacoes.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
automacoes/                         # app novo, sem models nem migrations
├── __init__.py
├── apps.py
├── urls.py                         # pagina, atualizar, importar, lancar, resolver
├── views.py                        # página, abas, região por HX-Target; ações movidas
├── historico.py                    # FiltrosHistorico, LinhaHistorico, SequenciaHistorico
├── visao_geral.py                  # LinhaAutomacao (linhas da visão geral, inclui o lançamento)
├── templates/automacoes/
│   ├── pagina.html                 # base_almoxarifado + abas (data-abas)
│   ├── _historico.html             # lista + paginação (região #historico)
│   └── _filtros_historico.html     # form.filtros-recolhiveis[data-filtros]
└── static/automacoes/css/automacoes.css   # só o que for novo (linha do lançamento, histórico)

config/settings.py                  # INSTALLED_APPS += "automacoes"
config/urls.py                      # path("painel/automacoes/", include("automacoes.urls"))

catalogo/views.py                   # só a curva: _contexto, situacao, atualizar e importar vão
                                    # para automacoes/views.py
catalogo/urls.py                    # só curva/
catalogo/templates/catalogo/
├── _situacao.html                  # hx-get para automacoes; linha do lançamento; sem "Histórico"
├── _robo.html                      # "Ver histórico"
└── situacao.html                   # apagado (a página passa a ser automacoes/pagina.html)
catalogo/static/catalogo/js/importacoes.js   # data-url/links para a página nova

pedidos/views/lancamentos.py        # apagado: contexto vai para automacoes (contexto_lancamento)
pedidos/urls.py                     # sem lancamentos/, lancar e resolver
pedidos/templates/pedidos/
├── _lancamentos.html               # hx-get para automacoes; sem "Últimas execuções"; "Ver histórico"
├── lancamentos.html                # apagado
├── painel.html                     # links e o form do atalho para automacoes
└── detalhe.html                    # "Resolver em Automações" → ?aba=lancamento
pedidos/consultas.py                # _inicio exposto para reuso no filtro de período

interface/navegacao.py              # "Automações" no lugar de "Catálogo" e "Lançamentos SCPI"

tests/
├── test_automacoes.py              # novo: página, abas, regiões, ações, rotas apagadas, menu
├── test_historico_automacoes.py    # novo: filtros, situação unificada, intercalação, paginação
├── test_pagina_catalogo.py         # URLs e asserções adaptadas
├── test_pagina_lancamentos.py      # idem
├── test_robos_avulsos.py           # rotas novas das importações
├── test_acesso.py, test_rotas.py, test_prefixo.py, test_painel.py   # rotas novas; antigas dão 404
CLAUDE.md                           # arquitetura: app automacoes, página e histórico
docs/DESIGN.md                      # só se surgir classe nova (histórico, linha do lançamento)
```

**Structure Decision**: Django monolítico, um app novo (`automacoes`) de composição ao lado de
`catalogo` e `pedidos`, que continuam donos dos modelos, serviços e parciais; as ações mudam para
o app novo (research R1, R2, R9).

## Fases de implementação (para o /speckit-tasks)

1. **Base da página**: app, rota, `pagina.html` com as abas, contextos extraídos
   (`contexto_catalogo`, `contexto_lancamento`), regiões por `HX-Target`, menu, ações movidas com
   redirecionamento para a aba de origem; páginas e rotas antigas apagadas. Testes atuais adaptados.
   Entrega US2, US3, US5 e US6.
2. **Visão geral**: linha do lançamento junto das fontes, selos nas abas, acompanhamento quando
   o lançamento está em andamento. Entrega US1.
3. **Histórico combinado**: `historico.py`, `_historico.html`, filtros no padrão do painel, "Ver
   histórico" nas abas; saem os dois históricos antigos. Entrega US4.
4. **Acabamento**: links do painel e do detalhe, 375 px, sem JavaScript, `CLAUDE.md` e
   `docs/DESIGN.md`, conferência por screenshot.

## Complexity Tracking

Sem violações da constituição a justificar.

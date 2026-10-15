# Implementation Plan: De/para de códigos e curva ABC consolidada

**Branch**: `001-depara-curva-abc` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-depara-curva-abc/spec.md`

## Summary

O sistema passa a guardar os pares "código antigo → código novo" (com fator de quantidade) que hoje
vivem na planilha MAPEAMENTO DE/PARA CONSOLIDADO. A partir deles, toda contagem de saídas é feita
pelo código canônico, e o formulário AB deixa de mostrar o mesmo material fatiado ou repetido.

Sobre essa consolidação, uma página nova mostra as curvas ABC por frequência e por valor, a tabela
de reposição e os códigos pendentes de mapeamento. Um comando carrega de uma vez os pares que a
planilha já tem.

**Abordagem técnica** (detalhes em [research.md](research.md)):
- três modelos novos no `catalogo`: `ParDePara`, `ConfiguracaoCurva` (linha única) e
  `ParametroReposicao`;
- funções puras para resolver o canônico, consolidar, montar a curva e calcular a reposição, em
  cima de uma única agregação das saídas por código;
- o comando `importar_depara` no app `implantacao`, ao lado do `importar_planilhas`.

## Technical Context

**Language/Version**: Python 3.13 (`>=3.13,<3.14`)

**Primary Dependencies**: Django 6.x, HTMX 4.0.0 (vendorizado), openpyxl (já usado pelo
`implantacao`); nenhuma dependência nova

**Storage**: MySQL 8 ou MariaDB (collation `utf8mb4_unicode_ci`)

**Testing**: pytest + pytest-django contra MySQL/MariaDB (`config.settings_test`)

**Target Platform**: servidor Windows (waitress + NSSM atrás do Apache em `/almoxarifado`)

**Project Type**: aplicação web Django (monólito com apps `catalogo`, `pedidos`, `scpi`, `implantacao`)

**Performance Goals**:
- página da curva e formulário AB respondem em menos de 1 s com 12 meses de saídas (~5–10 mil
  linhas de `SaidaSCPI`, menos de mil códigos distintos, ~400 pares);
- um par novo tem efeito na consulta seguinte (SC-005).

**Constraints**:
- sem cache;
- `Decimal` em todas as contas;
- sem dados anteriores a 01/01/2026;
- nenhuma mudança na importação das saídas nem no robô de lançamento.

**Scale/Scope**:
- 3 modelos novos, 1 tipo novo de `Importacao`;
- 1 página nova com 4 abas, 3 telas de admin, 1 comando;
- mudança no catálogo do formulário AB e na saúde do catálogo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano cumpre | Situação |
|---|---|---|
| I. Regras puras e fiéis à origem | Resolução do canônico, consolidação, curva e reposição são funções puras sem ORM (`catalogo/depara.py`, `catalogo/curva.py`), com as fórmulas lidas da planilha (research D5, D6). As 7 divergências estão registradas na spec. | ✅ |
| II. Uma porta de gravação | Nada grava em `pedidos`. Os modelos novos são cadastros do `catalogo`, gravados pelo admin e pela carga, que roda numa transação. | ✅ |
| III. Nunca lançar duas vezes no SCPI | Não mexe no robô, nas `LinhaSaida` nem no `LANCAMENTO_REAL`. O formulário AB continua gerando os mesmos pedidos, só com o catálogo ordenado de outro jeito. | ✅ |
| IV. Dados importados não se perdem em silêncio | A carga junta todos os problemas, tem ensaio, grava tudo ou nada, registra uma `Importacao` e recusa sobrescrever pares editados no sistema (research D8). Nada nas saídas importadas é alterado. | ✅ |
| V. Testes contra o banco real | Funções puras testadas sem banco; formulário AB, admin, páginas e carga testados no MySQL/MariaDB; nenhum teste abre o navegador. | ✅ |
| VI. Interface em pt-BR e acessível | Textos em pt-BR, design system Clean, classe e situação sempre com texto, códigos em mono, ícone Lucide local. | ✅ |
| Restrições técnicas | Sem dependência nova; migrations pela regra do projeto (research D11); nada novo no `.env`. | ✅ |
| Fluxo de desenvolvimento | Spec e plano antes do código; os quatro portões no `quickstart.md`; o `CLAUDE.md` é atualizado no mesmo PR (`catalogo`, `implantacao`, comando novo). | ✅ |

**Reavaliação depois da Fase 1**: o desenho (data-model, contratos) não introduziu nada fora da
tabela acima. Nenhuma violação; *Complexity Tracking* fica vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-depara-curva-abc/
├── plan.md              # este arquivo
├── research.md          # Fase 0: decisões D1–D12
├── data-model.md        # Fase 1: ParDePara, ConfiguracaoCurva, ParametroReposicao
├── quickstart.md        # Fase 1: roteiro de validação
├── contracts/
│   ├── paginas.md       # página Curva ABC, admin e formulário AB
│   └── importar_depara.md  # comando de carga dos pares
├── checklists/
│   └── requirements.md  # checklist de qualidade da spec
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
catalogo/
├── models.py            # + ParDePara, ConfiguracaoCurva, ParametroReposicao; Importacao.Tipo.DEPARA
├── depara.py            # novo, puro: validar_par, resolver_canonicos, consolidar
├── curva.py             # novo, puro: periodo, curva (A/B/C), reposicao, pendentes
├── consultas_curva.py   # novo: agregação das saídas por código e montagem a partir do banco
├── catalogos.py         # catalogo_ab() passa a usar a consolidação e a janela
├── saude.py             # sem cadastro e pendentes passam a considerar o canônico
├── admin.py             # + admins dos três modelos novos
├── views.py             # + view curva
├── urls.py              # + "curva/"
├── migrations/0001_initial.py   # regenerada (a importação das planilhas ainda não ocorreu, research D11)
└── templates/catalogo/
    ├── curva.html       # novo: página com abas
    └── _curva_*.html    # novos: tabela de cada aba

implantacao/
├── planilha.py          # ler_xlsx ganha o parâmetro `abas`
├── depara.py            # novo: leitura e validação dos pares da planilha (sem banco)
└── management/commands/importar_depara.py   # novo

interface/
├── navegacao.py         # + item "Curva ABC"
└── templates/interface/_icone.html   # + ícone de gráfico

tests/
├── test_depara.py           # novo: validação e resolução (puro) + admin
├── test_curva.py            # novo: curva, reposição, período (puro)
├── test_importar_depara.py  # novo: carga, ensaio, travas
├── test_pagina_curva.py     # novo: página e abas
└── test_catalogos.py        # AB consolidado; limite de consultas 5 → 6

docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md   # SaidaSCPI ≠ MOV_NORM (FR-022)
deploy/VIRADA.md         # manter a planilha até a carga conferida; passo do importar_depara
CLAUDE.md                # catalogo, implantacao e o comando novo
```

**Structure Decision**: segue os apps existentes. O de/para e os cálculos são cadastro e consulta
do catálogo, por isso ficam no `catalogo`. A carga da planilha é migração única, por isso fica no
`implantacao`, que pode ser apagado depois da virada. Nenhum app novo.

## Complexity Tracking

Sem violações da constituição.

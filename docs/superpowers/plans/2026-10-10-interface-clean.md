# Interface no estilo Clean — plano de implementação

> **Situação:** executado. As caixas abaixo não foram marcadas durante a execução; o que vale
> hoje está no código e no `CLAUDE.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar toda a fundação visual herdada do WMS-Almoxarifado pelo design system Clean.
Isso cobre páginas públicas, login e área do almoxarifado, com vocabulário de CSS próprio,
só tema claro, fontes servidas localmente e azul `#2563EB` como destaque. Comportamento,
URLs e textos continuam os mesmos.

**Architecture:**
- Três CSS novos em `interface/static/interface/css/`:
  - `clean.css`: tokens, fontes, tipografia e ritmos;
  - `componentes.css`;
  - `layouts.css`: público, casca do almoxarifado e impressão.
- Ícones Lucide num include (`interface/_icone.html`).
- Os templates de todas as apps são reescritos com o vocabulário novo. Os CSS de cada app
  (`pedidos.css`, `catalogo.css`, `entrar.css`) ficam só com o que é próprio delas.

**Tech Stack:** Django 6 templates, HTMX 4.0.0 (vendorizado), CSS puro sem build, JavaScript
puro, pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-interface-clean-design.md`. Ela atualiza a seção 2
("Interface") da spec principal, `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`.

## Global Constraints

- **Skills, em toda tarefa que mexe em CSS ou template:**
  - carregue antes `clean-design` (`.claude/skills/clean-design/`). Ela é a autoridade
    visual, mas onde ela e a spec divergem vale a spec (tema só claro, dois ritmos, nada de
    seções de landing page, sem *scroll reveal*);
  - `frontend-design` serve de apoio de composição (hierarquia, estados, acabamento), sem
    trazer fontes, cores ou estéticas fora do Clean;
  - `ui-ux-pro-max` só como consulta de diretrizes de UX e acessibilidade, na revisão final.
- **Cores** (spec, seção 2):
  - neutros: fundo `#FFFFFF`, superfície `#F7F6F2`, texto `#0F0E0C`, texto secundário
    `#6B6760`, texto suave `#A8A49F`, borda `#E8E6E1`;
  - destaque: `#2563EB`, hover `#1D4ED8`;
  - status:
    - ok: `#ECF7EE`/`#1E6B34`;
    - aviso: `#FDF4E3`/`#8A5A00`;
    - erro: `#FCEDEC`/`#A3261D`;
    - informação: `#EFF4FF`/`#1D4ED8`;
    - neutro: `#F7F6F2`/`#6B6760`.
  - Nenhuma outra cor, nenhum gradiente.
- **Fontes:** Geist (títulos), DM Sans (texto), Geist Mono (códigos), em `.woff2` locais em
  `interface/static/interface/fonts/`. Nunca Inter, Roboto, Arial ou system-ui como fonte
  principal. Nada de Google Fonts ou CDN.
- **Tema:** só claro. Nenhuma página carrega `data-theme-toggle`, `data-theme` ou `almox-tema`.
- **Forma:** raios de 12px (cards), 8px (botões e campos) e 100px (selos); múltiplos de 8 no
  espaçamento; sombras do guia; ícones SVG Lucide (traço 1.5, `currentColor`); nenhum emoji
  na interface.
- **Movimento:** só transições de 0.18s, `scale(.98)` no clique e o `fadeUp` do sucesso;
  `prefers-reduced-motion` zera tudo.
- **Regras do projeto que continuam:**
  - estado nunca só por cor;
  - códigos em `.mono`;
  - foco visível;
  - alvos de toque com no mínimo 44px no celular;
  - tabelas com rolagem lateral;
  - scripts no `<head>` com `defer`;
  - logout por POST num formulário único;
  - o `<meta name="htmx-config">` com `noSwap` continua no `base.html`.
- **O que não muda:** comportamento, URLs, ids usados pelo HTMX (`#formulario`,
  `#busca-materiais`, `#resultados`, `#carrinho`, `#lista-pedidos`, `#situacao-catalogo`),
  nomes de campos, textos e regras.
- **Testes:**
  - asserção que procura classe ou HTML antigo é atualizada para o vocabulário novo, sem
    perder o que verifica;
  - nenhum teste de comportamento é removido;
  - teste que dependa só de uma tag ou template removido sai junto com ele.
- **Commits:** no branch `interface-clean`, com
  `git -c user.name="João" -c user.email="jm_zr@icloud.com" commit ...`. Toda mensagem termina
  com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Ao fim de cada tarefa:** `uv run ruff format -q .`, `uv run ruff check .` e
  `uv run pytest -q` verdes.
- Arquivos com aspas ou JavaScript são escritos com a ferramenta Write, não com heredoc.

## Vocabulário de classes

Todas as tarefas usam estes nomes, e nenhum outro para essas funções.

| Função | Classes |
|---|---|
| Ritmo (no `<body>`) | `ritmo-publico`, `ritmo-almox` |
| Texto | `rotulo-secao` (versalete), `texto-secundario`, `texto-suave`, `texto-pequeno`, `mono`, `visually-hidden` |
| Pilhas e grades | `pilha` (gap 16), `pilha-larga` (gap do ritmo), `grade-2` (2 colunas; 1 abaixo de 640px), `linha` (flex com quebra, gap 8) |
| Botões | `botao` + `botao-primario`, `botao-secundario`, `botao-texto`, `botao-perigo` (com `botao-texto`), `botao-icone`, `botao-bloco` (largura total abaixo de 640px) |
| Campos | `campo` (div), `campo-rotulo` (label), `campo-entrada` (input, select ou textarea), `campo-dica`, `campo-erro`, `campo-com-erro` (no `campo`), `campo-check` (label com checkbox), `campo-busca` (div com ícone) |
| Cartões | `cartao`, `cartao-titulo`, `cartao-sutil` (fundo `#F7F6F2`), `cartao-opcao` (link clicável) |
| Selos | `selo` + `selo-ok`, `selo-aviso`, `selo-erro`, `selo-info`, `selo-neutro` |
| Avisos | `aviso` + `aviso-ok`, `aviso-atencao`, `aviso-erro`, `aviso-info` |
| Tabela | `tabela-rolagem` (wrapper), `tabela`, `tabela-data`, `tabela-vazia` |
| Paginação | `paginacao`, `paginacao-resumo`, `paginacao-lista`, `paginacao-link`, `paginacao-atual`, `paginacao-desativado`, `paginacao-reticencia`, `paginacao-larga`, `paginacao-compacta` |
| Filtros | `filtros`, `filtros-campo`, `filtros-acoes` |
| Passos | `passo`, `passo-numero`, `passo-cabecalho`, `passo-corpo` |
| Materiais | `lista-materiais`, `material`, `material-bloqueado`, `material-dados`, `material-acao`, `quantidade`, `quantidade-campo` |
| Carrinho | `carrinho`, `carrinho-linha`, `carrinho-linha-erro` |
| Vazio | `vazio`, `vazio-titulo` |
| Dados | `dados` (`<dl>` em grade de rótulo e valor) |
| Ações | `acoes` (linha de botões no fim de um formulário) |
| Layout público | `publico-topo`, `publico-topo-interno`, `publico-conteudo`, `publico-cabecalho`, `publico-sub`, `publico-rodape`, `marca`, `link-discreto` |
| Casca do almoxarifado | `app`, `app-lateral`, `app-lateral-topo`, `app-lateral-painel`, `app-menu`, `app-menu-item`, `app-menu-botao`, `app-conta`, `app-principal`, `pagina-cabecalho`, `pagina-sub`, `pagina-acoes` |
| Impressão | `nao-imprimir`, `so-tela`, `folha-recibo` (mantidas) |

Classes antigas que somem dos templates (mapa para quem migra):

| Antiga | Nova |
|---|---|
| `btn` | `botao botao-secundario` |
| `btn btn-primary` | `botao botao-primario` |
| `btn btn-secondary-danger` | `botao botao-texto botao-perigo` |
| `card` | `cartao` |
| `page-section` | — (o espaço vem da `pilha-larga` em volta) |
| `field` (em input, select ou textarea) | `campo-entrada` |
| `field-label` | `campo-rotulo` |
| `field-hint` | `campo-dica` |
| `field-check` | `campo-check` |
| `error-box` | `aviso aviso-erro` |
| `alert alert-info` | `aviso aviso-info` |
| `alert alert-success` | `aviso aviso-ok` |
| `alert alert-warning` | `aviso aviso-atencao` |
| `badge badge-success` | `selo selo-ok` |
| `badge-warning` | `selo-aviso` |
| `badge-danger` | `selo-erro` |
| `badge-info` | `selo-info` |
| `badge-neutral`, `badge-plain` | `selo-neutro` |
| `text-muted`, `cell-secondary` | `texto-secundario` |
| `text-link` | — (o `<a>` já é link) |
| `table-wrapper` | `tabela-rolagem` |
| `table` | `tabela` |
| `table-cell-date` | `tabela-data` |
| `table-empty-row` | `tabela-vazia` |
| `empty-state` | `vazio` |
| `empty-state-title` | `vazio-titulo` |
| `filter-bar` | `filtros` |
| `filter-bar-field` | `filtros-campo` |
| `filter-bar-actions` | `filtros-acoes` |
| `form-actions` | `acoes` |
| `grid` | `grade-2` |

## Review Focus

1. **Celular com 375px:** a página não pode ganhar rolagem horizontal; a tabela rola dentro do
   próprio wrapper. É coberto por testes de que toda `<table class="tabela">` fica dentro de
   `.tabela-rolagem` (Tarefas 5 e 6).
2. **Bloco vazio no cabeçalho** (página sem rótulo ou subtítulo): sem buraco no layout. O
   `<p>` sai sem espaço dentro, para o `:empty` funcionar. É coberto por um teste do HTML
   renderizado (Tarefa 3).
3. **Recibo impresso:** sai só o recibo, sem barra lateral, cabeçalho, mensagens ou cores de
   fundo. É coberto por um teste das regras `@media print` do `layouts.css` (Tarefa 3) e
   pela conferência visual (Tarefa 8).
4. **Fonte que não carrega** (arquivo ausente ou rede lenta): o texto aparece na fonte
   reserva na hora. É coberto pelo teste de `font-display: swap` e de que os sete `.woff2`
   existem (Tarefa 1).
5. **Navegação por teclado:** todo controle tem foco visível, e o menu móvel abre e fecha
   pelo teclado. É coberto pelo teste da regra `:focus-visible` (Tarefa 1), do `aria-expanded`
   no botão do menu (Tarefa 3) e pela conferência visual.

---

### Task 1: Fundação, fontes e ícones

**Files:**
- Create: `interface/static/interface/css/clean.css`,
  `interface/static/interface/fonts/` (sete `.woff2` e três `OFL-*.txt`),
  `interface/templates/interface/_icone.html`, `tests/test_clean.py`
- Modify: `interface/templates/interface/base.html`, `THIRD-PARTY-NOTICES.md`
- Delete: `interface/static/interface/css/tokens.css`, `base.css`, `components.css`,
  `publico.css`
- Modify: `tests/test_interface.py` (`test_layout_publico_carrega_assets_no_head` e
  `test_layout_publico_sem_barra_lateral_e_com_um_main`)

**Interfaces:**
- Produces:
  - `clean.css` com os tokens e as classes de texto, pilha e ícone do vocabulário;
  - `interface/_icone.html`, usado com
    `{% include "interface/_icone.html" with nome="busca" %}`, que renderiza
    `<svg class="icone" ...>` ou nada;
  - blocos do `base.html`: `title`, `extra_css`, `extra_head`, `body_class`, `content`,
    `extra_js`.

- [ ] **Step 1: Baixar as fontes (pedir confirmação ao usuário antes)**

Fonte: pacotes `@fontsource/geist-sans`, `@fontsource/dm-sans` e `@fontsource/geist-mono` no
jsDelivr.
1. Ache a versão estável mais recente de cada um em
   `https://data.jsdelivr.com/v1/package/npm/@fontsource/<pacote>` e fixe-a.
2. Diga ao usuário os sete arquivos, a origem e o tamanho aproximado (uns 20 KB cada) e
   espere o "pode baixar".
3. Baixe para uma pasta nova do scratchpad e só depois copie para
   `interface/static/interface/fonts/`:
   - `geist-sans-latin-600-normal.woff2` e `geist-sans-latin-700-normal.woff2`;
   - `dm-sans-latin-400-normal.woff2`, `dm-sans-latin-500-normal.woff2` e
     `dm-sans-latin-600-normal.woff2`;
   - `geist-mono-latin-400-normal.woff2` e `geist-mono-latin-500-normal.woff2`.
4. Baixe o `LICENSE` de cada pacote (OFL 1.1) e salve como `OFL-Geist.txt`, `OFL-DMSans.txt`
   e `OFL-GeistMono.txt`.

URL de cada arquivo: `https://cdn.jsdelivr.net/npm/@fontsource/<pacote>@<versão>/files/<arquivo>`.

- [ ] **Step 2: Testes que falham** (`tests/test_clean.py`)

```python
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string

FONTES = [
    "geist-sans-latin-600-normal.woff2",
    "geist-sans-latin-700-normal.woff2",
    "dm-sans-latin-400-normal.woff2",
    "dm-sans-latin-500-normal.woff2",
    "dm-sans-latin-600-normal.woff2",
    "geist-mono-latin-400-normal.woff2",
    "geist-mono-latin-500-normal.woff2",
]


def css(nome):
    return Path(finders.find(f"interface/css/{nome}")).read_text(encoding="utf-8")


@pytest.mark.parametrize("arquivo", FONTES)
def test_fontes_locais_existem_e_tem_font_face(arquivo):
    assert finders.find(f"interface/fonts/{arquivo}")
    assert f"../fonts/{arquivo}" in css("clean.css")


def test_licencas_das_fontes():
    for nome in ("OFL-Geist.txt", "OFL-DMSans.txt", "OFL-GeistMono.txt"):
        assert finders.find(f"interface/fonts/{nome}")


def test_tokens_do_clean():
    texto = css("clean.css")
    for valor in ("#ffffff", "#f7f6f2", "#0f0e0c", "#6b6760", "#a8a49f", "#e8e6e1",
                  "#2563eb", "#1d4ed8", "font-display: swap", ":focus-visible",
                  "prefers-reduced-motion"):
        assert valor in texto.lower()
    for proibido in ("system-ui", "Inter", "Roboto", "Arial", "gradient"):
        assert proibido not in texto


def test_fundacao_antiga_removida():
    for nome in ("tokens.css", "base.css", "components.css", "publico.css"):
        assert finders.find(f"interface/css/{nome}") is None


def test_icone_conhecido_e_desconhecido():
    svg = render_to_string("interface/_icone.html", {"nome": "busca"})
    assert '<svg class="icone"' in svg and 'aria-hidden="true"' in svg
    assert 'stroke-width="1.5"' in svg
    assert render_to_string("interface/_icone.html", {"nome": "xyz"}).strip() == ""


def test_base_sem_tema_e_com_css_novo():
    html = render_to_string("interface/base.html", {})
    head = html.split("</head>")[0]
    assert "interface/css/clean.css" in head
    assert "almox-tema" not in html and "data-theme" not in html
    assert 'src="/static/interface/js/shell.js" defer' in head
    assert '<meta name="htmx-config"' in head
```

Em `tests/test_interface.py`, `test_layout_publico_carrega_assets_no_head` passa a conferir
`interface/css/clean.css`, `componentes.css` e `layouts.css` no `<head>` (as duas últimas
entram nas Tarefas 2 e 3; nesta tarefa, confira só `clean.css`). A linha `'"almox-tema"' in
head` vira `not in`. Em `test_layout_publico_sem_barra_lateral_e_com_um_main`, a linha
`"data-theme-toggle" in html` vira `not in`.

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_clean.py tests/test_interface.py -q`
Expected: FAIL (`clean.css` e `_icone.html` não existem; o tema ainda aparece).

- [ ] **Step 4: `clean.css`**

```css
/*
 * Clean — fundação visual do Central Almoxarifado (docs/DESIGN.md; skill clean-design).
 * Tokens, fontes, tipografia, ritmos e utilitários. Só tema claro.
 */

@font-face { font-family: "Geist"; src: url("../fonts/geist-sans-latin-600-normal.woff2") format("woff2"); font-weight: 600; font-style: normal; font-display: swap; }
@font-face { font-family: "Geist"; src: url("../fonts/geist-sans-latin-700-normal.woff2") format("woff2"); font-weight: 700; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("../fonts/dm-sans-latin-400-normal.woff2") format("woff2"); font-weight: 400; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("../fonts/dm-sans-latin-500-normal.woff2") format("woff2"); font-weight: 500; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("../fonts/dm-sans-latin-600-normal.woff2") format("woff2"); font-weight: 600; font-style: normal; font-display: swap; }
@font-face { font-family: "Geist Mono"; src: url("../fonts/geist-mono-latin-400-normal.woff2") format("woff2"); font-weight: 400; font-style: normal; font-display: swap; }
@font-face { font-family: "Geist Mono"; src: url("../fonts/geist-mono-latin-500-normal.woff2") format("woff2"); font-weight: 500; font-style: normal; font-display: swap; }

:root {
  --fundo: #ffffff;
  --superficie: #f7f6f2;
  --texto: #0f0e0c;
  --texto-secundario: #6b6760;
  --texto-suave: #a8a49f;
  --borda: #e8e6e1;
  --destaque: #2563eb;
  --destaque-hover: #1d4ed8;
  --destaque-texto: #ffffff;
  --destaque-superficie: #eff4ff;
  --ok-superficie: #ecf7ee;
  --ok-texto: #1e6b34;
  --aviso-superficie: #fdf4e3;
  --aviso-texto: #8a5a00;
  --erro-superficie: #fcedec;
  --erro-texto: #a3261d;
  --info-superficie: var(--destaque-superficie);
  --info-texto: var(--destaque-hover);
  --neutro-superficie: var(--superficie);
  --neutro-texto: var(--texto-secundario);

  --fonte-titulo: "Geist", "DM Sans", sans-serif;
  --fonte-texto: "DM Sans", sans-serif;
  --fonte-mono: "Geist Mono", ui-monospace, monospace;

  --esp-meio: 4px;
  --esp-1: 8px;
  --esp-2: 16px;
  --esp-3: 24px;
  --esp-4: 32px;
  --esp-6: 48px;
  --esp-8: 64px;
  --esp-12: 96px;
  --esp-16: 128px;

  --raio-cartao: 12px;
  --raio-controle: 8px;
  --raio-pilula: 100px;

  --sombra-cartao: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.04);
  --sombra-hover: 0 6px 20px rgba(0, 0, 0, 0.08);
  --sombra-elevada: 0 8px 30px rgba(0, 0, 0, 0.09);
  --anel-foco: 0 0 0 2px var(--fundo), 0 0 0 4px var(--destaque);
  --transicao: 0.18s ease;

  /* Ritmo: os valores mudam com .ritmo-publico / .ritmo-almox no <body>. */
  --texto-corpo: 16px;
  --titulo-1: 32px;
  --recheio-cartao: var(--esp-3);
  --entre-blocos: var(--esp-4);
  --celula-v: 12px;
  --celula-h: 16px;
  --altura-controle: 44px;
}

.ritmo-publico {
  --texto-corpo: 17px;
  --titulo-1: clamp(32px, 5vw, 48px);
  --recheio-cartao: var(--esp-4);
  --entre-blocos: var(--esp-6);
}

.ritmo-almox {
  --texto-corpo: 15px;
  --titulo-1: 24px;
  --recheio-cartao: var(--esp-3);
  --entre-blocos: var(--esp-3);
  --celula-v: 10px;
  --celula-h: 12px;
  --altura-controle: 40px;
}

*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--fundo);
  color: var(--texto);
  font-family: var(--fonte-texto);
  font-size: var(--texto-corpo);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4 {
  margin: 0;
  font-family: var(--fonte-titulo);
  color: var(--texto);
  letter-spacing: -0.02em;
  line-height: 1.2;
}
h1 { font-size: var(--titulo-1); font-weight: 700; line-height: 1.1; }
h2 { font-size: 1.25em; font-weight: 600; }
h3 { font-size: 1.05em; font-weight: 600; letter-spacing: -0.01em; }
p, ul, ol, dl, dd { margin: 0; }
ul, ol { padding-left: 1.2em; }

a { color: var(--destaque); text-decoration: none; transition: color var(--transicao); }
a:hover { color: var(--destaque-hover); text-decoration: underline; text-underline-offset: 3px; }

button, input, select, textarea { font: inherit; color: inherit; }

:focus-visible { outline: none; box-shadow: var(--anel-foco); border-radius: var(--raio-controle); }

.mono { font-family: var(--fonte-mono); font-size: 0.92em; letter-spacing: 0; }
.texto-secundario { color: var(--texto-secundario); }
.texto-suave { color: var(--texto-suave); }
.texto-pequeno { font-size: 0.875em; }

.rotulo-secao {
  font-family: var(--fonte-texto);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--texto-suave);
}
.rotulo-secao:empty { display: none; }

.visually-hidden {
  position: absolute !important;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0);
  white-space: nowrap; border: 0;
}

.pilha { display: grid; gap: var(--esp-2); }
.pilha-larga { display: grid; gap: var(--entre-blocos); }
.linha { display: flex; flex-wrap: wrap; align-items: center; gap: var(--esp-1); }
.grade-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--esp-2) var(--esp-3); }
@media (max-width: 640px) { .grade-2 { grid-template-columns: 1fr; } }

.icone { display: inline-block; flex: none; width: 18px; height: 18px; vertical-align: middle; }

@keyframes subir {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 5: `_icone.html`**

Escreva com a ferramenta Write. É um `{% if %}`/`{% elif %}` por nome, sem `else`, para nome
desconhecido não renderizar nada. A moldura é igual em todos os ramos:
`<svg class="icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">…</svg>`.
O comentário no topo diz que os traços são do Lucide (ISC).

O arquivo não pode soltar espaço antes do `<svg>`: a Tarefa 3 depende de `>{% include %}`
virar `><svg`. Faça assim:
- o comentário vai num `{# … #}` colado ao primeiro `{% if %}`, na mesma linha;
- nenhuma quebra de linha antes do `<svg>` em nenhum ramo (`{% if nome == "caixa" %}<svg …>…</svg>{% elif … %}`).

Acrescente ao teste do Step 2:
`assert render_to_string("interface/_icone.html", {"nome": "busca"}).startswith("<svg")`.

O conteúdo de cada ramo, em traços Lucide:

| nome | conteúdo |
|---|---|
| `caixa` | `<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>` |
| `busca` | `<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>` |
| `mais` | `<path d="M5 12h14"/><path d="M12 5v14"/>` |
| `menos` | `<path d="M5 12h14"/>` |
| `lixeira` | `<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>` |
| `impressora` | `<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>` |
| `sair` | `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>` |
| `seta-direita` | `<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>` |
| `seta-esquerda` | `<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>` |
| `alerta` | `<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>` |
| `check` | `<path d="M20 6 9 17l-5-5"/>` |
| `menu` | `<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>` |
| `fechar` | `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>` |
| `painel` | `<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>` |
| `recibo` | `<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>` |
| `catalogo` | `<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>` |
| `cadastros` | `<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>` |
| `saida` | `<path d="M21 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6"/><path d="m21 3-9 9"/><path d="M15 3h6v6"/>` |

- [ ] **Step 6: `base.html`**

Escreva com a ferramenta Write:

```django
{% load static %}<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{% block title %}Central Almoxarifado{% endblock %}</title>
  {% comment %}
  Base comum aos dois layouts. Só tema claro (spec da interface Clean). O `html.js` mostra o
  botão do menu móvel. Scripts no <head> com `defer`, nunca no <body>: ao restaurar o
  histórico o HTMX troca o <body> e re-executaria os scripts. O HTMX 4 troca o conteúdo mesmo
  em resposta 4xx/5xx: o `noSwap` impede que uma falha apague o formulário montado.
  {% endcomment %}
  <script>document.documentElement.classList.add("js");</script>
  <meta name="htmx-config" content='{"noSwap":[204,304,"4xx","5xx"]}'>
  <link rel="preload" href="{% static 'interface/fonts/dm-sans-latin-400-normal.woff2' %}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{% static 'interface/css/clean.css' %}">
  {% block extra_css %}{% endblock %}
  <script src="{% static 'interface/js/shell.js' %}" defer></script>
  <script src="{% static 'interface/vendor/htmx/htmx-4.0.0.min.js' %}" defer></script>
  {% block extra_head %}{% endblock %}
</head>
<body class="{% block body_class %}{% endblock %}">
  {% block content %}{% endblock %}
  {% block extra_js %}{% endblock %}
</body>
</html>
```

Apague os quatro CSS antigos.

Em `THIRD-PARTY-NOTICES.md`, acrescente a seção "Fontes (SIL Open Font License 1.1)":
- Geist e Geist Mono (Vercel);
- DM Sans (Colophon Foundry / Google);
- a origem (pacotes `@fontsource` com a versão fixada) e o caminho das licenças em
  `interface/static/interface/fonts/OFL-*.txt`;
- a menção aos ícones Lucide (ISC), com o aviso de copyright do Lucide.

- [ ] **Step 7: Rodar e ver passar**

Run: `uv run pytest tests/test_clean.py tests/test_interface.py -q`
Expected: PASS.

- [ ] **Step 8: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS. As páginas ficam sem estilo até as próximas tarefas; nenhum teste de
comportamento depende de CSS.

Commit — `Fundação Clean: tokens, fontes locais e ícones; sai o tema escuro`

---

### Task 2: Componentes, mensagens e paginação

**Files:**
- Create: `interface/static/interface/css/componentes.css`
- Modify: `interface/templates/interface/base.html` (link do `componentes.css` depois do
  `clean.css`), `interface/templates/interface/_mensagens.html`,
  `interface/templates/interface/_paginacao.html`,
  `interface/templatetags/interface_extras.py`, `tests/test_interface.py`, `tests/test_clean.py`
- Delete: `interface/templates/interface/_th_ordenavel.html`

**Interfaces:**
- Consumes: os tokens da Tarefa 1.
- Produces: as classes de botões, campos, cartões, selos, avisos, tabela, paginação, filtros,
  passos, materiais, quantidade, carrinho, vazio, dados e ações do vocabulário.

- [ ] **Step 1: Testes que falham**

Em `tests/test_interface.py`, `test_mensagens_por_nivel` passa a esperar
`(ERROR, "aviso aviso-erro", "alert")`, `(SUCCESS, "aviso aviso-ok", "status")`,
`(WARNING, "aviso aviso-atencao", "status")` e `(INFO, "aviso aviso-info", "status")`.

Saem os testes de `querystring_ordenacao`, `rotulo_ordenacao` e `truncar_meio`, e os que
renderizam `_th_ordenavel.html` (essas tags e o template saem nesta tarefa, sem uso no
projeto). Ficam os de `querystring_pagina`, `intervalo_paginas`, `separador_milhar` e
`quantidade`.

Acrescente a `tests/test_clean.py`:

```python
def test_componentes_carregados_e_com_o_vocabulario():
    html = render_to_string("interface/base.html", {})
    assert "interface/css/componentes.css" in html.split("</head>")[0]
    texto = css("componentes.css")
    for classe in (".botao-primario", ".campo-entrada", ".cartao", ".selo-ok", ".aviso-erro",
                   ".tabela-rolagem", ".paginacao-atual", ".passo-numero", ".quantidade",
                   ".carrinho", ".vazio", ".dados"):
        assert classe in texto


def test_paginacao_no_vocabulario_novo(rf):
    from django.core.paginator import Paginator
    pagina = Paginator(list(range(100)), 10).get_page(3)
    html = render_to_string(
        "interface/_paginacao.html",
        {"pagina": pagina, "parametro": "pagina", "rotulo": "Paginação"},
        request=rf.get("/"),
    )
    assert 'class="paginacao"' in html and "paginacao-atual" in html
    assert 'aria-current="page"' in html and "pagination" not in html
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_clean.py tests/test_interface.py -q`
Expected: FAIL.

- [ ] **Step 3: `componentes.css`**

Escreva com a ferramenta Write:

```css
/* Componentes do Clean (docs/DESIGN.md). Só usa os tokens de clean.css. */

/* Botões */
.botao {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--esp-1);
  min-height: var(--altura-controle); padding: 0 20px;
  border: 1px solid transparent; border-radius: var(--raio-controle);
  font-family: var(--fonte-texto); font-size: 0.95em; font-weight: 500; line-height: 1;
  text-decoration: none; white-space: nowrap; cursor: pointer;
  transition: background-color var(--transicao), border-color var(--transicao),
    color var(--transicao), transform var(--transicao);
}
.botao:hover { text-decoration: none; }
.botao:active { transform: scale(0.98); }
.botao[disabled], .botao[aria-disabled="true"] { opacity: 0.5; cursor: not-allowed; transform: none; }
.botao-primario { background: var(--destaque); color: var(--destaque-texto); }
.botao-primario:hover { background: var(--destaque-hover); color: var(--destaque-texto); }
.botao-secundario { background: var(--fundo); border-color: var(--borda); color: var(--texto); }
.botao-secundario:hover { background: var(--superficie); color: var(--texto); }
.botao-texto { min-height: 0; padding: var(--esp-meio) var(--esp-1); background: none; color: var(--texto-secundario); }
.botao-texto:hover { background: var(--superficie); color: var(--texto); }
.botao-perigo, .botao-perigo:hover { color: var(--erro-texto); }
.botao-icone { width: var(--altura-controle); padding: 0; }
@media (max-width: 640px) { .botao-bloco { width: 100%; } }

/* Campos */
.campo { display: grid; gap: 6px; }
.campo-rotulo { font-size: 0.875em; font-weight: 500; color: var(--texto); }
.campo-entrada {
  width: 100%; min-height: var(--altura-controle); padding: 10px 14px;
  background: var(--fundo); border: 1px solid var(--borda); border-radius: var(--raio-controle);
  transition: border-color var(--transicao), box-shadow var(--transicao);
}
.campo-entrada::placeholder { color: var(--texto-suave); }
.campo-entrada:hover { border-color: #d6d3cc; }
.campo-entrada:focus { outline: none; border-color: var(--destaque); box-shadow: 0 0 0 3px var(--destaque-superficie); }
textarea.campo-entrada { min-height: 96px; resize: vertical; }
select.campo-entrada { padding-right: 36px; }
.campo-dica { font-size: 0.85em; color: var(--texto-secundario); }
.campo-erro { font-size: 0.85em; color: var(--erro-texto); }
.campo-com-erro .campo-entrada { border-color: var(--erro-texto); }
.campo-check { display: flex; align-items: flex-start; gap: 10px; cursor: pointer; }
.campo-check input { width: 18px; height: 18px; margin-top: 3px; accent-color: var(--destaque); }
.campo-busca { position: relative; }
.campo-busca .icone { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--texto-suave); pointer-events: none; }
.campo-busca .campo-entrada { padding-left: 42px; }

/* Cartões */
.cartao {
  background: var(--fundo); border: 1px solid var(--borda); border-radius: var(--raio-cartao);
  box-shadow: var(--sombra-cartao); padding: var(--recheio-cartao);
}
.cartao-titulo { margin-bottom: var(--esp-2); }
.cartao-sutil { background: var(--superficie); box-shadow: none; }
.cartao-opcao {
  display: grid; gap: var(--esp-1); color: inherit; text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.cartao-opcao:hover { color: inherit; text-decoration: none; transform: translateY(-2px); box-shadow: var(--sombra-hover); }
.cartao-opcao .icone { width: 24px; height: 24px; }
.cartao-opcao-seta { margin-top: var(--esp-1); color: var(--destaque); transition: transform var(--transicao); }
.cartao-opcao:hover .cartao-opcao-seta { transform: translateX(4px); }

/* Selos (estado sempre com texto) */
.selo {
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px;
  border-radius: var(--raio-pilula); font-size: 0.8em; font-weight: 500; line-height: 1.6; white-space: nowrap;
}
.selo-ok { background: var(--ok-superficie); color: var(--ok-texto); }
.selo-aviso { background: var(--aviso-superficie); color: var(--aviso-texto); }
.selo-erro { background: var(--erro-superficie); color: var(--erro-texto); }
.selo-info { background: var(--info-superficie); color: var(--info-texto); }
.selo-neutro { background: var(--neutro-superficie); color: var(--neutro-texto); border: 1px solid var(--borda); }

/* Avisos */
.aviso {
  display: flex; gap: var(--esp-1); align-items: flex-start;
  padding: 14px var(--esp-2); border-radius: var(--raio-controle); font-size: 0.95em;
}
.aviso > .icone { margin-top: 3px; }
.aviso ul { margin-top: var(--esp-meio); }
.aviso-ok { background: var(--ok-superficie); color: var(--ok-texto); }
.aviso-atencao { background: var(--aviso-superficie); color: var(--aviso-texto); }
.aviso-erro { background: var(--erro-superficie); color: var(--erro-texto); }
.aviso-info { background: var(--info-superficie); color: var(--info-texto); }
.aviso:empty { display: none; }

/* Tabela */
.tabela-rolagem { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.tabela { width: 100%; border-collapse: collapse; font-size: 0.95em; }
.tabela th {
  padding: var(--celula-v) var(--celula-h); text-align: left; white-space: nowrap;
  font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--texto-suave); border-bottom: 1px solid var(--borda);
}
.tabela td { padding: var(--celula-v) var(--celula-h); border-bottom: 1px solid var(--borda); vertical-align: top; }
.tabela tbody tr { transition: background-color var(--transicao); }
.tabela tbody tr:hover { background: var(--superficie); }
.tabela tbody tr:last-child td { border-bottom: 0; }
.tabela-data { white-space: nowrap; color: var(--texto-secundario); }
.tabela-vazia td { text-align: center; color: var(--texto-secundario); padding: var(--esp-4); }

/* Paginação */
.paginacao { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--esp-2); margin-top: var(--esp-2); }
.paginacao-resumo { font-size: 0.875em; color: var(--texto-secundario); }
.paginacao-lista { display: flex; flex-wrap: wrap; gap: var(--esp-meio); list-style: none; margin: 0; padding: 0; }
.paginacao-link {
  display: inline-flex; align-items: center; justify-content: center; min-width: 36px; height: 36px; padding: 0 10px;
  border: 1px solid var(--borda); border-radius: var(--raio-controle); background: var(--fundo); color: var(--texto); font-size: 0.9em;
}
a.paginacao-link:hover { background: var(--superficie); color: var(--texto); text-decoration: none; }
.paginacao-atual { background: var(--texto); border-color: var(--texto); color: var(--fundo); }
.paginacao-desativado { color: var(--texto-suave); }
.paginacao-reticencia { padding: 0 var(--esp-meio); color: var(--texto-suave); align-self: center; }
.paginacao-compacta { display: none; }
@media (max-width: 640px) { .paginacao-larga { display: none; } .paginacao-compacta { display: list-item; } }

/* Filtros */
.filtros { display: flex; flex-wrap: wrap; align-items: flex-end; gap: var(--esp-2); }
.filtros-campo { display: grid; gap: 6px; flex: 1 1 160px; min-width: 0; }
.filtros-campo:first-child { flex-basis: 240px; }
.filtros-acoes { display: flex; align-items: center; gap: var(--esp-2); }

/* Passos numerados */
.passo { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--esp-1) var(--esp-3); }
.passo-numero { font-family: var(--fonte-titulo); font-size: 32px; font-weight: 600; line-height: 1; letter-spacing: -0.02em; color: var(--texto-suave); }
.passo-cabecalho { display: grid; gap: var(--esp-meio); align-content: start; }
.passo-corpo { grid-column: 2; display: grid; gap: var(--esp-2); }
@media (max-width: 640px) { .passo { grid-template-columns: 1fr; } .passo-corpo { grid-column: 1; } }

/* Lista de materiais e quantidade */
.lista-materiais { list-style: none; margin: 0; padding: 0; border: 1px solid var(--borda); border-radius: var(--raio-cartao); max-height: 30rem; overflow-y: auto; }
.material { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--esp-2); padding: 14px var(--esp-2); border-bottom: 1px solid var(--borda); }
.material:last-child { border-bottom: 0; }
.material-dados { display: grid; gap: 2px; flex: 1 1 15rem; min-width: 0; }
.material-dados strong { font-weight: 500; }
.material-acao { display: flex; align-items: center; gap: var(--esp-1); }
.material-bloqueado .material-dados strong { color: var(--texto-secundario); }
.quantidade { display: inline-flex; align-items: center; border: 1px solid var(--borda); border-radius: var(--raio-controle); background: var(--fundo); }
.quantidade .botao-icone { min-height: 0; width: 40px; height: var(--altura-controle); border: 0; background: none; color: var(--texto-secundario); }
.quantidade .botao-icone:hover { background: var(--superficie); color: var(--texto); }
.quantidade-campo { width: 64px; min-height: var(--altura-controle); border: 0; border-inline: 1px solid var(--borda); text-align: center; background: none; }
.quantidade-campo:focus { outline: none; box-shadow: inset 0 0 0 2px var(--destaque); }

/* Carrinho */
.carrinho { display: grid; gap: var(--esp-2); padding: var(--esp-3); background: var(--superficie); border-radius: var(--raio-cartao); }
.carrinho ul { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--esp-1); }
.carrinho-linha {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--esp-1) var(--esp-2);
  padding: 12px var(--esp-2); background: var(--fundo); border: 1px solid var(--borda); border-radius: var(--raio-controle);
}
.carrinho-linha-erro { border-color: var(--erro-texto); }

/* Estado vazio */
.vazio { display: grid; justify-items: center; gap: var(--esp-1); padding: var(--esp-6) var(--esp-3); text-align: center; color: var(--texto-secundario); }
.vazio-titulo { font-family: var(--fonte-titulo); font-weight: 600; color: var(--texto); }

/* Dados (rótulo e valor) */
.dados { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--esp-2) var(--esp-3); }
.dados dt { font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; color: var(--texto-suave); }
.dados dd { overflow-wrap: anywhere; }

/* Ações de formulário */
.acoes { display: flex; flex-wrap: wrap; align-items: center; gap: var(--esp-2); }

@media (max-width: 640px) {
  .botao, .campo-entrada, .paginacao-link { min-height: 44px; }
}
```

- [ ] **Step 4: Templates**

`base.html` ganha `<link rel="stylesheet" href="{% static 'interface/css/componentes.css' %}">`
logo depois do `clean.css`.

`_mensagens.html` (escreva com Write; o comentário diz que o mapeamento dos níveis fica ali):

```django
{% if messages %}
<div class="pilha mensagens">
  {% for message in messages %}
  {% if message.tags == 'error' %}
  <div class="aviso aviso-erro" role="alert">{% include "interface/_icone.html" with nome="alerta" %}<p>{{ message }}</p></div>
  {% elif message.tags == 'success' %}
  <div class="aviso aviso-ok" role="status">{% include "interface/_icone.html" with nome="check" %}<p>{{ message }}</p></div>
  {% elif message.tags == 'warning' %}
  <div class="aviso aviso-atencao" role="status">{% include "interface/_icone.html" with nome="alerta" %}<p>{{ message }}</p></div>
  {% else %}
  <div class="aviso aviso-info" role="status"><p>{{ message }}</p></div>
  {% endif %}
  {% endfor %}
</div>
{% endif %}
```

`_paginacao.html`: troque só as classes e mantenha a estrutura, os ids estáveis e os
atributos HTMX:

| Antiga | Nova |
|---|---|
| `pagination` | `paginacao` |
| `pagination-summary` | `paginacao-resumo` |
| `pagination-list` | `paginacao-lista` |
| `pagination-item-prev` e `pagination-item-next` | sem classe |
| `pagination-item-wide` | `paginacao-larga` |
| `pagination-item-compact` | `paginacao-compacta` |
| `pagination-link` | `paginacao-link` |
| `pagination-link-current` | `paginacao-link paginacao-atual` |
| `pagination-link-disabled` | `paginacao-link paginacao-desativado` |
| `pagination-ellipsis` | `paginacao-reticencia` |

Atualize o comentário do arquivo, que cita o `docs/DESIGN.md` do WMS.

Em `interface_extras.py`, apague `querystring_ordenacao`, `rotulo_ordenacao` e `truncar_meio`
e atualize a docstring do módulo. Apague `_th_ordenavel.html`.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_clean.py tests/test_interface.py -q`
Expected: PASS.

- [ ] **Step 6: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Componentes do Clean, mensagens e paginação; saem tags do WMS sem uso`

---

### Task 3: Layouts, menu e shell

**Files:**
- Create: `interface/static/interface/css/layouts.css`
- Modify:
  - templates: `interface/templates/interface/base.html` (link do `layouts.css`),
    `base_publico.html`, `base_almoxarifado.html`, `_menu.html`;
  - código: `interface/navegacao.py`, `interface/static/interface/js/shell.js`;
  - testes: `tests/test_acesso.py`, `tests/test_formularios_publicos.py`,
    `tests/test_pagina_catalogo.py`, `tests/test_painel.py`, `tests/test_revisao_pedidos.py`,
    `tests/test_interface.py`, `tests/test_clean.py`.

**Interfaces:**
- Consumes: Tarefas 1 e 2.
- Produces:
  - **blocos do `base_publico.html`:**
    - `title`, `extra_css`, `extra_head`;
    - `rotulo` (texto do rótulo de seção; o `<p>` é do layout);
    - `heading`;
    - `sub` (o `<p class="publico-sub">` é do layout);
    - `page`, `rodape`;
  - **blocos do `base_almoxarifado.html`:** `title`, `extra_css`, `extra_head`, `rotulo`,
    `heading`, `sub` (o `<p class="pagina-sub">` é do layout), `tools`, `page`;
  - **`ItemMenu(rotulo, rota, icone="", so_equipe=False)`**, e cada item de `menu` traz a
    chave `icone`.

- [ ] **Step 1: Testes que falham**

Substitua `class="side` por `class="app-lateral` nos testes que já o usam:
- `test_acesso.py`, linhas 23 e 37;
- `test_formularios_publicos.py`, linha 57;
- `test_pagina_catalogo.py`, linha 75;
- `test_painel.py`, linha 109;
- `test_revisao_pedidos.py`, linha 69;
- `test_interface.py`, `test_layout_publico_sem_barra_lateral_e_com_um_main`.

As asserções de item atual do menu (`test_acesso.py:38` e `test_pagina_catalogo.py:49`) passam
a usar um helper. Em `test_acesso.py`, `test_menu_na_ordem_da_spec` troca `f">{r}</a>"` por
`f"<span>{r}</span>"`.

```python
def item_atual(html, url, rotulo):
    return re.search(
        rf'<a class="app-menu-item" href="{re.escape(url)}" aria-current="page">'
        rf'<svg class="icone".*?</svg><span>{rotulo}</span></a>',
        html,
        re.S,
    )
```

Acrescente a `tests/test_clean.py`:

```python
def test_layouts_carregados_e_com_impressao():
    html = render_to_string("interface/base.html", {})
    assert "interface/css/layouts.css" in html.split("</head>")[0]
    texto = css("layouts.css")
    impressao = texto[texto.index("@media print") :]
    for seletor in (".app-lateral", ".pagina-cabecalho", ".mensagens", ".nao-imprimir", ".so-tela"):
        assert seletor in impressao


def test_cabecalho_publico_vazio_sem_espaco(rf):
    html = render_to_string("interface/base_publico.html", {}, request=rf.get("/"))
    assert '<p class="rotulo-secao"></p>' in html
    assert '<p class="publico-sub"></p>' in html
    assert 'class="ritmo-publico"' in html


def test_menu_com_icone_e_botao_acessivel(admin_client):
    html = admin_client.get("/almoxarifado/").text
    assert 'class="ritmo-almox"' in html
    assert 'data-menu-toggle aria-expanded="false" aria-controls="menu-lateral"' in html
    assert '<a class="app-menu-item" href="/almoxarifado/" aria-current="page"><svg class="icone"' in html


def test_itens_do_menu_tem_icone():
    from interface.navegacao import ITENS_MENU
    assert all(item.icone for item in ITENS_MENU)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_clean.py tests/test_acesso.py tests/test_interface.py -q`
Expected: FAIL.

- [ ] **Step 3: `layouts.css`**

Escreva com a ferramenta Write:

```css
/* Layouts: público (sem login) e casca da área do almoxarifado; impressão. */

.pular { position: absolute; left: var(--esp-2); top: -100px; z-index: 10; padding: var(--esp-1) var(--esp-2); background: var(--texto); color: var(--fundo); border-radius: var(--raio-controle); }
.pular:focus { top: var(--esp-2); color: var(--fundo); }

.marca { display: inline-flex; align-items: center; gap: 10px; font-family: var(--fonte-titulo); font-weight: 600; letter-spacing: -0.01em; color: var(--texto); }
.marca:hover { color: var(--texto); text-decoration: none; }
.marca .icone { width: 22px; height: 22px; }
.link-discreto { color: var(--texto-secundario); font-size: 0.95em; }
.link-discreto:hover { color: var(--texto); }

/* Público */
.publico-topo { border-bottom: 1px solid var(--borda); background: var(--fundo); }
.publico-topo-interno, .publico-conteudo, .publico-rodape { width: 100%; max-width: 720px; margin-inline: auto; padding-inline: var(--esp-3); }
.publico-topo-interno { display: flex; align-items: center; justify-content: space-between; gap: var(--esp-2); min-height: 64px; }
.publico-conteudo { display: grid; gap: var(--entre-blocos); padding-block: var(--esp-8) var(--esp-12); }
.publico-cabecalho { display: grid; gap: var(--esp-2); }
.publico-sub { color: var(--texto-secundario); font-size: 1.05em; max-width: 36em; }
.publico-sub:empty { display: none; }
.publico-rodape { padding-block: var(--esp-4); border-top: 1px solid var(--borda); color: var(--texto-suave); font-size: 0.875em; }
@media (max-width: 640px) {
  .publico-topo-interno, .publico-conteudo, .publico-rodape { padding-inline: var(--esp-2); }
  .publico-conteudo { padding-block: var(--esp-4) var(--esp-8); }
}

/* Casca do almoxarifado */
.app { display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 100vh; background: var(--superficie); }
.app-lateral { position: sticky; top: 0; height: 100vh; display: flex; flex-direction: column; background: var(--fundo); border-right: 1px solid var(--borda); }
.app-lateral-topo { display: flex; align-items: center; justify-content: space-between; padding: 20px var(--esp-3); }
.app-menu-botao { display: none; }
.app-lateral-painel { display: flex; flex: 1; flex-direction: column; justify-content: space-between; min-height: 0; padding: var(--esp-1) var(--esp-2) var(--esp-3); overflow-y: auto; }
.app-menu { display: grid; gap: 2px; }
.app-menu-item {
  position: relative; display: flex; align-items: center; gap: 12px; padding: 10px 12px;
  border-radius: var(--raio-controle); color: var(--texto-secundario); font-weight: 500;
  transition: background-color var(--transicao), color var(--transicao);
}
.app-menu-item:hover { background: var(--superficie); color: var(--texto); text-decoration: none; }
.app-menu-item[aria-current="page"] { background: var(--superficie); color: var(--texto); }
.app-menu-item[aria-current="page"]::before { content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: var(--destaque); }
.app-conta { display: grid; gap: var(--esp-meio); padding: var(--esp-2) 12px 0; border-top: 1px solid var(--borda); }
.app-conta-nome { font-weight: 500; }
.app-conta form { margin-top: var(--esp-1); }
.app-principal { min-width: 0; display: grid; align-content: start; gap: var(--entre-blocos); padding: var(--esp-4) var(--esp-4) var(--esp-8); }
.pagina-cabecalho { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: var(--esp-2); }
.pagina-cabecalho > div:first-child { display: grid; gap: var(--esp-meio); }
.pagina-sub { color: var(--texto-secundario); }
.pagina-sub:empty { display: none; }
.pagina-acoes { display: flex; flex-wrap: wrap; align-items: center; gap: var(--esp-1); }

@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; }
  .app-lateral { position: sticky; z-index: 5; height: auto; border-right: 0; border-bottom: 1px solid var(--borda); }
  .app-lateral-topo { padding: 12px var(--esp-2); }
  .js .app-menu-botao { display: inline-flex; }
  .js .app-lateral:not([data-aberto]) .app-lateral-painel { display: none; }
  .app-lateral-painel { padding-top: 0; }
  .app-principal { padding: var(--esp-3) var(--esp-2) var(--esp-6); }
}

/* Impressão: só o conteúdo, sem casca, sem fundos */
@media print {
  .app-lateral, .pagina-cabecalho, .mensagens, .publico-topo, .publico-rodape, .pular,
  .nao-imprimir, .so-tela { display: none !important; }
  .app { display: block; background: none; }
  .app-principal { padding: 0; }
  body { background: #ffffff; color: #000000; }
  .cartao { box-shadow: none; border-color: #cccccc; }
}
```

- [ ] **Step 4: Templates e código**

`base.html` ganha o link de `layouts.css` depois de `componentes.css`.

`base_publico.html` (escreva com Write; o `<p>` não pode ter espaço dentro, para o `:empty`
funcionar):

```django
{% extends "interface/base.html" %}
{% comment %}
Layout público (sem login), pensado primeiro para o celular: cabeçalho com a marca e o link
da área do almoxarifado, coluna central de 720px. Blocos: rotulo, heading, sub, page, rodape.
{% endcomment %}
{% block body_class %}ritmo-publico{% endblock %}
{% block content %}
<a class="pular" href="#main">Pular para o conteúdo</a>
<header class="publico-topo">
  <div class="publico-topo-interno">
    <a class="marca" href="{% url 'pedidos:inicio' %}">{% include "interface/_icone.html" with nome="caixa" %}<span>Central Almoxarifado</span></a>
    <a class="link-discreto" href="{% url 'login' %}">Área do almoxarifado</a>
  </div>
</header>
<main class="publico-conteudo" id="main">
  <header class="publico-cabecalho">
    <p class="rotulo-secao">{% block rotulo %}{% endblock %}</p>
    <h1>{% block heading %}{% endblock %}</h1>
    <p class="publico-sub">{% block sub %}{% endblock %}</p>
  </header>
  {% include "interface/_mensagens.html" %}
  {% block page %}{% endblock %}
</main>
<footer class="publico-rodape">{% block rodape %}Almoxarifado SAEP{% endblock %}</footer>
{% endblock %}
```

`base_almoxarifado.html`:

```django
{% extends "interface/base.html" %}
{% comment %}
Layout da área do almoxarifado (login obrigatório): barra lateral (`_menu.html`) e a área de
trabalho com cabeçalho da página (rotulo, heading, sub, tools), mensagens e o bloco page.
{% endcomment %}
{% block body_class %}ritmo-almox{% endblock %}
{% block content %}
<a class="pular" href="#main">Pular para o conteúdo</a>
<div class="app">
  {% include "interface/_menu.html" %}
  <main class="app-principal" id="main">
    <header class="pagina-cabecalho">
      <div>
        <p class="rotulo-secao">{% block rotulo %}{% endblock %}</p>
        <h1>{% block heading %}{% endblock %}</h1>
        <p class="pagina-sub">{% block sub %}{% endblock %}</p>
      </div>
      <div class="pagina-acoes">{% block tools %}{% endblock %}</div>
    </header>
    {% include "interface/_mensagens.html" %}
    {% block page %}{% endblock %}
  </main>
</div>
{% endblock %}
```

`_menu.html` (o `{% for %}` fica numa linha só, para o `<a>` sair como no teste):

```django
{% comment %}
Barra lateral do almoxarifado. Abaixo de 900px vira cabeçalho com o botão de menu
(`interface/js/shell.js`); sem JavaScript, a navegação fica aberta. Sair é só POST com CSRF,
num único formulário.
{% endcomment %}
<aside class="app-lateral">
  <div class="app-lateral-topo">
    <a class="marca" href="{% url 'pedidos:painel' %}">{% include "interface/_icone.html" with nome="caixa" %}<span>Central Almoxarifado</span></a>
    <button type="button" class="botao botao-texto botao-icone app-menu-botao" data-menu-toggle aria-expanded="false" aria-controls="menu-lateral" aria-label="Menu">{% include "interface/_icone.html" with nome="menu" %}</button>
  </div>
  <div class="app-lateral-painel" id="menu-lateral">
    <nav class="app-menu" aria-label="Seções">
      {% for item in menu %}<a class="app-menu-item" href="{{ item.url }}"{% if item.atual %} aria-current="page"{% endif %}>{% include "interface/_icone.html" with nome=item.icone %}<span>{{ item.rotulo }}</span></a>
      {% endfor %}
    </nav>
    <div class="app-conta">
      <p class="app-conta-nome">{{ user.get_full_name|default:user.username }}</p>
      <p class="mono texto-suave texto-pequeno">{{ user.username }}</p>
      <form method="post" action="{% url 'logout' %}">
        {% csrf_token %}
        <button type="submit" class="botao botao-texto">{% include "interface/_icone.html" with nome="sair" %}Sair</button>
      </form>
    </div>
  </div>
</aside>
```

`_icone.html` precisa sair sem espaço antes do `<svg>`, para o `>{% include %}` virar
`><svg`. Se a Tarefa 1 deixou um comentário ou uma quebra de linha antes do primeiro
`{% if %}`, corrija com `{% spaceless %}` em volta do arquivo ou tirando os espaços.

`navegacao.py`:
- `ItemMenu` ganha `icone: str = ""` antes de `so_equipe`;
- `ITENS_MENU`:
  - `ItemMenu("Painel", "pedidos:painel", "painel")`;
  - `ItemMenu("Saída avulsa", "pedidos:avulsa", "saida")`;
  - `ItemMenu("Recibos", "pedidos:recibos_pendentes", "recibo")`;
  - `ItemMenu("Catálogo", "catalogo:situacao", "catalogo")`;
  - `ItemMenu("Cadastros", "admin:index", "cadastros", so_equipe=True)`;
- `menu()` acrescenta `"icone": item.icone` em cada item.

`shell.js` (escreva com Write; só o menu móvel e o "Pular para o conteúdo"; o tema sai):

```js
/*
 * Shell — menu móvel da área do almoxarifado. Carregado com `defer` no <head>; os listeners
 * ficam em `document` e sobrevivem à troca do <body> pelo HTMX. Sem JavaScript, a navegação
 * aparece aberta (o botão só existe com `html.js`).
 */
(function () {
  "use strict";

  function fechar(lateral, devolverFoco) {
    var botao = lateral.querySelector("[data-menu-toggle]");
    lateral.removeAttribute("data-aberto");
    if (botao) {
      botao.setAttribute("aria-expanded", "false");
      if (devolverFoco) botao.focus();
    }
  }

  document.addEventListener("click", function (evento) {
    var alvo = evento.target;
    if (!alvo || !alvo.closest) return;
    var botao = alvo.closest("[data-menu-toggle]");
    if (!botao) return;
    var lateral = botao.closest(".app-lateral");
    if (!lateral) return;
    if (lateral.hasAttribute("data-aberto")) {
      fechar(lateral, false);
    } else {
      lateral.setAttribute("data-aberto", "");
      botao.setAttribute("aria-expanded", "true");
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    var lateral = document.querySelector(".app-lateral[data-aberto]");
    if (lateral) fechar(lateral, true);
  });
})();
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_clean.py tests/test_acesso.py tests/test_interface.py tests/test_pagina_catalogo.py tests/test_painel.py tests/test_revisao_pedidos.py tests/test_formularios_publicos.py -q`
Expected: PASS.

- [ ] **Step 6: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Layouts Clean: página pública, barra lateral com ícones e menu móvel`

---

### Task 4: Login

**Files:**
- Modify: `contas/templates/contas/entrar.html`, `contas/static/contas/css/entrar.css`
- Test: `tests/test_acesso.py`

**Interfaces:**
- Consumes: Tarefas 1 a 3 (`base.html`, componentes e `marca`).

- [ ] **Step 1: Teste que falha** (`tests/test_acesso.py`)

```python
def test_login_no_estilo_clean(client):
    r = client.get(reverse("login"))
    assert 'class="ritmo-publico entrada-pagina"' in r.text
    assert 'class="cartao entrada-cartao"' in r.text
    assert 'class="botao botao-primario botao-bloco"' in r.text
    r = entrar(client, senha="errada")
    assert 'class="aviso aviso-erro"' in r.text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_acesso.py -q`
Expected: FAIL.

- [ ] **Step 3: `entrar.html` e `entrar.css`**

`entrar.html` (escreva com Write; mantém os campos, o erro ligado por `aria-describedby` e o
texto de recuperação):

```django
{% extends "interface/base.html" %}
{% load static %}
{% block title %}{% if form.errors %}Erro: {% endif %}Entrar — Central Almoxarifado{% endblock %}
{% block extra_css %}<link rel="stylesheet" href="{% static 'contas/css/entrar.css' %}">{% endblock %}
{% block body_class %}ritmo-publico entrada-pagina{% endblock %}
{% block content %}
{% comment %}
Login da área do almoxarifado: card centralizado no fundo off-white, sem barra lateral. A
recusa é genérica (`FormularioEntrada`) e não diz se a matrícula existe.
{% endcomment %}
<main class="entrada" id="main">
  <a class="marca" href="{% url 'pedidos:inicio' %}">{% include "interface/_icone.html" with nome="caixa" %}<span>Central Almoxarifado</span></a>
  <div class="cartao entrada-cartao">
    <div class="pilha">
      <p class="rotulo-secao">Acesso restrito</p>
      <h1>Área do almoxarifado</h1>
    </div>
    {% if form.non_field_errors %}
    <div class="aviso aviso-erro" id="login-erro" role="alert">
      {% include "interface/_icone.html" with nome="alerta" %}
      <div>{% for error in form.non_field_errors %}<p>{{ error }}</p>{% endfor %}</div>
    </div>
    {% endif %}
    <form method="post" class="pilha">
      {% csrf_token %}
      {% if next %}<input type="hidden" name="next" value="{{ next }}">{% endif %}
      {% for field in form %}
      <div class="campo{% if field.errors %} campo-com-erro{% endif %}">
        <label class="campo-rotulo" for="{{ field.id_for_label }}">{{ field.label }}</label>
        {{ field }}
        {% if field.errors %}<p class="campo-erro" id="{{ field.auto_id }}_error">{{ field.errors.0 }}</p>{% endif %}
      </div>
      {% endfor %}
      <button type="submit" class="botao botao-primario botao-bloco">Entrar</button>
    </form>
    <p class="texto-suave texto-pequeno">Esqueceu a senha? Procure o responsável pelo almoxarifado.</p>
  </div>
</main>
{% endblock %}
```

`entrar.css`:

```css
/* Login: card centralizado no fundo off-white. */
.entrada-pagina { background: var(--superficie); }
.entrada { min-height: 100vh; display: grid; place-content: center; justify-items: center; gap: var(--esp-3); padding: var(--esp-6) var(--esp-2); }
.entrada-cartao { width: min(400px, 100%); display: grid; gap: var(--esp-3); box-shadow: var(--sombra-elevada); }
.entrada-cartao h1 { font-size: 28px; }
.entrada input { width: 100%; min-height: var(--altura-controle); padding: 10px 14px; border: 1px solid var(--borda); border-radius: var(--raio-controle); background: var(--fundo); transition: border-color var(--transicao), box-shadow var(--transicao); }
.entrada input:focus { outline: none; border-color: var(--destaque); box-shadow: 0 0 0 3px var(--destaque-superficie); }
.entrada .botao-bloco { width: 100%; }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_acesso.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Login no estilo Clean`

---

### Task 5: Páginas públicas e componentes de materiais

**Files:**
- Modify:
  - templates: `pedidos/templates/pedidos/inicio.html`, `formulario.html`, `_formulario.html`,
    `_materiais.html`, `_resultados.html`, `_carrinho.html`, `_sucesso.html`;
  - estáticos: `pedidos/static/pedidos/css/pedidos.css`, `pedidos/static/pedidos/js/pedidos.js`;
  - testes: `tests/test_formularios_publicos.py`, `tests/test_carrinho.py`.

**Interfaces:**
- Consumes: vocabulário e layouts (Tarefas 1 a 3).
- Produces: `_materiais.html`, `_resultados.html` e `_carrinho.html` no vocabulário novo, que
  a saída avulsa (Tarefa 7) reutiliza; `pedidos.css` com o que é próprio de pedidos
  (sucesso, recibo nas Tarefas 6 e 7).

- [ ] **Step 1: Testes que falham** (`tests/test_formularios_publicos.py`)

```python
def test_inicio_no_estilo_clean(client):
    r = client.get(reverse("pedidos:inicio"))
    assert r.text.count('class="cartao cartao-opcao"') == 2
    assert '<p class="rotulo-secao">Almoxarifado SAEP</p>' in r.text


def test_formulario_em_tres_passos(client):
    r = client.get(reverse("pedidos:formulario", args=["limpeza"]))
    for numero, titulo in (("01", "Quem pede"), ("02", "Materiais"), ("03", "Entrega")):
        assert f'<span class="passo-numero" aria-hidden="true">{numero}</span>' in r.text
        assert f"<h2>{titulo}</h2>" in r.text
    assert 'class="campo-busca"' in r.text and 'class="lista-materiais"' in r.text
    assert 'data-quantidade="mais"' in r.text and 'data-quantidade="menos"' in r.text
    assert "<details" not in r.text
    assert r.text.index("data-erro-envio") < r.text.index('class="passo"')


def test_sucesso_no_estilo_clean(client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        r = postar(client, "limpeza", token(), itens=LIMPEZA_ITENS)
    assert 'class="cartao sucesso-pedido"' in r.text
    assert '<p class="sucesso-numero mono">P-000001</p>' in r.text
```

Em `tests/test_carrinho.py`, `test_endpoint_do_carrinho` continua igual: os campos
escondidos não mudam. Acrescente:

```python
@pytest.mark.django_db
def test_carrinho_no_vocabulario_novo(client):
    montar_cenario()
    r = client.post(reverse("pedidos:carrinho", args=["ab"]), {"adicionar": "016.005.010", "qtd-016.005.010": "3"})
    assert 'class="carrinho"' in r.text and 'class="carrinho-linha"' in r.text
    assert "Seu pedido (1)" in r.text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_formularios_publicos.py tests/test_carrinho.py -q`
Expected: FAIL.

- [ ] **Step 3: Templates** (escreva todos com Write; mantenha toda a lógica Django, os ids e
  os atributos HTMX de hoje)

`inicio.html`:

```django
{% extends "interface/base_publico.html" %}
{% load static %}
{% block title %}Pedir materiais — Central Almoxarifado{% endblock %}
{% block extra_css %}<link rel="stylesheet" href="{% static 'pedidos/css/pedidos.css' %}">{% endblock %}
{% block rotulo %}Almoxarifado SAEP{% endblock %}
{% block heading %}Pedir materiais ao almoxarifado{% endblock %}
{% block sub %}Escolha o tipo de material. Cada tipo tem seu próprio formulário.{% endblock %}
{% block page %}
<div class="opcoes-formulario">
  <a class="cartao cartao-opcao" href="{% url 'pedidos:formulario' 'limpeza' %}">
    {% include "interface/_icone.html" with nome="caixa" %}
    <span class="rotulo-secao">Formulário 1</span>
    <h2>Limpeza, copa/cozinha e escritório</h2>
    <span class="texto-secundario">Produtos de limpeza, itens de copa e cozinha e material de escritório.</span>
    <span class="cartao-opcao-seta">{% include "interface/_icone.html" with nome="seta-direita" %}</span>
  </a>
  <a class="cartao cartao-opcao" href="{% url 'pedidos:formulario' 'ab' %}">
    {% include "interface/_icone.html" with nome="catalogo" %}
    <span class="rotulo-secao">Formulário 2</span>
    <h2>Materiais AB</h2>
    <span class="texto-secundario">Demais materiais do almoxarifado, com busca por grupo, subgrupo e estoque.</span>
    <span class="cartao-opcao-seta">{% include "interface/_icone.html" with nome="seta-direita" %}</span>
  </a>
</div>
<p class="texto-suave texto-pequeno">Enviar um pedido não é a saída do material: o almoxarifado confere, separa e confirma o atendimento depois.</p>
{% endblock %}
```

`formulario.html`:

```django
{% extends "interface/base_publico.html" %}
{% load static %}
{% block title %}{{ fluxo.titulo }} — Central Almoxarifado{% endblock %}
{% block extra_css %}<link rel="stylesheet" href="{% static 'pedidos/css/pedidos.css' %}">{% endblock %}
{% block extra_head %}<script src="{% static 'pedidos/js/pedidos.js' %}" defer></script>{% endblock %}
{% block rotulo %}{{ fluxo.formulario }}{% endblock %}
{% block heading %}{{ fluxo.titulo }}{% endblock %}
{% block sub %}<a href="{% url 'pedidos:inicio' %}" class="link-voltar">{% include "interface/_icone.html" with nome="seta-esquerda" %}Trocar tipo de material</a>{% endblock %}
{% block page %}
<div id="formulario">{% if sucesso %}{% include "pedidos/_sucesso.html" %}{% else %}{% include "pedidos/_formulario.html" %}{% endif %}</div>
{% endblock %}
```

`_formulario.html` (o bloco de indisponível usa `aviso aviso-atencao` com o ícone `alerta` e
os textos de hoje):

```django
{% if indisponivel %}
<div class="aviso aviso-atencao" role="alert">{% include "interface/_icone.html" with nome="alerta" %}<p>{% if fluxo.nome == "ab" %}Este formulário está indisponível no momento (estoque ou catálogo não carregou). Avise o almoxarifado.{% else %}Este formulário está indisponível no momento. Avise o almoxarifado.{% endif %}</p></div>
{% else %}
<form method="post" action="{% url 'pedidos:formulario' fluxo.nome %}" class="pilha-larga formulario-pedido"
      hx-post="{% url 'pedidos:formulario' fluxo.nome %}" hx-target="#formulario" data-formulario-pedido>
  {% csrf_token %}
  <input type="hidden" name="token" value="{{ envio.token }}">
  <div class="visually-hidden" aria-hidden="true">
    <label for="confirmacao-extra">Não preencha este campo</label>
    <input id="confirmacao-extra" type="text" name="confirmacao_extra" tabindex="-1" autocomplete="off">
  </div>
  <div class="aviso" data-erro-envio role="alert"></div>
  {% if mensagem %}
  <div class="aviso aviso-erro" role="alert">{% include "interface/_icone.html" with nome="alerta" %}<div><p>{{ mensagem }}</p>{% if erros %}<ul>{% for erro in erros %}<li>{{ erro.texto }}</li>{% endfor %}</ul>{% endif %}</div></div>
  {% endif %}

  <section class="passo">
    <span class="passo-numero" aria-hidden="true">01</span>
    <div class="passo-cabecalho"><h2>Quem pede</h2></div>
    <div class="passo-corpo">
      <div class="campo">
        <label class="campo-rotulo" for="solicitante">Nome completo *</label>
        <input id="solicitante" class="campo-entrada" type="text" name="solicitante" maxlength="200" autocomplete="name" value="{{ campos.solicitante }}">
      </div>
    </div>
  </section>

  <section class="passo">
    <span class="passo-numero" aria-hidden="true">02</span>
    <div class="passo-cabecalho"><h2>Materiais</h2><p class="texto-secundario">Busque, escolha a quantidade e adicione ao pedido.</p></div>
    <div class="passo-corpo">{% include "pedidos/_materiais.html" %}</div>
  </section>

  <section class="passo">
    <span class="passo-numero" aria-hidden="true">03</span>
    <div class="passo-cabecalho"><h2>Entrega</h2></div>
    <div class="passo-corpo">
      <div class="campo">
        <label class="campo-rotulo" for="destino">Destino dos materiais *</label>
        {% if fluxo.nome == "limpeza" %}
        <input id="destino" class="campo-entrada" type="text" name="destino" maxlength="200" list="destinos" autocomplete="off" value="{{ campos.destino }}" aria-describedby="destino-dica">
        <datalist id="destinos">{% for d in destinos %}<option value="{{ d }}">{% endfor %}</datalist>
        <p id="destino-dica" class="campo-dica">Digite para buscar ou escrever outro destino.</p>
        {% else %}
        <input id="destino" class="campo-entrada" type="text" name="destino" maxlength="200" value="{{ campos.destino }}">
        {% endif %}
      </div>
      <div class="campo">
        <label class="campo-rotulo" for="obs">Observação</label>
        <textarea id="obs" class="campo-entrada" name="obs" maxlength="200">{{ campos.obs }}</textarea>
      </div>
    </div>
  </section>

  <div class="acoes">
    <button type="submit" class="botao botao-primario botao-bloco">{% if divergente %}Já conferi com o almoxarifado — enviar como novo pedido{% else %}Enviar pedido{% endif %}</button>
  </div>
</form>
{% endif %}
```

`_materiais.html` (sem `<details>`; os atributos HTMX são os de hoje):

```django
{% comment %}
Busca de materiais e carrinho (dentro do <form>). Os botões "Adicionar" e "Remover" mandam o
formulário inteiro (o HTMX inclui os valores do <form> em requisição não GET) e só o trecho do
carrinho volta. O carrinho vive nos campos escondidos de `_carrinho.html`.
{% endcomment %}
<div id="busca-materiais" class="busca-materiais">
  <div class="campo">
    <label class="campo-rotulo" for="busca-q">Buscar material pelo nome ou código</label>
    <div class="campo-busca">
      {% include "interface/_icone.html" with nome="busca" %}
      <input id="busca-q" class="campo-entrada" type="search" name="q" autocomplete="off" data-busca
             placeholder="Ex.: luva, fita veda rosca, 016.005.010"
             hx-get="{{ url_materiais }}" hx-trigger="input changed delay:300ms, search"
             hx-target="#resultados" hx-include="#busca-materiais">
    </div>
  </div>
  {% if filtros %}
  <div class="campo">
    <label class="campo-rotulo" for="busca-filtro">{% if fluxo.nome == "ab" %}Grupo e subgrupo{% else %}Categoria{% endif %}</label>
    <select id="busca-filtro" class="campo-entrada" name="filtro" hx-get="{{ url_materiais }}"
            hx-trigger="change" hx-target="#resultados" hx-include="#busca-materiais">
      {% if fluxo.nome == "ab" %}
      <option value="">Todos os grupos</option>
      {% for grupo, subgrupos in filtros %}
      <optgroup label="{{ grupo }}">
        <option value="{{ grupo }}">Todo o grupo {{ grupo }}</option>
        {% for sub in subgrupos %}<option value="{{ grupo }} › {{ sub }}">{{ grupo }} › {{ sub }}</option>{% endfor %}
      </optgroup>
      {% endfor %}
      {% else %}
      <option value="">Todas as categorias</option>
      {% for categoria in filtros %}<option value="{{ categoria }}">{{ categoria }}</option>{% endfor %}
      {% endif %}
    </select>
  </div>
  {% endif %}
</div>
<div id="resultados" aria-live="polite">{% include "pedidos/_resultados.html" %}</div>
<div id="carrinho">{% include "pedidos/_carrinho.html" %}</div>
```

`_resultados.html`:

```django
{% load interface_extras %}
<p class="texto-secundario texto-pequeno">{% if not total %}Nenhum material encontrado.{% elif total > resultados|length %}Mostrando {{ resultados|length }} de {{ total|separador_milhar }} — refine a busca ou use os filtros.{% elif total == 1 %}1 material{% else %}{{ total|separador_milhar }} materiais{% endif %}</p>
{% if resultados %}
<ul class="lista-materiais">
  {% for r in resultados %}
  <li class="material{% if r.motivo %} material-bloqueado{% endif %}">
    <div class="material-dados">
      <strong>{{ r.item.nome }}</strong>
      <span class="texto-secundario texto-pequeno"><span class="mono">{{ r.item.codigo }}</span> · {{ r.info }}{% if r.classe %} · {{ r.classe }}{% endif %}</span>
      {% if r.motivo %}<span><span class="selo selo-aviso">{{ r.motivo }}</span></span>{% endif %}
    </div>
    {% if not r.motivo %}
    <div class="material-acao">
      <label class="visually-hidden" for="qtd-{{ forloop.counter }}">Quantidade{% if fluxo.inteiro %} (inteira){% endif %} de {{ r.item.nome }}{% if r.item.unidade %} ({{ r.item.unidade }}){% endif %}</label>
      <div class="quantidade">
        <button type="button" class="botao botao-icone" data-quantidade="menos" aria-label="Diminuir">{% include "interface/_icone.html" with nome="menos" %}</button>
        <input id="qtd-{{ forloop.counter }}" class="quantidade-campo campo-qtd" type="text" name="qtd-{{ r.item.codigo }}" value="1" inputmode="{% if fluxo.inteiro %}numeric{% else %}decimal{% endif %}">
        <button type="button" class="botao botao-icone" data-quantidade="mais" aria-label="Aumentar">{% include "interface/_icone.html" with nome="mais" %}</button>
      </div>
      <button type="button" class="botao botao-secundario" hx-post="{{ url_carrinho }}" hx-target="#carrinho"
              hx-vals='{"adicionar": "{{ r.item.codigo|escapejs }}"}' aria-label="Adicionar {{ r.item.nome }}">Adicionar</button>
    </div>
    {% endif %}
  </li>
  {% endfor %}
</ul>
{% endif %}
```

`_carrinho.html` (o rótulo "Itens (N)" vira "Seu pedido (N)"):

```django
<div class="carrinho">
  <h3>Seu pedido ({{ carrinho.linhas|length }})</h3>
  {% if carrinho.erro %}<div class="aviso aviso-erro" role="alert">{% include "interface/_icone.html" with nome="alerta" %}<p>{{ carrinho.erro }}</p></div>{% endif %}
  {% if carrinho.aviso %}<div class="aviso aviso-info" role="status"><p>{{ carrinho.aviso }}</p></div>{% endif %}
  {% if carrinho.linhas %}
  <ul>
    {% for linha in carrinho.linhas %}
    <li class="carrinho-linha{% if linha.codigo in codigos_erro %} carrinho-linha-erro{% endif %}">
      <input type="hidden" name="item_codigo" value="{{ linha.codigo }}">
      <input type="hidden" name="item_qtd" value="{{ linha.texto }}">
      <span class="material-dados"><strong>{{ linha.item.nome|default:linha.codigo }}</strong><span class="mono texto-secundario texto-pequeno">{{ linha.codigo }}</span>{% if linha.codigo in codigos_erro %}<span><span class="selo selo-erro">Corrigir</span></span>{% endif %}</span>
      <span class="linha"><strong class="carrinho-qtd">{{ linha.texto }}{% if linha.item.unidade %} {{ linha.item.unidade }}{% endif %}</strong>
      <button type="button" class="botao botao-texto botao-perigo" hx-post="{{ url_carrinho }}" hx-target="#carrinho"
              hx-vals='{"remover": "{{ linha.codigo|escapejs }}"}' aria-label="Remover {{ linha.item.nome|default:linha.codigo }}">{% include "interface/_icone.html" with nome="lixeira" %}Remover</button></span>
    </li>
    {% endfor %}
  </ul>
  {% else %}
  <p class="texto-secundario">Nenhum material adicionado ainda.</p>
  {% endif %}
</div>
```

`_sucesso.html`:

```django
<section class="cartao sucesso-pedido">
  <span class="sucesso-icone">{% include "interface/_icone.html" with nome="check" %}</span>
  <p class="rotulo-secao">{% if resposta.reenvio %}Pedido já estava registrado{% else %}Pedido registrado{% endif %}</p>
  <p class="sucesso-numero mono">{{ resposta.numero }}</p>
  <p>{% if n_itens == 1 %}1 material registrado{% else %}{{ n_itens }} materiais registrados{% endif %} para {{ resposta.pedido.solicitante }}.</p>
  {% if resposta.reenvio %}<p class="texto-secundario">Reenvio confirmado: nenhum aviso novo foi enviado.</p>
  {% elif resposta.telegram == "falhou" %}<p class="texto-secundario">O aviso ao almoxarifado pelo Telegram falhou, mas o pedido está gravado.</p>{% endif %}
  <div class="aviso aviso-info"><p>Guarde o número. O almoxarifado vai conferir e separar os materiais; a saída só é registrada quando o atendimento for confirmado.</p></div>
  <div class="acoes">
    <a class="botao botao-primario" href="{% url 'pedidos:formulario' fluxo.nome %}">Fazer outro pedido</a>
    <a class="botao botao-secundario" href="{% url 'pedidos:inicio' %}">Voltar ao início</a>
  </div>
</section>
```

Os testes atuais procuram "Pedido registrado" e "Pedido já estava registrado". O texto
continua no HTML, em versalete só pelo CSS.

- [ ] **Step 4: `pedidos.css` (substitui o arquivo inteiro) e `pedidos.js`**

```css
/* Pedidos: o que é próprio desta app. Componentes comuns ficam em interface/css. */

.opcoes-formulario { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--esp-3); }
.link-voltar { display: inline-flex; align-items: center; gap: 6px; color: var(--texto-secundario); }
.link-voltar:hover { color: var(--texto); }
.busca-materiais { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: var(--esp-2); align-items: end; }
@media (max-width: 640px) { .busca-materiais { grid-template-columns: 1fr; } }
.carrinho-qtd { white-space: nowrap; font-weight: 500; }

.sucesso-pedido { display: grid; justify-items: start; gap: var(--esp-2); animation: subir 0.4s ease both; }
.sucesso-icone { display: inline-flex; width: 48px; height: 48px; align-items: center; justify-content: center; border-radius: 50%; background: var(--ok-superficie); color: var(--ok-texto); }
.sucesso-icone .icone { width: 24px; height: 24px; }
.sucesso-numero { font-size: 40px; font-weight: 500; line-height: 1.1; letter-spacing: -0.01em; color: var(--texto); }
```

Em `pedidos.js`, acrescente o − e o +, delegados em `document`, dentro da mesma IIFE:

```js
  // − e + da quantidade nos resultados da busca: só no navegador; o servidor revalida.
  document.addEventListener("click", function (e) {
    var botao = e.target.closest && e.target.closest("[data-quantidade]");
    if (!botao) return;
    var campo = botao.parentNode.querySelector(".quantidade-campo");
    if (!campo) return;
    var inteiro = parseInt((campo.value || "").split(",")[0], 10);
    if (isNaN(inteiro)) inteiro = 1;
    var passo = botao.getAttribute("data-quantidade") === "mais" ? 1 : -1;
    var resto = campo.value.indexOf(",") >= 0 ? campo.value.slice(campo.value.indexOf(",")) : "";
    campo.value = String(Math.max(1, inteiro + passo)) + resto;
  });
```

O seletor de Enter (`.campo-qtd`) continua valendo, porque o campo mantém essa classe. O
"Adicionar" da mesma linha passa a ser achado por `linha.querySelector("[hx-post]")`, porque
agora há outros botões na linha. Ajuste no handler de `keydown`.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_formularios_publicos.py tests/test_carrinho.py -q`
Expected: PASS.

- [ ] **Step 6: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Páginas públicas no estilo Clean: início, formulário em três passos, carrinho e sucesso`

---

### Task 6: Painel e catálogo

**Files:**
- Modify:
  - templates: `pedidos/templates/pedidos/painel.html`, `_painel_lista.html`;
  - código: `pedidos/templatetags/pedidos_extras.py`, `pedidos/consultas.py` (widgets do
    `FiltrosPainel`);
  - catálogo: `catalogo/templates/catalogo/situacao.html`, `_situacao.html`, `_saude.html`,
    `catalogo/static/catalogo/css/catalogo.css`;
  - testes: `tests/test_painel.py`, `tests/test_pagina_catalogo.py`.

**Interfaces:**
- Consumes: Tarefas 1 a 3.
- Produces: `badge_situacao`/`badge_scpi` passam a devolver `selo-*`; `_saude.html` usa
  `selo-*`.

- [ ] **Step 1: Testes que falham**

Em `tests/test_painel.py`:

```python
def test_painel_no_estilo_clean(client, logado):
    criar_pedido()
    r = client.get(reverse("pedidos:painel"))
    assert 'class="filtros"' in r.text and 'class="campo-busca"' in r.text
    assert 'class="selo selo-info"' in r.text
    assert re.search(r'<div class="tabela-rolagem">\s*<table class="tabela">', r.text)
    assert 'class="campo-entrada"' in r.text  # widgets do FiltrosPainel
```

(acrescente `import re` no topo do arquivo, se faltar).

Em `tests/test_pagina_catalogo.py`:

```python
def test_catalogo_no_estilo_clean(client, usuario_logado):
    r = client.get(reverse("catalogo:situacao"))
    assert re.search(r'<div class="tabela-rolagem">\s*<table class="tabela">', r.text)
    assert 'class="botao botao-primario"' in r.text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_painel.py tests/test_pagina_catalogo.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

- **`pedidos_extras.py`:**
  - `_SITUACAO`: aguardando `selo-info`, atendido `selo-ok`, parcial `selo-aviso`, avulsa
    `selo-neutro`;
  - `_SCPI`: sem `selo-neutro`, aguardando `selo-info`, parcial `selo-aviso`, lancado
    `selo-ok`, atencao `selo-erro`;
  - o padrão vira `selo-neutro`.
- **`consultas.py`:** em `FiltrosPainel`, todo campo ganha `widget=...(attrs={"class":
  "campo-entrada"})`. O `q` ganha também `type="search"` e
  `placeholder="Nº, solicitante ou recebedor"`. `de` e `ate` mantêm `type="date"`.
- **`painel.html`:**
  - `{% block rotulo %}Pedidos{% endblock %}`, heading "Painel" e o sub atual;
  - `tools`:
    - `<a class="botao botao-primario">` com o ícone `mais` e "Saída avulsa";
    - recibos pendentes: `<a class="botao botao-secundario">` com o ícone `impressora` e
      "Imprimir recibos pendentes (N)", ou `<span class="texto-secundario texto-pequeno">`
      "Nenhum recibo pendente";
  - o conteúdo em `<div class="pilha-larga">` com:
    1. **Saúde do catálogo:** `<section class="cartao saude-painel">` com
       `<h2 class="cartao-titulo">Saúde do catálogo</h2>`. Com problemas, inclui
       `catalogo/_saude.html`; sem problemas, `<p class="linha texto-secundario">` com o ícone
       `check` e "Catálogo em dia.". Fecha com o link "Ver catálogo".
    2. **Filtros:** `<form class="cartao filtros" method="get" …mesmos atributos HTMX de
       hoje…>`:
       - um `filtros-campo` para a busca, com `<label class="campo-rotulo">`,
         `<div class="campo-busca">`, o ícone `busca` e `{{ filtros.q }}`;
       - um `filtros-campo` por campo restante, com `<label class="campo-rotulo">` e
         `{{ campo }}`;
       - `<div class="filtros-acoes">` com `<button class="botao botao-secundario">Filtrar`
         e o link "Limpar filtros".
    3. `<div id="lista-pedidos" class="cartao">` com o include da lista.
- **`_painel_lista.html`:**
  - `table-wrapper` vira `tabela-rolagem` e `table` vira `tabela`;
  - a origem vira `<span class="selo selo-neutro">`; as situações usam `selo` e os filtros;
  - o Nº continua `<a href=...><span class="mono numero-pedido">`;
  - o SCPI vira `<span class="selo …">SCPI: …</span>`;
  - o vazio vira `<div class="vazio"><p class="vazio-titulo">…</p></div>`;
  - a paginação continua como include.
- **`_saude.html`:** `badge badge-danger|warning|success` vira `selo selo-erro|selo-aviso|selo-ok`
  e a lista fica `<ul class="saude">`.
- **`situacao.html` e `_situacao.html`:** aplique o mapa de classes antigas. O botão
  "Atualizar agora" vira `botao botao-primario`; a tabela de importações vai para
  `tabela-rolagem`/`tabela`; os selos de situação seguem o mapa; o card de saúde vira
  `cartao`. Mantenha o id `situacao-catalogo` e os atributos HTMX.
- **`catalogo.css` (substitui):**

```css
/* Catálogo: lista da saúde (também usada no painel) e a faixa do botão. */
.saude { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.saude li { display: flex; align-items: flex-start; gap: var(--esp-1); }
.saude .selo { flex: none; margin-top: 2px; }
.atualizar-catalogo { display: flex; flex-wrap: wrap; align-items: center; gap: var(--esp-2); }
```

O painel já carrega `catalogo/css/catalogo.css` pelo `extra_css`; troque o bloco
`extra_head` antigo por `extra_css` onde a página carregar só CSS.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_painel.py tests/test_pagina_catalogo.py tests/test_saude.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Painel e catálogo no estilo Clean`

---

### Task 7: Detalhe, atendimento, saída avulsa e recibos

**Files:**
- Modify:
  - templates: `pedidos/templates/pedidos/detalhe.html`, `_recibo.html`, `_campos_saida.html`,
    `avulsa.html`, `recibos.html`;
  - estáticos: `pedidos/static/pedidos/css/pedidos.css` (acréscimos);
  - testes: `tests/test_atendimento.py`, `tests/test_saida_avulsa.py`, `tests/test_recibos.py`.

**Interfaces:**
- Consumes: `_materiais.html`, `_resultados.html` e `_carrinho.html` (Tarefa 5); os selos
  (Tarefa 6).

- [ ] **Step 1: Testes que falham**

```python
# tests/test_atendimento.py
def test_detalhe_no_estilo_clean(client, pedido, logado):
    r = client.get(reverse("pedidos:detalhe", args=[pedido.numero]))
    assert 'class="cartao recibo"' in r.text and '<dl class="dados">' in r.text
    assert 'class="grade-2"' in r.text and 'class="campo-check"' in r.text
    assert re.search(r'<div class="tabela-rolagem">\s*<table class="tabela', r.text)


# tests/test_saida_avulsa.py
def test_avulsa_em_dois_passos(client, usuario):
    client.force_login(usuario)
    r = client.get(reverse("pedidos:avulsa"))
    for numero, titulo in (("01", "Dados da saída"), ("02", "Materiais")):
        assert f'<span class="passo-numero" aria-hidden="true">{numero}</span>' in r.text
        assert f"<h2>{titulo}</h2>" in r.text


# tests/test_recibos.py
def test_recibos_no_estilo_clean(client, logado):
    criar_pedido(atendido=True)
    r = client.get(reverse("pedidos:recibos_pendentes"))
    assert '<article class="folha-recibo cartao' in r.text
    assert 'class="botao botao-primario" data-imprimir' in r.text
```

(acrescente `import re` onde faltar). Os testes de recibos que procuram
`'<article class="folha-recibo'` continuam valendo.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_atendimento.py tests/test_saida_avulsa.py tests/test_recibos.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar** (mantenha toda a lógica Django, os textos e os nomes de campo de
  hoje)

**`_recibo.html`:**
- O contêiner vira `<div class="cartao recibo">`. No detalhe ele entra solto; nos recibos,
  dentro do `<article>`.
- Cabeçalho: `<p class="rotulo-secao">Almoxarifado SAEP — Recibo de …</p>`,
  `<h2 class="recibo-numero">Nº <span class="mono">…</span></h2>` e as linhas `.so-tela` em
  `texto-suave texto-pequeno`.
- Quadros: `<div class="recibo-quadros so-tela">` com dois
  `<div class="cartao cartao-sutil recibo-quadro">`, cada um com
  `<p class="rotulo-secao">Situação do pedido</p>` (ou "Integração com o SCPI"), o `selo` e a
  descrição em `texto-secundario`.
- Dados: `<dl class="dados">`, com as mesmas regras de `so-tela` para campo vazio.
- Materiais: `<h3>Materiais (N)</h3>` e
  `<div class="tabela-rolagem"><table class="tabela recibo-itens">`.
- Saída registrada: `<div class="recibo-saida"><h3>Saída registrada</h3><dl class="dados">…`.
- Assinaturas: `<div class="assinaturas">` com os dois `<p>`.

**`detalhe.html`:**
- `rotulo`: o `get_origem_display`;
- heading: "Pedido"/"Saída avulsa" e o Nº em mono;
- `tools`:
  - "Imprimir recibo" (`botao botao-primario`, ícone `impressora`);
  - "Registrar outra saída" (`botao botao-secundario`, ícone `mais`);
  - "Voltar ao painel" (`botao botao-texto`, ícone `seta-esquerda`);
- conteúdo em `<div class="pilha-larga">`, com:
  1. o `<p class="texto-secundario texto-pequeno nao-imprimir">` de quem registrou ou
     atendeu;
  2. o include do recibo;
  3. quando cabe atendimento, `<section class="cartao nao-imprimir atendimento">` com
     `<h2 class="cartao-titulo">Confirmar atendimento</h2>` e o `<form class="pilha-larga">`:
     - `_campos_saida.html`;
     - o bloco "Quantidade entregue por material":
       `<div class="pilha"><div><p class="campo-rotulo">…</p><p class="campo-dica">…</p></div>`;
       cada item é uma `<div class="entregue">` com o `<label>` (material e "(pedido: …)" em
       `texto-secundario`) e `<input class="campo-entrada entregue-campo campo-qtd">`;
     - o `aviso aviso-info` sobre o lote;
     - erros em `aviso aviso-erro`;
     - `<div class="acoes">` com o botão primário.

**`_campos_saida.html`:**
- `<div class="grade-2">`, com cada campo num `<div class="campo">`:
  - `campo-rotulo` e `campo-entrada`;
  - o botão "Quem recebe é o solicitante (…)" vira `botao botao-texto` com
    `data-preencher-recebedor`, logo abaixo do campo recebedor;
- Observações em `<div class="campo">` de largura total (fora da grade);
- a caixa vira `<label class="campo-check"><input type="checkbox" name="nao_lancar"…>`, com
  `<span><strong>Não lançar no SCPI</strong><span class="campo-dica">Use para material fora
  de estoque.</span></span>`.

**`avulsa.html`:**
- `rotulo`: "Origem: avulsa";
- heading "Saída avulsa" e o sub atual;
- o `<form class="pilha-larga">` com dois `<section class="passo cartao">`:
  - `01` "Dados da saída", com `_campos_saida.html`;
  - `02` "Materiais", com `_materiais.html` e a dica "Decimais com vírgula (ex.: 1,5).";
- erros e `acoes` com o botão primário;
- indisponível em `aviso aviso-atencao` com o ícone `alerta`.

**`recibos.html`:**
- `tools` vazio;
- a barra vira `<div class="cartao barra-recibos nao-imprimir">` com:
  - `<button type="button" class="botao botao-primario" data-imprimir>` com o ícone
    `impressora` e "Imprimir";
  - o formulário de marcar, com `botao botao-secundario`;
- cada recibo vai em `<article class="folha-recibo cartao">`, com o include do recibo; o
  `cartao recibo` interno não leva borda nem sombra dentro do article (CSS abaixo);
- o vazio em `vazio`/`vazio-titulo`.

**Acrescente a `pedidos.css`:**

```css
.recibo { display: grid; gap: var(--esp-3); }
.folha-recibo .recibo { padding: 0; border: 0; box-shadow: none; }
.recibo-numero { font-size: 28px; }
.recibo-numero .mono { font-size: 1em; font-weight: 500; }
.recibo-quadros { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--esp-2); }
.recibo-quadro { display: grid; gap: var(--esp-1); justify-items: start; padding: var(--esp-2); }
.recibo-saida { display: grid; gap: var(--esp-2); padding-top: var(--esp-3); border-top: 1px solid var(--borda); }
.assinaturas { display: grid; gap: var(--esp-6); margin-top: var(--esp-4); }
.entregue { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--esp-1) var(--esp-2); padding: 10px 0; border-bottom: 1px solid var(--borda); }
.entregue label { flex: 1 1 240px; }
.entregue-campo { width: 120px; text-align: right; }
.barra-recibos { display: flex; flex-wrap: wrap; align-items: center; gap: var(--esp-2); }
.folha-recibo + .folha-recibo { margin-top: var(--esp-3); }
@media print {
  .folha-recibo { break-after: page; border: 0; box-shadow: none; padding: 0; }
  .folha-recibo:last-child { break-after: auto; }
  .recibo .selo { border: 1px solid #999999; background: none; color: #000000; }
}
```

Apague de `pedidos.css` as regras antigas de recibo, entregue, campos de saída e impressão que
a Tarefa 5 ainda não tenha removido.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_atendimento.py tests/test_saida_avulsa.py tests/test_recibos.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte e commit**

Run: `uv run pytest -q`
Expected: PASS.

Commit — `Detalhe, atendimento, saída avulsa e recibos no estilo Clean`

---

### Task 8: Varredura, documentação e conferência visual

**Files:**
- Modify: `docs/DESIGN.md` (reescrito), `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`
  (seção 2 e "Decisões já tomadas"), `CLAUDE.md` (parágrafo de `interface`),
  `THIRD-PARTY-NOTICES.md`, `tests/test_clean.py`

- [ ] **Step 1: Teste de varredura que falha** (`tests/test_clean.py`)

```python
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANTIGAS = re.compile(
    r'class="[^"]*\b(btn|card|page-section|field|field-label|field-hint|error-box|alert|badge'
    r'|text-muted|table-wrapper|empty-state|filter-bar|form-actions|side|meta-env)\b'
)


def test_nenhum_template_usa_classe_da_fundacao_antiga():
    sujos = []
    for caminho in RAIZ.glob("*/templates/**/*.html"):
        if "admin" in caminho.parts:
            continue
        if ANTIGAS.search(caminho.read_text(encoding="utf-8")):
            sujos.append(str(caminho.relative_to(RAIZ)))
    assert sujos == []


def test_nenhum_emoji_nos_templates():
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    for caminho in RAIZ.glob("*/templates/**/*.html"):
        assert not emoji.search(caminho.read_text(encoding="utf-8")), caminho
```

- [ ] **Step 2: Rodar**

Run: `uv run pytest tests/test_clean.py -q`
Expected: FAIL se sobrou alguma classe antiga; PASS se as Tarefas 3 a 7 já limparam tudo.
Corrija o que aparecer até passar.

- [ ] **Step 3: Documentação**

- **`docs/DESIGN.md`**, reescrito em pt-BR, até umas 150 linhas:
  - origem: skill `clean-design` e a spec da interface;
  - os tokens com os valores, os ritmos e as fontes;
  - a tabela do vocabulário de classes deste plano;
  - ícones, movimento e as regras do projeto que continuam;
  - impressão;
  - como criar uma tela nova (carregar a skill e usar só o vocabulário).
- **Spec principal:**
  - na tabela "Decisões já tomadas", a linha "Interface" passa a dizer: "Design system Clean
    (`.claude/skills/clean-design/`, spec `2026-10-10-interface-clean-design.md`): só tema
    claro, fontes locais, destaque azul `#2563EB`.";
  - na seção 2 ("Interface"), o parágrafo que cita o WMS-Almoxarifado e o tema
    claro/escuro é reescrito do mesmo jeito;
  - a frase sobre o `THIRD-PARTY-NOTICES.md` (django-observatory) passa a citar as fontes OFL
    e os ícones Lucide.
- **`CLAUDE.md`:** o parágrafo de `interface` passa a descrever:
  - `clean.css`, `componentes.css` e `layouts.css`, `_icone.html` e as fontes locais;
  - só tema claro, e o `shell.js` só com o menu móvel;
  - os dois ritmos (`ritmo-publico`/`ritmo-almox`);
  - a skill `.claude/skills/clean-design/` e o `docs/DESIGN.md`;
  - que a regra de scripts no `<head>` com `defer` continua.
- **`THIRD-PARTY-NOTICES.md`:**
  - o aviso MIT do WMS-Almoxarifado/django-observatory fica só para o que ainda é copiado:
    `_paginacao.html` e as tags `querystring_pagina`, `intervalo_paginas`,
    `separador_milhar` e `quantidade`;
  - os itens do WMS que não existem mais saem (`tokens.css`, `base.css`, `components.css`,
    `shell.js` com tema).

- [ ] **Step 4: Suíte, estáticos e lint**

Run: `uv run python manage.py collectstatic --noinput && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run python manage.py makemigrations --check --dry-run`
Expected: tudo verde e "No changes detected".

- [ ] **Step 5: Conferência visual com o usuário**

Suba o servidor (`uv run python manage.py runserver 8000`, em segundo plano) e peça ao
usuário que confira, a 375px, 768px e 1280px:
1. Início: dois cartões, hover com a seta andando.
2. Formulário de limpeza:
   - os três passos;
   - buscar "cafe" e usar o − e o +;
   - adicionar, adicionar de novo (aviso da soma) e remover;
   - enviar e ver o cartão de sucesso.
3. Formulário AB: a quantidade acima do estoque aparece no carrinho e no envio; os erros
   ficam no topo.
4. Login: erro com senha errada.
5. Painel:
   - filtros, a tabela no celular rolando só por dentro, a paginação;
   - o menu móvel abaixo de 900px, inclusive pelo teclado e com Esc.
6. Detalhe e atendimento.
7. Saída avulsa até o detalhe.
8. Recibos: a pré-visualização de impressão do navegador mostra só os recibos, um por folha,
   sem cores de fundo.

Problema de comportamento vira teste antes da correção; ajuste visual vai direto, com novo
commit.

- [ ] **Step 6: Commit**

Commit — `Documentação do design Clean e varredura das classes antigas`

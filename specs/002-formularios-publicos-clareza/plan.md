# Implementation Plan: Clareza e facilidade de uso dos formulários públicos de pedido

**Branch**: `002-formularios-publicos-clareza` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-formularios-publicos-clareza/spec.md`

## Summary

Os formulários públicos de pedido ficam mais fáceis de terminar e de entender, sem mudar nenhuma
regra, texto de erro, limite ou o que é gravado:

- no celular, a gaveta do pedido passa a enviar, e a barra fixa diz o próximo passo;
- erros aparecem junto do campo, com resumo focável e com links no topo;
- a página inicial e os títulos falam pelo conteúdo ("Ferramentas, peças e materiais" no lugar de
  "Materiais AB"), com exemplos;
- nome e destino ficam lembrados no aparelho, e sair com materiais no pedido pede confirmação;
- ajustes na busca, no carrinho, nos campos, no cabeçalho e na tela de sucesso.

**Abordagem técnica** (detalhes em [research.md](research.md)):

- `regras.Erro` ganha `campo` opcional, preenchido pelas validações e por `erros_de_tamanho`; a
  view monta `erros_por_campo` para o template (R1);
- a gaveta envia pelo botão final via `requestSubmit`, sem levar estado novo à view do carrinho
  (R2);
- lembrar dados, confirmar a saída e o retorno do "Adicionar" são só `pedidos.js` +
  `localStorage`, com o formulário funcionando igual sem JavaScript (R5, R6, R9);
- a ordem dos resultados muda em `fluxos.buscar`, antes do corte de 50 (R7).

## Technical Context

**Language/Version**: Python 3.13 (`>=3.13,<3.14`); JavaScript ES5 sem build (como o `pedidos.js`)

**Primary Dependencies**: Django 6.x, HTMX 4.0.0 (vendorizado); nenhuma dependência nova

**Storage**: MySQL 8 ou MariaDB, sem mudança de modelo; `localStorage` do navegador para nome e
destino (R5)

**Testing**: pytest + pytest-django contra MySQL/MariaDB (`config.settings_test`); testes de
template pelo `client`; o `pedidos.js` por testes que leem o arquivo-fonte; o comportamento
completo do JavaScript pelo roteiro manual do [quickstart](quickstart.md)

**Target Platform**: navegadores de celular (Android/Chrome, maioria) e desktop; servidor Windows
(waitress atrás do Apache em `/almoxarifado`)

**Project Type**: aplicação web Django (apps `pedidos`, `interface`, `catalogo`)

**Performance Goals**: nenhuma requisição nova; a ordenação dos resultados é uma passada estável
sobre o catálogo já carregado (centenas a poucos milhares de itens)

**Constraints**:

- textos de erro, regras, limites anti-abuso, numeração e gravação iguais (FR-008, FR-028);
- formulário enviável sem JavaScript;
- design system Clean, só tema claro, ícones Lucide locais;
- caminhos sem prefixo fixo (`tests/test_prefixo.py`);
- scripts no `<head>` com `defer`.

**Scale/Scope**:

- 8 templates de `pedidos` e 1 de `interface`;
- `pedidos.js` e `pedidos.css`;
- `regras.py` (dataclass `Erro` e duas validações), `servicos.py` (`erros_de_tamanho`),
  `fluxos.py` (títulos, ordem, texto de estoque), `views/publico.py` (contexto de erros e de
  sucesso);
- ícone novo só se o `_icone.html` não tiver o check/alerta necessários (já tem `check` e
  `alerta`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano cumpre | Situação |
|---|---|---|
| I. Regras puras e fiéis à origem | `Erro.campo` é um dado a mais numa dataclass pura, com padrão `None`; nenhum texto, nenhuma condição e nenhuma ordem de erros muda. A ordem dos resultados da busca é apresentação, não regra de pedido. | ✅ |
| II. Uma porta de gravação | Nada novo grava em `pedidos`; `registrar_pedido` é chamado igual. O identificador do envio continua decidindo reenvio e divergência; o botão da gaveta envia o mesmo `<form>`. | ✅ |
| III. Nunca lançar duas vezes no SCPI | Não toca em `LinhaSaida`, robô nem `LANCAMENTO_REAL`. | ✅ |
| IV. Dados importados não se perdem | Não toca em importações. | ✅ |
| V. Testes contra o banco real | Toda mudança de template e de contexto ganha teste pelo `client` no MySQL/MariaDB; `Erro.campo` e a nova ordem de `buscar` ganham teste puro. O JavaScript é testado lendo o arquivo-fonte (ganchos e chamadas essenciais), como o projeto já faz em `tests/test_carrinho.py`, sem abrir navegador; o comportamento completo fica no roteiro manual do quickstart. | ✅ |
| VI. Interface em pt-BR e acessível | Textos em pt-BR; erro com ícone e texto, nunca só cor; resumo focável com links; anúncio do "Adicionado" por `role="status"`; nada de CDN. | ✅ |
| Restrições técnicas | Nenhuma variável nova no `.env`, nenhuma migration. | ✅ |
| Fluxo de desenvolvimento | Spec e plano antes do código; portões no quickstart; `CLAUDE.md` atualizado no mesmo PR (gaveta envia, `Erro.campo`, dados lembrados no `localStorage`, nomes públicos dos formulários). | ✅ |

**Reavaliação depois da Fase 1**: o contrato e o data-model não acrescentaram gravação, modelo ou
dependência. Nenhuma violação; *Complexity Tracking* fica vazio.

## Project Structure

### Documentation (this feature)

```text
specs/002-formularios-publicos-clareza/
├── plan.md              # este arquivo
├── research.md          # Fase 0: decisões R1–R12
├── data-model.md        # Fase 1: Erro.campo, contextos, Fluxo, localStorage
├── quickstart.md        # Fase 1: portões e roteiro manual
├── contracts/
│   └── telas-publicas.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pedidos/
├── regras.py                     # Erro.campo; campo nos erros de nome e destino
├── servicos.py                   # erros_de_tamanho com campo
├── fluxos.py                     # títulos, sem `formulario`, ordem pedíveis→bloqueados, "disponíveis"
├── views/publico.py              # erros_por_campo; itens e destino no sucesso
├── templates/pedidos/
│   ├── inicio.html               # títulos e exemplos
│   ├── formulario.html           # rótulo "Pedido de materiais"
│   ├── _formulario.html          # resumo de erros, erros por campo, dica do destino, "(opcional)", "Não é você?"
│   ├── _carrinho.html            # barra (vazio/N), gaveta com Enviar, sem código no público
│   ├── _resultados.html          # unidade só embaixo do nome
│   ├── _materiais.html           # região de anúncio do "Adicionado"
│   └── _sucesso.html             # destino, lista de materiais, data-lembrar-*
└── static/pedidos/
    ├── js/pedidos.js             # enviar pela gaveta, foco no resumo, limpar erro, lembrar, beforeunload, "Adicionado"
    └── css/pedidos.css           # botões da gaveta, barra vazia, unidade, campo-ajuda
interface/templates/interface/
└── base_publico.html             # cabeçalho sem "Área do almoxarifado"

tests/
├── test_regras_pedidos.py        # campo dos erros
├── test_registrar_pedido.py      # campo nos erros de tamanho
├── test_formularios_publicos.py  # início, erros por campo, sucesso, cabeçalho, rótulos
└── test_carrinho.py              # barra/gaveta, ordem, "disponíveis", unidade, código só na avulsa
```

**Structure Decision**: tudo cabe nos apps existentes; `pedidos` concentra a mudança e
`interface` só perde o link do cabeçalho público. O `CLAUDE.md` recebe os ajustes descritos no
Constitution Check.

## Ordem sugerida (para o `/speckit-tasks`)

1. **US1 + US2 (P1)**: `Erro.campo` e `erros_por_campo` → template de erros → gaveta com envio e
   barra → JS (enviar pela gaveta, foco, limpar erro).
2. **US3, US4, US5 (P2)**: títulos e início → lembrar nome e destino → `beforeunload`.
3. **US6, US7, US8 (P3)**: campos e destino → busca/carrinho → cabeçalho e sucesso.
4. `CLAUDE.md` e roteiro manual do quickstart.

## Riscos

- **Nomes de evento do HTMX 4** (R9): conferir no arquivo vendorizado antes de escrever o
  retorno do "Adicionar".
- **Folga da busca no celular** (branch `feat/busca-rola-celular`): esta feature parte do `main`
  depois desse merge; mexer na barra fixa pode mudar a altura que o `pedidos.js` usa para a folga
  (`topoLivre`/`caberNaTela`) — conferir no roteiro manual.
- **Testes que conferem textos atuais** (`test_carrinho.py`, `test_formularios_publicos.py`):
  mudam junto, de propósito; listados no quickstart.

## Complexity Tracking

Sem violações.

# Implementation Plan: Clareza e segurança da página Lançamentos SCPI

**Branch**: `ajustes-ui-ux` (diretório da spec: `003-lancamentos-scpi-clareza`) | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-lancamentos-scpi-clareza/spec.md`

## Summary

A página Painel › Lançamentos SCPI passa a mostrar a ação que dá para executar agora, o que vai
ser lançado e o que aconteceu na última execução, sem mudar nenhuma regra do lançamento, nenhuma
trava e nada do que é gravado:

- a ação em destaque é "Simular" enquanto o lançamento real está bloqueado ("Lançar no SCPI" com
  cadeado e a dica do bloqueio, como no cartão do painel), e "Lançar no SCPI" depois da virada;
- os dois botões e o limite de requisições ficam num formulário só; some o "Executar com opções";
- a fila do robô aparece como lista (até 20 requisições, com o total);
- "Não lançar" pede confirmação num segundo passo, também sem JavaScript;
- a falha vira uma frase em português com o próximo passo, o detalhe técnico recolhido e, na
  simulação, "Simular de novo";
- o andamento vira uma frase, uma linha de dados e só os contadores diferentes de zero;
- o histórico mostra "Requisições" (N de M) e a duração; os textos trocam "lote" por "requisição".

**Abordagem técnica** (detalhes em [research.md](research.md)):

- um módulo puro novo, `pedidos/andamento.py`, transforma uma `ExecucaoRobo` em frase, contadores,
  duração, "N de M" e explicação da falha (R4, R5, R6);
- a fila sai de `consultas.fila_do_robo()`, em SQL com a mesma regra de `requisicoes.selecionar`,
  conferida por teste (R2); `lotes_pendentes()` passa a seguir a mesma regra (R3);
- o formulário do lançamento manda o modo pelo botão clicado (`name="modo"`), e o `LancamentoForm`
  continua validando igual (R1);
- o "Não lançar" é um `<details>` com um formulário próprio que manda `confirmado=1`; a view recusa
  `nao_lancar` sem ele, antes de chamar `resolver_lote`, que não muda (R7).

## Technical Context

**Language/Version**: Python 3.13 (`>=3.13,<3.14`); JavaScript ES5 sem build, só se preciso (R7)

**Primary Dependencies**: Django 6.x, HTMX 4.0.0 (vendorizado); nenhuma dependência nova

**Storage**: MySQL 8 ou MariaDB, sem mudança de modelo nem migration (tudo sai de `ExecucaoRobo`
e `LinhaSaida` como estão)

**Testing**: pytest + pytest-django contra MySQL/MariaDB (`config.settings_test`); funções puras
de `pedidos/andamento.py` sem banco; página pelo `client`; concordância da fila em SQL com
`requisicoes.selecionar`; o resto (dica por toque, foco, 375 px) pelo roteiro manual do
[quickstart](quickstart.md)

**Target Platform**: navegador desktop (maioria) e celular; servidor Windows (waitress atrás do
Apache em `/almoxarifado`)

**Project Type**: aplicação web Django (apps `pedidos`, `scpi`, `interface`)

**Performance Goals**: a página faz no máximo duas consultas a mais para a fila (lotes elegíveis
com contagem e corte de 20; primeira linha de cada um), sem carregar todas as linhas pendentes;
a recarga de 3 s durante a execução não fica mais pesada que hoje

**Constraints**:

- regras do lançamento, travas, `LANCAMENTO_REAL`, mensagens das resoluções e gravações iguais
  (FR-022; princípio III);
- `servicos.resolver_lote`, `scpi/lancamento.py` e `scpi/disparo.py` sem mudança de comportamento;
- o trecho recarregado pelo HTMX nunca contém um formulário que o operador esteja usando (FR-011);
- design system Clean, só tema claro, estado nunca só por cor, ícones Lucide locais;
- caminhos sem prefixo fixo (`tests/test_prefixo.py`); scripts no `<head>` com `defer`.

**Scale/Scope**:

- 1 view (`pedidos/views/lancamentos.py`), 2 templates (`lancamentos.html`, `_lancamentos.html`),
  `pedidos/forms.py`, `pedidos/consultas.py`, `pedidos.css`;
- 1 módulo novo (`pedidos/andamento.py`) e a extração de `agrupar` em `scpi/requisicoes.py`;
- fila antes da virada: centenas a poucos milhares de linhas pendentes; histórico: 10 execuções.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como |
|---|---|---|
| I. Regras puras e fiéis | ✅ | A decisão "o que está na fila" fica em `requisicoes.agrupar` (puro, extraído de `selecionar` sem mudar o resultado); a versão SQL em `consultas` é conferida por teste, como `consultas` × `regras.situacao_*`. A apresentação da execução é pura (`pedidos/andamento.py`). |
| II. Uma porta de gravação | ✅ | Nada novo grava. "Não lançar" continua indo por `servicos.resolver_lote`; a view só recusa antes, sem a confirmação. |
| III. Nunca lançar duas vezes | ✅ | Nenhuma mudança em `lancamento.py`, travas, journal ou `LANCAMENTO_REAL`. O botão bloqueado é `type="button"` e o `LancamentoForm` continua recusando `modo=lancar` com o bloqueio ligado. "Simular de novo" é só simulação; falha de lançamento real não ganha atalho para relançar (FR-013). A fila segue a regra do robô: lote travado ou já com requisição não aparece como "a lançar". |
| IV. Dados importados | ✅ n/a | Não toca em importação. |
| V. Testes contra o banco real | ✅ | Cada mudança de comportamento ganha teste no MySQL/MariaDB; nenhum teste abre navegador. |
| VI. Interface pt-BR, acessível | ✅ | Textos em pt-BR, situação escrita além do selo, falha com `role="alert"`, dica ligada por `aria-describedby`, `.mono` nos números de pedido; nada externo. |
| Restrições técnicas | ✅ | Sem modelo novo nem variável nova no `.env`. |
| Fluxo | ✅ | Spec e plano antes do código; `CLAUDE.md` atualizado no mesmo PR (fila, confirmação do "Não lançar", `andamento.py`, formulário sem "Executar com opções"). |

Nenhuma exceção a justificar. **Reavaliação pós-design**: mantida (o design de R1–R8 não grava
nada novo e não toca no robô).

## Project Structure

### Documentation (this feature)

```text
specs/003-lancamentos-scpi-clareza/
├── plan.md              # este arquivo
├── research.md          # decisões R1–R8
├── data-model.md        # estruturas de apresentação (sem modelo novo)
├── quickstart.md        # roteiro de validação
├── contracts/
│   └── pagina-lancamentos.md   # rotas, POSTs e estrutura da página
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pedidos/
├── andamento.py                    # NOVO (puro): frase, contadores, duração, N de M, falha
├── consultas.py                    # fila_do_robo(); lotes_pendentes() com a regra do robô
├── forms.py                        # LancamentoForm sem RadioSelect; modo vem do botão
├── views/lancamentos.py            # contexto novo; resolver exige confirmado no nao_lancar
├── templates/pedidos/
│   ├── lancamentos.html            # sem o rótulo "SCPI"
│   └── _lancamentos.html           # ação, fila, andamento, travas, histórico
└── static/pedidos/css/pedidos.css  # fila, frase do andamento, contadores, confirmação

scpi/
└── requisicoes.py                  # agrupar() extraído de selecionar(), mesmo resultado

tests/
├── test_andamento.py               # NOVO: funções puras
├── test_pagina_lancamentos.py      # ação principal, fila, confirmação, falha, histórico, textos
├── test_scpi_requisicoes.py        # agrupar = parte de selecionar
├── test_consultas_fila.py          # NOVO: SQL × requisicoes.agrupar
├── test_lancamento_real.py         # botão bloqueado com dica, sem envio
└── test_painel.py                  # contagem do cartão com a regra do robô

CLAUDE.md                           # trecho da página Lançamentos SCPI
```

**Structure Decision**: tudo dentro dos apps existentes. A apresentação da execução vai para um
módulo puro em `pedidos` (perto da view que o usa) em vez de template tags, para ser testada sem
banco; a regra da fila continua em `scpi/requisicoes.py`, único dono do "o que o robô lança".

## Complexity Tracking

Nenhuma violação da constituição.

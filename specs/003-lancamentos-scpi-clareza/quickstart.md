# Quickstart: validar a página Lançamentos SCPI

## Pré-requisitos

- MySQL 8 ou MariaDB local, `.env` copiado de `.env.example`, `uv sync` e `migrate` feitos.
- Uma conta do painel (`createsuperuser` ou admin).
- Dados de teste: pedidos atendidos com linhas de saída `PENDENTE` (atender pelo painel, ou pelos
  helpers de `tests/cenario.py` num `manage.py shell`), e ao menos um lote travado (no admin,
  mudar o `status` de uma `LinhaSaida` para "Verificar no SCPI").

## Testes automatizados

```bash
uv run pytest tests/test_andamento.py tests/test_consultas_fila.py tests/test_pagina_lancamentos.py tests/test_lancamento_real.py tests/test_scpi_requisicoes.py tests/test_painel.py
```

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check .
```

```bash
uv run python manage.py makemigrations --check --dry-run
```

Esperado: tudo verde e nenhuma migration nova.

## Roteiro manual (navegador)

Subir o servidor (`preview_start` com o `.claude/launch.json`, ou `uv run python manage.py
runserver`) e abrir `/painel/lancamentos/` logado.

| # | Situação | Conferir | Spec |
|---|---|---|---|
| 1 | `LANCAMENTO_REAL=0`, 2 requisições na fila | "Simular" é o único botão em destaque; "Lançar no SCPI" tem cadeado; Tab até ele mostra a dica e Enter não envia; no celular (375 px) o toque mostra a dica | US1 1–2, FR-001–002 |
| 2 | `LANCAMENTO_REAL=1` (reiniciar o servidor) | "Lançar no SCPI" em destaque, "Simular" secundário | US1 3 |
| 3 | Fila com 2 requisições e um lote travado | "2 requisições aguardando o robô"; duas linhas com Nº, data, recebedor, centro de custo e materiais; o travado não está na lista; o Nº abre o pedido | US2, FR-006–007 |
| 4 | Mais de 20 requisições na fila | 20 linhas e "e mais K requisições"; total correto | FR-008 |
| 5 | Limite 1 e "Simular" | a mensagem fala de 1 requisição; a execução processa 1 | FR-005 |
| 6 | Durante a simulação (`--dry-run` real ou execução recém-criada) | botões e limite desabilitados com o motivo; "requisição N de M" se atualiza a cada 3 s; a recarga para no fim | US1 4, US5 3, FR-017 |
| 7 | Simulação concluída de 3 | frase "… concluída: 3 de 3 requisições preenchidas."; quem iniciou e a duração; só "3 simuladas" | US5 1 |
| 8 | Execução com falha inesperada (ex.: SCPI fora do ar) | frase em português, até onde chegou, "Nenhuma linha mudou de estado."; "Detalhe técnico" fechado; "Simular de novo" inicia outra simulação; leitor de tela anuncia o alerta | US4, FR-012–014 |
| 9 | Falha de lançamento real (simular no shell: `ExecucaoRobo` com `simulacao=False`, `situacao=FALHA`) | sem botão para relançar; link para as travas | US4 4 |
| 10 | Lote travado → "Não lançar…" | abre o aviso; nada gravado até "Confirmar: não lançar"; fechar o painel desiste; confirmado, o lote sai das travas com a mensagem de sempre | US3, FR-009 |
| 11 | Repetir o 10 com o JavaScript desligado | mesmo comportamento (o `<details>` abre sem JS) | FR-010 |
| 12 | Sem travas | só a linha "Nenhuma trava para conferir" | FR-021 |
| 13 | Histórico com simulação 3 de 3 e execução sem fim | "3 de 3" e duração; "—" na sem fim; modo escrito | US6, FR-019 |
| 14 | Celular 375 px | sem rolagem horizontal; o andamento cabe numa tela; erro técnico longo quebra linha | FR-018, SC-005 |
| 15 | 1 requisição na fila | "1 requisição aguardando o robô"; nenhum "lote(s)" na página; sem rótulo "SCPI" acima do título | US7, FR-020 |

Ao fim, voltar `LANCAMENTO_REAL` ao valor de antes.

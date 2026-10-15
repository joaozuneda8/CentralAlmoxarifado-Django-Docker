# Quickstart: validar a página Automações

## Pré-requisitos

- MySQL/MariaDB local e `.env` (ver `README.md`); `uv sync`; banco migrado.
- Um usuário da área interna (`uv run python manage.py createsuperuser`).

## Portões automáticos

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
```

Os testes das duas páginas antigas (`tests/test_pagina_catalogo.py`,
`tests/test_pagina_lancamentos.py`, `tests/test_robos_avulsos.py`) passam contra os endereços novos;
os novos ficam em `tests/test_automacoes.py` (página, abas, regiões HTMX, ações, rotas apagadas, menu) e
`tests/test_historico_automacoes.py` (filtros, situação unificada, intercalação, paginação).

## Cenários no navegador

Suba o servidor (`uv run python manage.py runserver`) e entre em `/painel/entrar/`.

1. **Visão geral (US1)**: abra `/painel/automacoes/`. A barra lateral mostra "Automações" marcado e
   não mostra "Catálogo" nem "Lançamentos SCPI". A visão geral lista lançamento, cadastro, estoque e
   saídas, cada um com o estado em texto.
2. **Estoque com falha**: no shell (`uv run python manage.py shell`), crie
   `Importacao(tipo="ESTOQUE", situacao="FALHA", erro="TimeoutError: …", fim=agora)`. Recarregue: a
   linha do estoque diz "Falhou", a aba Estoque tem o selo, e "Tentar de novo" abre a aba Estoque.
3. **Lançamento (US2)**: com uma saída atendida pendente, abra a aba Lançamento no SCPI: "Simular" em
   destaque, "Lançar no SCPI" com cadeado, fila com a requisição. Simule (o robô abre o SCPI; sem
   acesso, a execução falha com a frase em português). Ao voltar, a página está na mesma aba.
4. **Importação avulsa (US3)**: na aba Estoque, envie `tests/fixtures/scpi/estoque.csv`. A página
   volta à aba Estoque com o aviso; a visão geral acompanha até terminar.
5. **Histórico (US4)**: na visão geral, o histórico mistura as execuções acima, da mais recente para
   a mais antiga. Escolha Robô "Estoque" e Situação "Falhou": a lista se atualiza sem recarregar, o
   endereço muda, a contagem de filtros aparece no botão e, com o painel fechado, cada filtro vira
   um chip. Recarregue: os filtros continuam. "Limpar filtros" volta à lista inteira. Na aba de um
   robô, "Ver histórico" abre a lista filtrada por ele.
6. **Links internos (US5)**: no painel, "para conferir" e o link do catálogo levam direto a
   Automações; `/painel/catalogo/` e `/painel/lancamentos/` dão "página não encontrada".
7. **Sem JavaScript**: desligue o JavaScript; as cinco partes aparecem empilhadas, os filtros
   enviam pelo botão "Filtrar" e a paginação funciona por links.
8. **Celular**: com 375 px de largura, nenhuma parte tem rolagem horizontal da página (as tabelas
   rolam dentro de si).

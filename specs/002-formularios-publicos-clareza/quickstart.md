# Quickstart: validar os formulários públicos

## Pré-requisitos

- Banco local com catálogo e centros de custo carregados (como no desenvolvimento normal).
- `uv sync` feito.

## Portões automáticos

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
```

Os testes de template conferem a estrutura do [contrato](contracts/telas-publicas.md); os de
regras conferem o `campo` dos erros ([data-model](data-model.md)). Testes que mudam de texto:
`tests/test_carrinho.py` ("Estoque: 10 UN" → "10 UN disponíveis", "Ver pedido" → "Revisar e
enviar", "Continuar pedindo" → "Adicionar mais materiais") e
`tests/test_formularios_publicos.py` (início sem "Formulário 1/2").

## Roteiro manual (navegador, `uv run python manage.py runserver`)

Celular (375 px) e desktop, nos dois formulários.

1. **Início** (`/`): sem "Formulário 1/2" nem "AB"; cada cartão com exemplos. (US3)
2. **Gaveta** (`/pedido/ab/`, celular): barra diz "Nenhum material adicionado"; buscar "luva",
   adicionar um → botão mostra "Adicionado" e volta; barra mostra "Seu pedido / 1 material" e
   "Revisar e enviar"; abrir a gaveta → "Enviar pedido" e "Adicionar mais materiais"; sem código
   do material na linha. (US1, US7)
3. **Erros**: com nome vazio, tocar "Enviar pedido" na gaveta → a gaveta fecha, o resumo aparece
   no topo com foco, "Nome completo" e "Destino" como links; tocar no link → foco no campo, que
   está com borda e mensagem; digitar → a borda some. (US1, US2)
4. **Busca**: "luva" no AB → os sem estoque vêm no fim; texto "N UN disponíveis"; unidade só embaixo
   do nome, nada ao lado do − / +; na limpeza, "Adicionar" cabe no painel. (US7)
5. **Sair**: com 1 material no pedido, clicar "Trocar tipo de material" → o navegador pede
   confirmação; com o pedido vazio, sai direto. (US5)
6. **Envio e sucesso**: preencher, enviar → tela de sucesso com destino e lista de materiais;
   "Fazer outro pedido" → nome e destino já preenchidos; sair do sucesso não pede confirmação.
   (US4, US8)
7. **Lembrar**: abrir o outro formulário → nome e destino preenchidos e "Não é você? Limpar"
   visível; tocar → campos vazios; recarregar → continuam vazios. Em aba anônima com
   armazenamento bloqueado, o formulário abre normal. (US4)
8. **Campos**: sem asteriscos; "Observações (opcional)"; "O que pôr aqui?" abre a explicação.
   (US6)
9. **Cabeçalho**: sem "Área do almoxarifado" no topo; o rodapé mantém. (US8)
10. **Sem JavaScript** (desligar no navegador): o formulário envia pelo botão do fim, os erros
    aparecem no topo e nos campos, a explicação do destino abre. (SC-007)
11. **Saída avulsa** (`/painel/saida-avulsa/`): continua mostrando o código no carrinho e não pede
    confirmação ao sair; resultados com a nova ordem e a unidade só embaixo do nome. (FR-029)
12. **Teclado e leitor de tela**: navegar só com Tab até enviar; o resumo é anunciado; o
    "Adicionado" é anunciado. (SC-007)

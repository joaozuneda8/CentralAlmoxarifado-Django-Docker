# Quickstart: validar o de/para e a curva ABC

Roteiro para provar que a funcionalidade funciona de ponta a ponta. Os detalhes de cada tela e do
comando estão em [contracts/](contracts/), e os campos em [data-model.md](data-model.md).

## Pré-requisitos

- MySQL 8 ou MariaDB local e `.env` configurado (README).
- Banco atualizado:

```bash
uv run python manage.py migrate
```

- Cadastro, estoque e saídas importados (do SCPI ou dos CSVs de exemplo):

```bash
uv run python manage.py importar_estoque --arquivo tests/fixtures/scpi/estoque.csv
```

- Para a conferência com a planilha: o `.xlsx` exportado da planilha MAPEAMENTO DE/PARA CONSOLIDADO
  ("Arquivo › Fazer download › Microsoft Excel").

## 1. Testes automatizados

```bash
uv run pytest tests/test_depara.py tests/test_curva.py tests/test_importar_depara.py tests/test_pagina_curva.py tests/test_catalogos.py
```

Esperado: todos passam. Depois, os portões da constituição:

```bash
uv run pytest
```

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run python manage.py makemigrations --check --dry-run
```

## 2. Carga dos pares (história 2)

Ensaio, sem gravar:

```bash
uv run python manage.py importar_depara --arquivo planilha-mapeamento.xlsx --dry-run
```

Esperado: o relatório lista cerca de 400 pares, as correções da aba `DEPARA` e cada par recusado com
o motivo. Nada aparece em Cadastros › Pares de/para.

Carga de verdade:

```bash
uv run python manage.py importar_depara --arquivo planilha-mapeamento.xlsx
```

Esperado: os pares aparecem no admin com origem "planilha", e a página Catálogo mostra uma
importação "Pares de/para" concluída. Altere um par no admin e repita o comando: a carga é recusada
e nada muda.

## 3. Formulário AB consolidado (história 1)

1. Escolha um código antigo com saídas cujo novo também tenha saídas.
2. Abra o formulário AB: o material aparece uma vez só, com o código novo.
3. Confira a posição contra Curva ABC › Frequência: ela soma as ocorrências dos dois códigos.
4. No admin, tente registrar outro destino para o mesmo antigo e um par que feche um ciclo: os dois
   são recusados com a mensagem da spec.

## 4. Curvas e conferência com a planilha (história 3, SC-002 e SC-003)

1. Abra Painel › Curva ABC, aba Frequência, com o mesmo período da planilha.
2. Compare com a aba `ABC_FREQ_CONSOL`: a ordem e a classe precisam bater em pelo menos 99% dos
   materiais. As diferenças aceitas são só as divergências deliberadas da spec e a ordem dentro de
   um empate.
3. Confira a reconciliação no topo: as ocorrências e o valor de antes e de depois são iguais.
4. Na aba Valor, confira que o lançamento de R$ 63 milhões de janeiro aparece como veio (os
   outliers estão fora do escopo).

## 5. Reposição (história 4)

1. Escolha um material com consumo conhecido e confira os valores contra as fórmulas da FR-019.
2. Em Cadastros › Parâmetros de reposição, dê a ele um prazo de entrega de 45 dias e confira que o
   estoque de segurança e o ponto de pedido mudam na hora.
3. Confira que material com saldo 0 aparece como "esgotado", e não pela coluna de grupo, como na
   planilha.

## 6. Pendentes

Na aba Pendentes, confira que aparecem códigos antigos fora do padrão `000.` (como `003.000.025`)
que ainda não têm par.

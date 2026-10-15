# Contrato: comando `importar_depara`

Carga única dos pares da planilha MAPEAMENTO DE/PARA CONSOLIDADO (app `implantacao`).

```text
uv run python manage.py importar_depara --arquivo <planilha.xlsx> [--dry-run]
```

| Opção | Obrigatória | Efeito |
|---|---|---|
| `--arquivo` | sim | `.xlsx` exportado da planilha ("Arquivo › Fazer download › Microsoft Excel") |
| `--dry-run` | não | roda tudo, inclusive a gravação, numa transação desfeita no fim; nada fica gravado e nenhuma `Importacao` é criada |

## Entrada

- **Aba de mapeamento**: a primeira aba cujo nome começa por "Planilha de mapeamento" (o .xlsx
  não aceita "/" no nome de aba, e o Google a exporta como "Planilha de mapeamento depara"),
  colunas obrigatórias "Código Antigo" e "Código Novo".
- **Aba `DEPARA`**: colunas obrigatórias "Código Antigo" e "Código Novo"; "Fator p/ Qtd" e
  "Observação" opcionais.

Aba ou coluna obrigatória ausente: erro, nada é gravado.

## Regras

1. Da aba de mapeamento entram só as linhas com os dois códigos no formato `000.000.000` e antigo
   diferente do novo; as demais ("PRODUTO NOVO", traço, vazio) são ignoradas, com a contagem nos
   avisos.
2. Código antigo repetido na aba de mapeamento: vale a primeira ocorrência; as outras vão para os
   avisos, com o número da linha.
3. A aba `DEPARA` vence a de mapeamento para o mesmo código antigo, e traz o fator (vazio = 1).
4. Cada par passa pelas mesmas validações do admin (formato, antigo ≠ novo, fator > 0, sem ciclo).
   Par recusado vai para os avisos com o motivo e não impede os demais (FR-009).
5. Todos os pares aceitos substituem todos os pares existentes numa única transação (FR-011). Todos
   ficam com origem `PLANILHA`.

## Recusa sem alterar nada

- a planilha não pôde ser lida (aba ou coluna ausente, arquivo inválido);
- existe par com origem `SISTEMA`;
- o histórico do admin registra criação, alteração ou exclusão de par depois do fim da última carga
  bem-sucedida;
- outra carga de pares está em andamento (trava `GET_LOCK` do tipo `DEPARA`, como as importações).

## Saída

Relatório no terminal, igual no ensaio e na carga:
- pares lidos da aba de mapeamento;
- correções da aba `DEPARA`;
- pares gravados (ou que seriam gravados, no ensaio);
- lista dos recusados, com linha, aba e motivo;
- pares de código novo sem cadastro (aviso).

A carga de verdade registra uma `Importacao` do tipo `DEPARA` com esse resumo, e o código de saída
do comando é diferente de zero quando ela é recusada.

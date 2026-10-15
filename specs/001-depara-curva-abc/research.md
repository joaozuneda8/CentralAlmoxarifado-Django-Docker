# Pesquisa: De/para de códigos e curva ABC consolidada

Decisões da Fase 0. Cada uma resolve uma dúvida do contexto técnico ou fixa uma regra que a spec
deixou para o plano. As fórmulas de origem foram lidas da planilha MAPEAMENTO DE/PARA CONSOLIDADO
exportada em 2026-10-12.

## D1. Onde mora cada parte

- **Decisão**: o de/para, os parâmetros de reposição e os cálculos ficam no app `catalogo`. A carga
  dos pares da planilha fica no app `implantacao`, ao lado do `importar_planilhas`.
- **Motivo**: `catalogo` já guarda os cadastros mantidos à mão e monta o catálogo do formulário AB
  (`catalogos.py`). A carga da planilha é migração única, como o `importar_planilhas`, e pode ser
  apagada depois da virada junto com ele.
- **Alternativas**: um app novo (`curva`) dividiria `catalogos.py` entre dois apps e criaria uma
  dependência circular com o formulário AB; a carga no `catalogo` deixaria código de migração
  permanente no app principal.

## D2. Como resolver o código canônico

- **Decisão**: função pura `resolver_canonicos(pares)` em `catalogo/depara.py`, que recebe os pares
  (antigo, novo, fator) e devolve, para cada código antigo, o canônico final e o fator acumulado
  (produto dos fatores da cadeia). Códigos comparados por `norm_u`. Ciclo é erro.
- **Motivo**: são ~400 pares; montar o mapa em memória a cada consulta custa uma consulta e
  microssegundos, e a função pura é testável sem banco (Princípio I). A cadeia inteira corrige a
  limitação de dois saltos da planilha (divergência 3).
- **Fator na cadeia**: A → N com fator 5 e N → M com fator 2 dão A → M com fator 10. A planilha não
  tem cadeias com fator; o produto é a única leitura coerente com "quantidade convertida".
- **Alternativas**: guardar o canônico já resolvido em cada par (desnormalizado) exigiria
  recalcular toda a tabela a cada edição; uma consulta recursiva no banco é mais difícil de testar.

## D3. Como consolidar as saídas

- **Decisão**: uma consulta agrega `SaidaSCPI` por `cadpro` no período (ocorrências, soma de
  quantidade, soma de valor). O resultado (uma linha por código, menos de mil) passa por uma função
  pura `consolidar(linhas, canonicos)`, que troca o código pelo canônico, multiplica a quantidade
  pelo fator e soma por canônico.
- **Motivo**: agregar no banco antes de consolidar mantém o volume pequeno, e somar depois de
  multiplicar pelo fator é equivalente a converter linha a linha, porque o fator é o mesmo para
  todas as saídas de um código. Valor e ocorrências passam sem mudança (LEIAME, regra 1).
- **Sem cache**: como `catalogos.py` hoje; o efeito de um par novo aparece na próxima consulta
  (SC-005).
- **Alternativas**: replicar a `MOV_NORM` como tabela materializada criaria estado a manter
  sincronizado a cada importação e a cada edição de par.

## D4. Período (janela móvel)

- **Decisão**: `inicio = max(01/01/2026, hoje − meses)` e `fim = hoje`, com `meses` vindo da
  configuração (padrão 12). A data mínima é a constante `INICIO_DADOS_CONFIAVEIS = date(2026, 1, 1)`.
  Os dias do período são contados de forma inclusiva: `(fim − inicio).days + 1`.
- **Motivo**: decisão do João (janela móvel, nunca antes de 01/01/2026). A contagem inclusiva evita
  dividir por zero no primeiro dia e se aproxima da planilha, que divide pela diferença fracionária
  entre agora e o início.
- **O formulário AB usa a mesma janela.** Hoje ele conta todo o histórico importado; como o
  histórico começa em 01/01/2026, a diferença só aparece depois de 12 meses de dados.
- **Alternativas**: período fixo desde 01/01/2026 (o da planilha) cresce sem limite e dilui o
  consumo recente.

## D5. Curva ABC

- **Decisão**: função pura `curva(linhas, chave)` em `catalogo/curva.py`, com `chave` igual a
  ocorrências ou valor. Ordena pela chave decrescente e, no empate, pelo código. Percentual =
  item ÷ total; acumulado = soma até o item ÷ total. Classe: A com acumulado ≤ 0,78; B com ≤ 0,95;
  C no restante, como as fórmulas `IF(G<=0.78,"A",IF(G<=0.95,"B","C"))` das abas `ABC_*_CONSOL`.
- **Motivo**: reproduz a planilha (SC-002). O desempate pelo código torna a ordem determinística;
  o `QUERY` da planilha não define desempate, então a comparação do SC-002 aceita diferença de
  ordem dentro de um empate.
- **Total zero** (nenhuma saída ou valor total 0): a curva sai vazia, com aviso.

## D6. Reposição

- **Decisão**: função pura `reposicao(...)` em `catalogo/curva.py` com as fórmulas da spec (FR-019),
  em `Decimal`:
  - consumo diário = consumo total ÷ dias do período;
  - estoque de segurança = arredonda(consumo diário × prazo de entrega), meio para cima;
  - ponto de pedido = arredonda(consumo diário × prazo de entrega + estoque de segurança);
  - quanto pedir = teto(consumo diário × cobertura alvo + estoque de segurança);
  - cobertura em dias = estoque ÷ consumo diário, com duas casas;
  - situação = esgotado (estoque ≤ 0), comprar (estoque ≤ ponto de pedido) ou em estoque.
- **Motivo**: são as fórmulas da aba de mapeamento (`ROUND(G*Q,0)`, `ROUND(G*Q+M,0)`,
  `ROUNDUP(G*90+M,0)`, `J/G`), com o fator aplicado ao consumo (divergência 1) e a situação lida do
  estoque (divergência 2). O "comprar" substitui o "Nova compra necessária" digitado à mão na
  planilha por uma regra.
- **Estoque**: saldo do canônico + saldos dos códigos antigos que apontam para ele (como as colunas
  "Estoque Código Antigo/Novo"). O saldo dos antigos não é convertido pelo fator, como na planilha.
- **Alternativas**: arredondar só no fim mudaria o ponto de pedido em uma unidade em alguns casos e
  quebraria a comparação com a planilha.

## D7. Configuração geral e por material

- **Decisão**: um modelo de linha única `ConfiguracaoCurva` (janela em meses, prazo de entrega e
  cobertura alvo gerais), editado no admin, e um modelo `ParametroReposicao` (material, prazo de
  entrega e cobertura alvo opcionais), também no admin, com `autocomplete` do material.
- **Motivo**: a spec pede valores ajustáveis por quem mantém cadastros, sem reiniciar o sistema;
  variáveis do `.env` não servem. `Opcao` guarda listas de texto e não serve para números.
- **Linha única**: o código lê com `ConfiguracaoCurva.atual()`, que cria a linha com os padrões
  (12, 30, 90) se ela faltar; o admin não permite criar uma segunda nem apagar a existente.

## D8. Registro e trava da carga dos pares

- **Decisão**:
  - Cada carga gera uma `Importacao` de um tipo novo, `DEPARA`, com linhas, avisos e erro, e aparece
    na página Catálogo como as demais.
  - O par guarda `origem` (PLANILHA ou SISTEMA). O admin marca SISTEMA ao criar ou alterar.
  - A carga é recusada se houver par com origem SISTEMA ou se o histórico do admin (`LogEntry`) tiver
    qualquer criação, alteração ou exclusão de par depois do fim da última carga bem-sucedida.
- **Motivo**: o `LogEntry` já registra quem fez o quê e quando (FR-005) e cobre a exclusão, que não
  deixa linha para marcar. É a mesma ideia da trava do `importar_planilhas` (Princípio IV).
- **Alternativas**: um carimbo de "alterado em" na configuração exigiria lembrar de atualizá-lo em
  todo caminho de gravação.

## D9. Leitura da planilha de mapeamento

- **Decisão**:
  - A carga lê o `.xlsx` exportado ("Arquivo › Fazer download › Microsoft Excel").
  - Os pares do espelho vêm da aba de mapeamento original (colunas "Código Antigo" e "Código Novo").
    O `.xlsx` a exporta como "Planilha de mapeamento depara" (o formato não aceita "/" no nome de
    aba); vale a primeira aba cujo nome começa por "Planilha de mapeamento".
  - O sistema aplica ele mesmo as regras do `DEPARA_MAP`: os dois códigos no formato `000.000.000`,
    antigo diferente do novo, linhas com "PRODUTO NOVO", traço ou vazio ignoradas, e para código
    antigo repetido vale a primeira ocorrência, com aviso.
  - As correções vêm da aba `DEPARA` (colunas "Código Antigo", "Código Novo", "Fator p/ Qtd") e vencem
    o espelho.
  - `implantacao.planilha.ler_xlsx` ganha o parâmetro `abas` (hoje fixo em `ABAS`), para ler essas
    abas com a mesma rotina.
- **Motivo**: a aba `DEPARA_MAP` é uma fórmula `FILTER`; no `.xlsx` ela vem como valor em cache, que
  pode estar velho. Ler a fonte e aplicar a regra declarada no próprio `DEPARA_MAP` é mais seguro.
- **Ordem**: o `DEPARA_MAP` ordena pelo código novo antes de buscar; a regra declarada ("vale a
  primeira ocorrência") é a da aba de origem, e é a que o sistema segue.

## D10. Pendentes de mapeamento

- **Decisão**: um código é pendente se tem saída no período, não é antigo de nenhum par e o
  `Material` dele está oculto ou não existe no cadastro. A lista mostra ocorrências e valor, do maior
  valor para o menor.
- **Motivo**: FR-006 e divergência 4. O cadastro do SCPI marca como oculto o que foi inativado, e é
  esse o sinal de código antigo; o prefixo `000.` deixa de fora antigos como `003.000.025`.

## D11. Migrations

- **Decisão**: regenerar a `0001_initial` do `catalogo`, como manda a regra do projeto. O João
  confirmou em 2026-10-12 que a importação das planilhas no servidor (passo 3 de `deploy/VIRADA.md`)
  ainda não aconteceu. Se ela acontecer antes desta funcionalidade chegar ao `main`, a mudança vira
  uma `0002`.
  - A linha única de `ConfiguracaoCurva` é criada por `ConfiguracaoCurva.atual()`, não por migration
    de dados (o projeto proíbe migration de conversão de dados).
- **Motivo**: constituição, "Restrições técnicas".

## D12. Testes

- **Decisão**:
  - Funções puras (`resolver_canonicos`, `consolidar`, `curva`, `reposicao`, validação de par e
    leitura da planilha) com testes sem banco.
  - Formulário AB, admin, páginas e carga com testes no MySQL/MariaDB, com um `.xlsx` de exemplo
    montado no teste com `openpyxl`, como o `tests/planilha_exemplo.py`.
  - O teste que limita o número de consultas de `catalogo_ab()` sobe de 5 para 6 (a leitura dos
    pares).
- **SC-002** (comparar com a planilha real) é conferência manual, descrita no `quickstart.md`.

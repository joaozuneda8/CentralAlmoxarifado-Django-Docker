# Feature Specification: De/para de códigos e curva ABC consolidada

**Feature Branch**: `001-depara-curva-abc`

**Created**: 2026-10-12

**Status**: Implementada

**Input**: User description: "De/para de códigos (antigo → canônico) e curva ABC consolidada, substituindo a planilha MAPEAMENTO DE/PARA CONSOLIDADO"

## Contexto

Em março de 2026 o cadastro de materiais do SCPI foi padronizado: muitos materiais ganharam um
código novo, e o histórico de saídas ficou dividido entre o código antigo e o novo. Hoje o
sistema conta as saídas pelo código lançado, então o mesmo material aparece fatiado: perde
posição no formulário AB, ou aparece duas vezes (com o código antigo e o novo).

A planilha MAPEAMENTO DE/PARA CONSOLIDADO resolve isso fora do sistema: guarda os pares código
antigo → código novo, troca cada saída pelo código canônico antes de somar e, a partir daí,
calcula as curvas ABC (por frequência e por valor) e uma tabela de reposição (consumo, estoque de
segurança, ponto de pedido, quanto pedir, cobertura). Esta funcionalidade traz tudo isso para o
sistema, e a planilha deixa de ser necessária.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manter o de/para e ver o formulário AB consolidado (Priority: P1)

O responsável pelo cadastro registra no sistema os pares "código antigo → código novo" (com fator
de conversão quando a unidade mudou) e corrige ou remove pares errados. A partir daí, o formulário
AB passa a ordenar os materiais pelo número de saídas somado do código antigo com o canônico, e
nenhum material aparece duas vezes.

**Why this priority**: É o defeito que existe hoje: o formulário AB que os funcionários usam está
com a ordem errada e pode mostrar o mesmo material duas vezes. Sem o de/para, nada do resto
(curvas, reposição) fica correto.

**Independent Test**: Com saídas importadas nos códigos `A` (antigo) e `N` (novo), cadastrar o par
`A → N` e conferir que o formulário AB mostra só `N`, na posição dada pela soma das saídas de `A`
e `N`.

**Acceptance Scenarios**:

1. **Given** 30 saídas no código antigo `A` e 20 no novo `N`, sem par cadastrado, **When** o par
   `A → N` é registrado, **Then** o formulário AB passa a mostrar `N` uma vez só, contando 50
   saídas, e `A` não aparece mais.
2. **Given** o par `A → N` e o par `N → M`, **When** o formulário AB é montado, **Then** as saídas de
   `A`, `N` e `M` contam todas para `M`.
3. **Given** o par `A → N` já registrado, **When** alguém tenta registrar `A → X`, **Then** o sistema
   recusa e explica que `A` já aponta para `N` (um código antigo tem um só destino).
4. **Given** os pares `A → N` e `N → A` (ciclo), **When** o segundo é registrado, **Then** o sistema
   recusa e explica o ciclo.
5. **Given** um par registrado por engano, **When** ele é removido, **Then** o formulário AB volta a
   contar o código antigo separado, como antes do par.

---

### User Story 2 - Trazer os pares da planilha (Priority: P1)

Na implantação, o responsável exporta a planilha de mapeamento e o sistema carrega de uma vez os
pares que ela já tem (cerca de 400), com as correções manuais e os fatores, mostrando um relatório
do que entrou, do que foi recusado e por quê.

**Why this priority**: Os pares existentes são o trabalho de meses de padronização. Redigitá-los à
mão seria lento e sujeito a erro; sem eles, a história 1 começa vazia.

**Independent Test**: Carregar a exportação da planilha num sistema sem pares e conferir que o total
de pares, os fatores e as correções manuais batem com a planilha, e que o relatório lista cada par
recusado com o motivo.

**Acceptance Scenarios**:

1. **Given** a exportação da planilha com os pares do espelho e as correções manuais, **When** ela é
   carregada, **Then** cada código antigo fica com o destino da correção manual quando ela existe, e
   com o do espelho quando não existe.
2. **Given** um par fora do formato `000.000.000`, com antigo igual ao novo ou que formaria ciclo,
   **When** a planilha é carregada, **Then** o par é recusado e aparece no relatório com o motivo, e
   os demais entram.
3. **Given** um ensaio da carga, **When** ele é executado, **Then** o relatório sai completo e nada é
   gravado.
4. **Given** pares que já foram criados ou alterados no sistema depois da última carga, **When** a
   planilha é carregada de novo, **Then** a carga é recusada sem alterar nada, para não apagar o
   trabalho feito no sistema.

---

### User Story 3 - Consultar as curvas ABC consolidadas (Priority: P2)

O almoxarifado abre a curva ABC por frequência ou por valor, consolidada pelo código canônico, com
quantidade, valor, ocorrências, percentual, percentual acumulado e classe (A, B ou C) de cada
material, num período escolhido.

**Why this priority**: É a informação que a planilha entrega hoje para decidir o que priorizar no
estoque. Depende da história 1, mas não é necessária para o formulário AB funcionar.

**Independent Test**: Com saídas e pares conhecidos, abrir a curva por frequência e conferir a
ordem, os percentuais e a classe de cada material contra um cálculo feito à mão.

**Acceptance Scenarios**:

1. **Given** saídas consolidadas, **When** a curva por frequência é aberta, **Then** os materiais
   aparecem do mais para o menos requisitado, e a classe é A até 78% do acumulado, B até 95% e C
   no restante.
2. **Given** a mesma situação, **When** a curva por valor é aberta, **Then** a ordem e as classes
   seguem o valor total em vez do número de ocorrências.
3. **Given** a consolidação aplicada, **When** os totais da curva são comparados com as saídas
   importadas no mesmo período, **Then** o número de ocorrências e o valor total são iguais; só o
   número de linhas diminui.
4. **Given** um período escolhido que começa antes de 01/01/2026, **When** a curva é aberta,
   **Then** ela usa só as saídas a partir de 01/01/2026 e informa isso.

---

### User Story 4 - Saber o que repor (Priority: P3)

O almoxarifado consulta, para cada material com saídas no período, o consumo, o estoque (somando o
saldo do código antigo com o do canônico), o estoque de segurança, o ponto de pedido, quanto pedir,
a cobertura em dias e a situação (esgotado, comprar ou em estoque), e ajusta o prazo de entrega ou a
cobertura alvo dos materiais que fogem do padrão.

**Why this priority**: Substitui a última parte da planilha, mas o processo de compra pode
continuar usando a planilha por algum tempo sem prejudicar a operação.

**Independent Test**: Para um material com consumo e saldo conhecidos, conferir os valores
calculados contra as fórmulas desta spec, e conferir que mudar o prazo de entrega do material muda
o estoque de segurança e o ponto de pedido.

**Acceptance Scenarios**:

1. **Given** um material com 600 unidades consumidas em 300 dias (2 por dia), saldo de 100, prazo de
   entrega de 30 dias e cobertura alvo de 90 dias, **When** a reposição é consultada, **Then**
   mostra estoque de segurança 60, ponto de pedido 120, quanto pedir 240, cobertura de 50 dias e a
   situação "comprar".
2. **Given** o mesmo material com prazo de entrega próprio de 45 dias, **When** a reposição é
   consultada, **Then** o estoque de segurança passa a 90 e o ponto de pedido a 180.
3. **Given** um material com saldo 0, **When** a reposição é consultada, **Then** a situação é
   "esgotado".
4. **Given** um par com fator 5 (o antigo era um frasco de 5 L e o novo é de 1 L), **When** o
   consumo é calculado, **Then** cada unidade saída no código antigo conta como 5 no canônico.

---

### Edge Cases

- Código antigo com saídas e sem par, cujo material está oculto no cadastro ou não existe nele: o
  sistema o lista como pendente de mapeamento, com o número de saídas e o valor, para alguém criar
  o par.
- Vários códigos antigos apontando para o mesmo novo (N:1): somam normalmente.
- Código canônico sem cadastro, ou oculto no cadastro: fica fora do formulário AB e aparece como
  problema na situação do catálogo, como hoje.
- Código canônico que também está no formulário de limpeza: fica fora do formulário AB, como hoje (a
  limpeza prevalece).
- Material sem saídas no período: fica fora das curvas e da reposição.
- Período sem nenhuma saída: as curvas e a reposição aparecem vazias, com aviso.
- Fator de conversão zero, negativo ou não numérico: recusado.
- Par cujo código novo não existe no cadastro: aceito, com aviso (o cadastro pode ser importado
  depois).
- Saída com valor absurdo (como o lançamento de R$ 63 milhões em janeiro): entra na curva por valor
  como veio; o sistema não tenta corrigir.

## Requirements *(mandatory)*

### Functional Requirements

**De/para**

- **FR-001**: O sistema MUST guardar pares "código antigo → código novo", cada um com fator de
  conversão de quantidade (padrão 1) e observação opcional.
- **FR-002**: O sistema MUST aceitar só códigos no formato `000.000.000` e recusar par com antigo
  igual ao novo.
- **FR-003**: O sistema MUST recusar um segundo destino para o mesmo código antigo (sem 1:N) e
  aceitar vários antigos para o mesmo novo (N:1).
- **FR-004**: O sistema MUST resolver o código canônico de forma transitiva (A → N → M dá M) e
  recusar o par que formaria um ciclo.
- **FR-005**: Usuários com permissão de manter cadastros MUST poder criar, alterar e remover pares,
  e o sistema MUST registrar quem fez cada alteração e quando.
- **FR-006**: O sistema MUST listar os códigos pendentes de mapeamento: códigos com saídas no
  período, sem par, cujo material está oculto no cadastro ou não existe nele, com o número de
  saídas e o valor de cada um.
- **FR-007**: Ao registrar um par, o sistema MUST avisar quando o código novo não existe no
  cadastro, sem impedir o registro.

**Carga dos pares da planilha**

- **FR-008**: O sistema MUST carregar os pares a partir da exportação da planilha de mapeamento,
  combinando os pares do espelho com as correções manuais, que vencem em caso de conflito, e
  trazendo os fatores.
- **FR-009**: A carga MUST aplicar as mesmas validações do registro manual, juntar todos os
  problemas e mostrá-los de uma vez; par recusado não impede os demais.
- **FR-010**: A carga MUST ter um modo de ensaio, que produz o mesmo relatório sem gravar nada.
- **FR-011**: A carga MUST substituir todos os pares de uma vez (ou nada muda, se falhar) e MUST ser
  recusada quando houver par criado ou alterado no sistema depois da última carga.

**Consolidação e formulário AB**

- **FR-012**: Toda contagem e soma de saídas MUST usar o código canônico de cada saída; o valor e as
  ocorrências são somados como vieram, e a quantidade é multiplicada pelo fator do par.
- **FR-013**: O formulário AB MUST ordenar os materiais pelas ocorrências consolidadas no período da
  curva (FR-015) e mostrar cada material uma vez só, pelo código canônico.
- **FR-014**: O formulário AB MUST mostrar o saldo do código canônico (que é onde a saída será
  lançada) e manter as regras atuais de exclusão (sem cadastro, oculto, grupo oculto, presente na
  limpeza).

**Curvas ABC**

- **FR-015**: O período das curvas e da reposição MUST ser uma janela móvel configurável (padrão de
  12 meses, podendo ser maior) que nunca começa antes de 01/01/2026; quando a janela pediria uma
  data anterior, o início efetivo é 01/01/2026 e a tela informa isso.
- **FR-016**: O sistema MUST mostrar a curva ABC por frequência e a curva por valor, cada uma com
  código canônico, descrição, ocorrências, quantidade, valor, percentual, percentual acumulado e
  classe.
- **FR-017**: A classe MUST ser A até 78% do acumulado, B até 95% e C no restante.
- **FR-018**: O sistema MUST mostrar a reconciliação: totais de ocorrências e de valor antes e depois
  da consolidação (que precisam ser iguais) e o número de linhas antes e depois.

**Reposição**

- **FR-019**: Para cada material canônico com saídas no período, o sistema MUST calcular:
  consumo total (quantidade convertida); consumo diário (consumo total ÷ dias do período efetivo);
  estoque (saldo do canônico + saldo dos códigos antigos que apontam para ele); estoque de segurança
  (consumo diário × prazo de entrega); ponto de pedido (consumo diário × prazo de entrega + estoque
  de segurança); quanto pedir (consumo diário × cobertura alvo + estoque de segurança, arredondado
  para cima); cobertura em dias (estoque ÷ consumo diário); e a situação.
- **FR-020**: A situação MUST ser "esgotado" com estoque 0 ou menor, "comprar" com estoque até o
  ponto de pedido e "em estoque" acima dele.
- **FR-021**: O prazo de entrega (padrão 30 dias) e a cobertura alvo (padrão 90 dias) MUST ter um
  valor geral configurável e poder ser substituídos por material.

**Documentação e planilha**

- **FR-022**: A documentação do projeto MUST deixar de dizer que as saídas do SCPI substituem a aba
  `MOV_NORM` (elas equivalem à aba `Saídas`), e o roteiro da virada MUST manter a planilha de
  mapeamento disponível até a carga dos pares (história 2) ser feita e conferida.

### Divergências deliberadas da planilha

Pelo Princípio I da constituição, cada diferença em relação à planilha fica registrada aqui:

1. **O fator vale também no consumo da reposição.** Na planilha, o consumo da tabela de reposição
   soma as quantidades sem o fator, misturando unidades.
2. **A situação "esgotado/em estoque" usa o estoque.** Na planilha, a maior parte da coluna testa a
   coluna Grupo em vez do Estoque e marca como esgotado material com saldo.
3. **A cadeia de pares é resolvida até o fim.** A planilha resolve no máximo dois saltos.
4. **Pendentes pelo cadastro, não pelo prefixo.** A planilha só lista como pendentes os códigos que
   começam com `000.`; códigos antigos como `003.000.025` nunca aparecem.
5. **Período móvel.** A planilha usa um período fixo a partir de 01/01/2026 até hoje.
6. **Reposição de todo material com saídas.** A planilha só calcula a reposição das linhas da aba de
   mapeamento.
7. **Sem sugestão de pares por semelhança de nome.** A planilha gera sugestões assim no
   diagnóstico; o sistema não as gera, pela própria regra da planilha de que nada é unido por nome.

### Key Entities

- **Par de/para**: um código antigo, o código novo para o qual ele aponta, o fator de conversão de
  quantidade, a observação, quem registrou ou alterou e quando, e se veio da carga da planilha.
- **Código canônico**: não é guardado; é o destino final de um código depois de seguir os pares (ou
  o próprio código, se não houver par).
- **Parâmetros de reposição**: o prazo de entrega e a cobertura alvo gerais, e a substituição de cada
  um por material.
- **Configuração do período**: o tamanho da janela móvel das curvas e da reposição.
- **Carga de pares**: o registro de cada carga da planilha (quando, quem, quantos pares entraram,
  quantos foram recusados e por quê).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nenhum material aparece mais de uma vez no formulário AB por causa da recodificação.
- **SC-002**: Com os mesmos pares e as mesmas saídas, a ordem e as classes da curva por frequência
  coincidem com as da aba `ABC_FREQ_CONSOL` da planilha em pelo menos 99% dos materiais (as
  diferenças só podem vir das divergências deliberadas).
- **SC-003**: Os totais de ocorrências e de valor das curvas são idênticos aos das saídas importadas
  no mesmo período.
- **SC-004**: Todos os pares da planilha (cerca de 400) entram numa única carga, e cada par
  recusado aparece no relatório com o motivo.
- **SC-005**: O responsável cadastra um par novo e vê o efeito no formulário AB em menos de 1 minuto,
  sem rodar nenhuma tarefa à parte.
- **SC-006**: Depois da virada, o almoxarifado deixa de abrir a planilha de mapeamento para
  consultar curva ABC ou reposição.

## Assumptions

- Quem mantém os pares e os parâmetros de reposição são os usuários da área interna com permissão de
  manter cadastros, como já acontece com itens de limpeza e centros de custo.
- As curvas, a reposição e a lista de pendentes ficam na área interna, para qualquer usuário do
  almoxarifado; a exportação para planilha fica fora desta funcionalidade.
- A carga dos pares lê a exportação da planilha MAPEAMENTO DE/PARA CONSOLIDADO (abas de espelho e de
  correções manuais); depois da carga conferida, o sistema passa a ser a única fonte dos pares.
- As saídas usadas são as já importadas do SCPI; esta funcionalidade não muda a importação. Os dados
  anteriores a 01/01/2026 não são confiáveis e nunca entram nos cálculos.
- Valores absurdos de saída (outliers) ficam como vieram nesta funcionalidade; a correção é feita no
  SCPI.
- O conserto definitivo (inativar os códigos antigos no SCPI) é feito fora do sistema; enquanto ele
  não acontece, os pares precisam ser mantidos.
- A lista dos pendentes não sugere pares; quem cria o par decide qual é o código novo.

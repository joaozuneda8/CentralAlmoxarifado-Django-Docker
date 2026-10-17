# Feature Specification: Clareza e segurança da página Lançamentos SCPI

**Feature Branch**: `ajustes-ui-ux`

**Created**: 2026-10-14

**Status**: Implementada

**Input**: User description: "pode fazer tudo" — aplicar as 10 propostas da auditoria de fluxo e
usabilidade da página Painel › Lançamentos SCPI (ação principal, opções de execução, fila de
requisições, confirmação do "Não lançar", erro e andamento da execução, histórico e textos).

## Contexto

Na página Lançamentos SCPI, o almoxarifado dispara o robô que lança no SCPI as saídas atendidas
(ou só simula o lançamento), acompanha a execução e resolve os lotes travados. Uma auditoria feita
no navegador (desktop e celular de 375 px), com o lançamento real ainda bloqueado até a virada,
achou pontos que confundem ou expõem a erro quem opera a página:

- o botão de destaque é "Lançar no SCPI", que está desabilitado; a única ação possível, "Simular",
  parece secundária e o motivo do bloqueio é um texto solto, longe do botão;
- "Executar com opções" repete a escolha entre simular e lançar, que os dois botões já fazem, e
  esconde a única opção nova (o limite de requisições);
- a página diz só "1 lote(s) aguardando o robô": não dá para ver o que vai ser lançado;
- "Não lançar" tira a requisição do lançamento com um único clique, sem confirmação;
- quando a execução falha, aparece a exceção técnica em inglês, sem dizer o que fazer;
- o andamento mostra nove números rotulados, quase todos zero; no celular viram uma coluna longa;
- no histórico, a coluna "Lançadas" mostra 0 para toda simulação, mesmo a que simulou tudo;
- "lote", palavra interna do sistema, aparece onde o usuário pensa em "requisição".

Esta funcionalidade muda a apresentação e o fluxo da página. As regras do lançamento (quando um
lote é lançado, travado ou liberado), as travas contra lançar duas vezes, o bloqueio do lançamento
real até a virada e o que o robô grava continuam iguais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A ação possível em destaque (Priority: P1)

Quem abre a página vê como ação principal a que pode de fato executar agora. Até a virada, essa
ação é "Simular"; "Lançar no SCPI" aparece com um cadeado e, ao ser focado ou tocado, explica por
que está bloqueado. Depois da virada, "Lançar no SCPI" volta a ser a ação principal.

**Why this priority**: É a primeira coisa que o operador vê. Hoje o destaque aponta para um botão
morto, e o operador não entende por que nada acontece.

**Independent Test**: Com o lançamento real bloqueado, abrir a página e conferir que "Simular" é a
ação principal e que "Lançar no SCPI" mostra o motivo do bloqueio por foco do teclado e por toque;
com o lançamento real liberado, conferir o inverso.

**Acceptance Scenarios**:

1. **Given** o lançamento real bloqueado e requisições na fila, **When** o operador abre a página,
   **Then** "Simular" é a única ação em destaque e "Lançar no SCPI" aparece com um cadeado, num
   estilo que não convida ao clique.
2. **Given** o lançamento real bloqueado, **When** o operador foca "Lançar no SCPI" pelo teclado,
   passa o cursor ou toca nele, **Then** aparece a explicação "Lançamento real bloqueado até a
   virada: só a simulação roda." e nada é enviado.
3. **Given** o lançamento real liberado e requisições na fila, **When** o operador abre a página,
   **Then** "Lançar no SCPI" é a ação em destaque e "Simular" é secundária.
4. **Given** uma execução em andamento, **When** o operador olha os botões, **Then** nenhum dos dois
   inicia outra execução e a página diz que há uma execução em andamento.
5. **Given** nenhuma requisição na fila, **When** o operador abre a página, **Then** a página diz
   que não há nada aguardando o robô e os botões não iniciam execução.

---

### User Story 2 - Ver o que vai ser lançado antes de disparar (Priority: P1)

Antes de simular ou lançar, o operador vê a lista das requisições na fila do robô: o pedido (ou a
saída avulsa) de origem, a data, o recebedor, o centro de custo e o número de materiais de cada uma.

**Why this priority**: Lançar no SCPI é uma ação que o sistema não consegue desfazer (constituição,
princípio III). Ver a fila antes do clique é a última chance de notar algo errado.

**Independent Test**: Com duas requisições pendentes, abrir a página e conferir as duas linhas da
lista com seus dados, e o link de cada uma para o pedido.

**Acceptance Scenarios**:

1. **Given** duas requisições na fila, **When** o operador abre a página, **Then** vê o total ("2
   requisições aguardando o robô") e uma linha por requisição com número de origem, data,
   recebedor, centro de custo e número de materiais.
2. **Given** a lista da fila, **When** o operador escolhe o número de uma requisição, **Then** abre
   o detalhe do pedido de origem.
3. **Given** mais requisições na fila do que a lista mostra, **When** o operador a olha, **Then** vê
   as primeiras e a indicação de quantas ficaram de fora.
4. **Given** um lote travado (para conferir), **When** o operador olha a fila, **Then** esse lote não
   aparece nela, só em "Travas para conferir", como hoje o robô o deixa de fora.

---

### User Story 3 - Confirmar antes de tirar uma requisição do lançamento (Priority: P1)

Ao escolher "Não lançar" num lote travado, o operador precisa confirmar num segundo passo, que diz
o que vai acontecer, antes de a requisição sair do lançamento.

**Why this priority**: É a ação mais difícil de desfazer da página e hoje vai com um clique, ao
lado de botões de uso comum.

**Independent Test**: Num lote travado, escolher "Não lançar", conferir que nada mudou ainda, e
confirmar; o lote sai das travas.

**Acceptance Scenarios**:

1. **Given** um lote travado, **When** o operador escolhe "Não lançar", **Then** a página pede
   confirmação dizendo que a requisição não será lançada no SCPI, e o lote continua travado.
2. **Given** o pedido de confirmação na tela, **When** o operador confirma, **Then** o lote é marcado
   para não lançar e a página avisa o resultado, como hoje.
3. **Given** o pedido de confirmação na tela, **When** o operador desiste, **Then** o lote continua
   travado e nada é gravado.
4. **Given** o navegador sem JavaScript, **When** o operador escolhe "Não lançar", **Then** o lote só
   é marcado depois de uma confirmação explícita (a ação não vai num clique só).

---

### User Story 4 - Entender uma execução que falhou e o que fazer (Priority: P2)

Quando a última execução falha, o operador lê em português o que aconteceu e o próximo passo, pode
abrir o detalhe técnico se precisar e pode repetir a execução dali mesmo.

**Why this priority**: Hoje só se vê a exceção em inglês. O operador não sabe se o problema é do
pedido, do SCPI ou do sistema, nem se pode tentar de novo.

**Independent Test**: Com uma execução que falhou por erro inesperado, abrir a página e conferir a
frase em português, o detalhe técnico recolhido e o botão para repetir.

**Acceptance Scenarios**:

1. **Given** a última execução falhou por um erro inesperado, **When** o operador abre a página,
   **Then** lê uma frase em português dizendo que o robô parou por um erro do sistema, quantas
   requisições chegou a processar e que nenhuma linha mudou de estado (quando for o caso).
2. **Given** a falha na tela, **When** o operador abre "Detalhe técnico", **Then** vê o texto original
   do erro e o registro da execução; fechado, o detalhe não aparece.
3. **Given** a falha numa simulação, **When** o operador escolhe "Simular de novo", **Then** uma nova
   simulação começa, com as mesmas regras do botão "Simular".
4. **Given** a falha num lançamento real, **When** o operador olha a falha, **Then** não há atalho
   para repetir o lançamento real ali: ele volta ao botão principal, depois de conferir as travas.
5. **Given** a falha anunciada, **When** um leitor de tela chega à página, **Then** a falha é anunciada
   como alerta, e o estado nunca é indicado só por cor.

---

### User Story 5 - Andamento resumido numa frase (Priority: P2)

O operador entende a última execução lendo uma frase ("Simulação de hoje, 13:25, concluída: 3 de
3 requisições preenchidas") e uma linha com quem iniciou e quanto durou. Só os contadores que não
são zero aparecem. Durante a execução, vê o progresso "requisição N de M" atualizado sozinho.

**Why this priority**: Nove números quase sempre zero escondem o que importa; no celular a seção
vira uma coluna longa.

**Independent Test**: Com uma simulação concluída de 3 requisições, conferir a frase, a duração e
que só o contador "simuladas" aparece; durante uma execução, conferir o progresso.

**Acceptance Scenarios**:

1. **Given** uma simulação concluída de 3 requisições, **When** o operador abre a página, **Then** lê
   a frase com o modo, o momento, a situação e "3 de 3", vê quem iniciou e a duração, e não vê
   contadores zerados.
2. **Given** um lançamento concluído com pendências (1 lançada, 1 para verificar), **When** o
   operador abre a página, **Then** vê os contadores "lançadas" e "para verificar", e um atalho para
   as travas.
3. **Given** uma execução em andamento, **When** o operador acompanha a página, **Then** vê o
   progresso "requisição N de M" e a página se atualiza sozinha até a execução terminar, como hoje.
4. **Given** uma execução interrompida (processo morto), **When** o operador abre a página, **Then**
   a frase diz que a execução foi interrompida, como o selo faz hoje.
5. **Given** a página no celular de 375 px, **When** o operador olha o andamento, **Then** ele ocupa
   no máximo a altura de uma tela, sem rolagem horizontal.

---

### User Story 6 - Histórico que conta o que cada execução fez (Priority: P3)

Na lista das últimas execuções, o operador vê, para cada uma, quantas requisições ela fez (lançou
ou simulou) do total e quanto tempo durou.

**Why this priority**: Melhora de leitura do histórico; não bloqueia nenhuma ação.

**Independent Test**: Com uma simulação de 3 de 3 e um lançamento de 2 de 3 no histórico, conferir
as colunas "Requisições" e "Duração".

**Acceptance Scenarios**:

1. **Given** uma simulação que preencheu 3 de 3 requisições, **When** o operador olha o histórico,
   **Then** a linha mostra "3 de 3" e a duração, e não "Lançadas 0".
2. **Given** um lançamento real com 2 lançadas de 3, **When** o operador olha o histórico, **Then** a
   linha mostra "2 de 3".
3. **Given** uma execução ainda sem fim, **When** o operador olha o histórico, **Then** a duração
   aparece como "—".

---

### User Story 7 - Textos na língua do almoxarifado (Priority: P3)

A página fala em "requisição" onde hoje fala em "lote", usa plural de verdade e não repete o
título; quando não há travas, diz isso numa linha discreta em vez de um cartão vazio.

**Why this priority**: Pequenas fricções de leitura, sem bloqueio.

**Independent Test**: Abrir a página com 1 e com 2 requisições na fila e sem travas, e conferir os
textos.

**Acceptance Scenarios**:

1. **Given** 1 requisição na fila, **When** o operador lê a página, **Then** vê "1 requisição
   aguardando o robô"; com 2, "2 requisições aguardando o robô"; nunca "lote(s)".
2. **Given** a página, **When** o operador olha o cabeçalho, **Then** não há o rótulo "SCPI" repetido
   acima do título "Lançamentos SCPI".
3. **Given** nenhuma trava, **When** o operador olha a página, **Then** vê só a linha "Nenhuma trava
   para conferir", sem o cartão de travas.
4. **Given** um lote travado, **When** o operador olha o cartão da trava, **Then** o identificador
   continua sendo o número do pedido de origem, como hoje.

---

### Edge Cases

- Fila vazia e nenhuma execução registrada: a página diz que não há nada aguardando e que nenhuma
  execução foi feita, sem cartões vazios.
- Execução em andamento quando o operador escolhe "Não lançar": continua valendo a recusa de hoje
  (a resolução só aparece quando o lançamento termina).
- A execução termina enquanto o pedido de confirmação do "Não lançar" está na tela: a confirmação
  não pode ser apagada pela atualização automática da página.
- Fila com muitas requisições (antes da virada, todas as saídas atendidas desde a importação): a
  lista mostra as primeiras e o total, sem deixar a página lenta.
- Execução que falhou antes de saber o total (resumo vazio): a frase não mostra "0 de 0"; diz que
  parou antes de começar.
- Erro técnico muito longo: no detalhe recolhido, ele quebra linha e não cria rolagem horizontal
  na página.
- Simulação e lançamento real no histórico: o modo continua escrito na linha, não só por cor.

## Requirements *(mandatory)*

### Functional Requirements

**Ação principal**

- **FR-001**: A página MUST mostrar em destaque uma única ação: "Simular" enquanto o lançamento real
  estiver bloqueado, e "Lançar no SCPI" quando estiver liberado.
- **FR-002**: Com o lançamento real bloqueado, "Lançar no SCPI" MUST aparecer com um cadeado, MUST
  continuar alcançável pelo teclado e MUST mostrar o motivo do bloqueio por foco, cursor e toque,
  sem enviar nada — o mesmo comportamento do botão do cartão do painel.
- **FR-003**: Com execução em andamento ou fila vazia, os botões MUST NOT iniciar execução, e a
  página MUST dizer o motivo em texto.

**Opções de execução**

- **FR-004**: A escolha entre simular e lançar MUST ser feita só pelos dois botões; a página MUST NOT
  ter um segundo seletor de modo.
- **FR-005**: O limite de requisições MUST ficar à vista junto dos botões ("Só as primeiras [N]
  requisições", vazio = todas) e MUST valer para o botão escolhido, com a mesma validação de hoje.

**Fila do robô**

- **FR-006**: A página MUST listar as requisições que o robô lançaria agora, com número de origem
  (link para o detalhe), data, recebedor, centro de custo e número de materiais.
- **FR-007**: A lista MUST seguir as mesmas regras do robô para decidir o que está na fila: lote
  travado ou já com número de requisição fica de fora.
- **FR-008**: A lista MUST mostrar no máximo 20 requisições e, se houver mais, quantas ficaram de
  fora; o total MUST aparecer sempre.

**Confirmação do "Não lançar"**

- **FR-009**: "Não lançar" MUST pedir confirmação num segundo passo, que diz que a requisição não
  será lançada no SCPI, antes de gravar.
- **FR-010**: Sem JavaScript, "Não lançar" MUST continuar exigindo confirmação explícita.
- **FR-011**: A atualização automática da página MUST NOT apagar uma confirmação ou um formulário de
  resolução que o operador esteja usando.

**Falha da execução**

- **FR-012**: Uma execução que falhou MUST mostrar uma frase em português com o que aconteceu, até
  onde chegou e o próximo passo; o texto técnico do erro e o registro MUST ficar recolhidos num
  "Detalhe técnico".
- **FR-013**: Uma simulação que falhou MUST oferecer "Simular de novo"; um lançamento real que falhou
  MUST NOT oferecer atalho para relançar.
- **FR-014**: A falha MUST ser anunciada a leitores de tela como alerta, e a situação MUST estar
  escrita, não só indicada por cor.

**Andamento**

- **FR-015**: A última execução MUST ser resumida numa frase com modo, momento, situação e
  "N de M requisições", mais quem iniciou e a duração.
- **FR-016**: Só os contadores diferentes de zero MUST aparecer; com algum lote para verificar ou com
  erro, ou com falha de um lançamento real, MUST haver um atalho para as travas. A falha de uma
  simulação sem pendências não leva o atalho: a simulação não muda nenhuma linha.
- **FR-017**: Durante a execução, a página MUST mostrar o progresso "requisição N de M" e continuar
  se atualizando sozinha só enquanto houver execução em andamento.
- **FR-018**: No celular de 375 px, o andamento MUST caber na largura, sem rolagem horizontal.

**Histórico**

- **FR-019**: Cada linha do histórico MUST mostrar o modo, quem iniciou, a situação, "Requisições"
  (lançadas ou simuladas, conforme o modo, do total) e a duração ("—" sem fim).

**Textos**

- **FR-020**: Os textos voltados ao operador MUST usar "requisição" em vez de "lote", com plural
  correto, e MUST NOT repetir "SCPI" num rótulo acima do título. Exceções deliberadas: as
  mensagens de resultado das resoluções ("Lote … marcado para não lançar no SCPI.", FR-022) e o
  registro da execução, escrito pelo robô, continuam como são.
- **FR-021**: Sem travas, a seção de travas MUST se reduzir à linha "Nenhuma trava para conferir".

**Cartão do painel**

- **FR-023**: O cartão de lançamentos do painel MUST contar as requisições aguardando o robô pela
  mesma regra da fila da página (FR-007), mostrando o mesmo número, e MUST dizer "requisição
  aguardando o robô" / "requisições aguardando o robô" / "Nada aguardando o robô.", sem "lote".

**Inalterado**

- **FR-022**: As regras de lançamento, travamento e resolução, o bloqueio do lançamento real até a
  virada, as mensagens de resultado das resoluções e tudo o que é gravado MUST continuar iguais.

### Key Entities *(include if feature involves data)*

- **Requisição na fila**: um lote de linhas de saída pendentes que o robô lançaria como uma
  requisição no SCPI; mostra o número de origem (pedido ou saída avulsa), a data, o recebedor, o
  centro de custo e o número de materiais.
- **Execução do robô**: cada simulação ou lançamento, com quem iniciou, início, fim, situação,
  contadores (requisições, processadas, lançadas, simuladas, falhas, para verificar, ignoradas),
  registro e erro. Nada novo é guardado; a frase, a duração e "N de M" saem do que já existe.
- **Lote travado**: requisição que o robô deixou de fora por precisar de conferência; continua com
  as resoluções de hoje (informar requisição, liberar para relançar, não lançar).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com o lançamento real bloqueado, um operador que nunca viu a página inicia uma
  simulação no primeiro clique, sem tentar o botão bloqueado.
- **SC-002**: O operador diz quais requisições serão lançadas (origem e recebedor) sem sair da
  página, em menos de 10 segundos.
- **SC-003**: Nenhuma requisição sai do lançamento com um único clique: 100% das marcações "Não
  lançar" passam por confirmação.
- **SC-004**: Diante de uma execução que falhou, o operador diz em uma frase o que aconteceu e se
  pode repetir, sem ler texto em inglês.
- **SC-005**: No celular de 375 px, o resumo da última execução cabe numa tela (hoje ocupa cerca de
  duas), sem rolagem horizontal.
- **SC-006**: Nenhuma linha do histórico de simulação mostra "0" quando a simulação preencheu
  requisições.

## Assumptions

- O público é o almoxarifado (contas do painel), no desktop na maior parte do tempo, às vezes no
  celular; a página segue o design system Clean (`docs/DESIGN.md`).
- A falha "You cannot call this from an async context", vista na auditoria, é um defeito do robô
  de lançamento, não da página; corrigi-la fica fora desta funcionalidade. A página só passa a
  explicá-la melhor, como qualquer erro inesperado.
- O limite de 20 requisições na lista da fila é um padrão razoável para a tela; o total sempre
  aparece, e o detalhe de cada uma fica no pedido.
- O texto em português do erro inesperado é genérico ("o robô parou por um erro do sistema"); erros
  conhecidos do SCPI que já chegam em português continuam mostrados como vêm.
- "Simular de novo" usa as mesmas regras do botão "Simular" (trava de uma execução por vez, fila
  vazia não inicia), sem limite.
- O botão do cartão do painel que já explica o bloqueio do lançamento real é a referência de
  comportamento para FR-002.
- Nenhuma mudança de modelo de dados: tudo sai do que as execuções e as linhas de saída já guardam.

# Feature Specification: Página única de automações

**Feature Branch**: `004-pagina-automacoes`

**Created**: 2026-10-15

**Status**: Implementada

**Input**: User description: "quero unir as paginas catalogo e lancamentos scpi em uma só pagina de
gerenciamento de automacoes"

## Contexto

Hoje o almoxarifado acompanha os robôs que falam com o SCPI em duas páginas separadas da área
interna:

- **Catálogo**: a situação dos dados trazidos do SCPI (cadastro de materiais, estoque e saídas),
  o botão "Atualizar agora", a carga inicial completa, o que precisa de conferência, o histórico
  das importações e uma aba por robô de importação (Cadastro, Estoque, Saídas) para rodá-lo com
  parâmetros.
- **Lançamentos SCPI**: o robô que lança no SCPI as saídas atendidas ("Simular" e "Lançar no
  SCPI", com limite de requisições), a fila de requisições aguardando o robô, o andamento da
  execução, as travas para conferir e as últimas execuções.

As duas páginas tratam da mesma coisa para quem opera: robôs que rodam sozinhos ou sob comando,
que podem estar em andamento, falhar ou pedir conferência. Separadas, obrigam o operador a abrir
duas telas para saber se "está tudo bem com os robôs" e espalham pela barra lateral dois destinos
para o mesmo assunto.

Esta funcionalidade junta as duas numa só página, **Automações**, com uma visão geral de todos os
robôs, um histórico único de execuções com filtros e um lugar para cada robô. É uma mudança de organização e de apresentação: o que cada robô faz,
as regras de importação, as travas contra lançar duas vezes no SCPI, o bloqueio do lançamento real
até a virada e o que cada robô grava continuam exatamente como estão.

## Clarifications

### Session 2026-10-15

- Q: O sistema ainda não está em produção: as páginas e os endereços antigos precisam continuar
  funcionando? → A: Não. As páginas Catálogo e Lançamentos SCPI e seus endereços são apagados, sem
  redirecionamento; todos os endereços de Automações, inclusive os das ações, ficam sob a página
  nova. Só os modelos e as regras dos apps de catálogo e de pedidos ficam onde estão.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver de uma vez se os robôs estão bem (Priority: P1)

Ao abrir Automações, o operador vê numa só tela o estado de cada automação: as três importações do
SCPI (cadastro, estoque e saídas) e o lançamento no SCPI. Para cada uma vê se está em dia, em
andamento, com avisos, com falha ou travada, há quanto tempo rodou pela última vez e, quando algo
pede ação, um caminho direto para resolver.

**Why this priority**: É o motivo da união. Hoje responder "algum robô precisa de mim?" exige abrir
duas páginas; com a visão geral, basta uma olhada.

**Independent Test**: Com uma importação de estoque que falhou, uma requisição travada no
lançamento e as demais automações em dia, abrir Automações e conferir que a visão geral mostra as
quatro automações, destaca as duas que pedem ação e leva cada uma ao lugar onde se resolve.

**Acceptance Scenarios**:

1. **Given** as quatro automações em dia, **When** o operador abre Automações, **Then** vê as quatro
   com o estado "em dia" e quando cada uma rodou pela última vez, sem nenhum alerta.
2. **Given** a última importação de estoque com falha, **When** o operador abre Automações, **Then**
   a linha do estoque aparece como falha, com a frase do erro, e oferece "Tentar de novo", que leva
   ao lugar do robô de estoque.
3. **Given** um lote travado no lançamento, **When** o operador abre Automações, **Then** a linha do
   lançamento diz quantas requisições estão para conferir e leva às travas.
4. **Given** requisições aguardando o robô de lançamento, **When** o operador abre Automações,
   **Then** a linha do lançamento mostra quantas aguardam.
5. **Given** qualquer automação em andamento, **When** o operador está na visão geral, **Then** o
   estado dela se atualiza sozinho até terminar, sem recarregar a página.
6. **Given** um estado qualquer, **When** o operador o olha, **Then** o estado é dito em texto (não só
   por cor).

---

### User Story 2 - Operar o lançamento no SCPI dentro de Automações (Priority: P1)

Tudo o que hoje se faz em Lançamentos SCPI continua possível, agora dentro de Automações: simular
ou lançar (com o limite de requisições), ver a fila antes de disparar, acompanhar o andamento,
resolver as travas e consultar as últimas execuções.

**Why this priority**: É o uso diário mais crítico. A união não pode tirar nem dificultar nada do
lançamento, que mexe com o que o sistema não consegue desfazer no SCPI.

**Independent Test**: Em Automações, abrir o lugar do lançamento, simular com uma requisição na
fila, acompanhar até o fim e resolver uma trava; conferir que cada passo dá o mesmo resultado de
hoje.

**Acceptance Scenarios**:

1. **Given** o lançamento real bloqueado e requisições na fila, **When** o operador abre o lançamento
   em Automações, **Then** vê "Simular" como ação principal, "Lançar no SCPI" bloqueado com o motivo,
   o limite de requisições e a fila, como hoje.
2. **Given** uma simulação iniciada, **When** ela roda, **Then** o andamento se atualiza sozinho e,
   ao terminar, a atualização para.
3. **Given** um lote travado, **When** o operador o resolve (informar a requisição, liberar com
   "Conferi no SCPI" ou "Não lançar" com confirmação), **Then** o resultado e as recusas são os de
   hoje e a página continua no lançamento.
4. **Given** uma execução do lançamento em andamento, **When** o operador tenta iniciar outra ou
   resolver uma trava, **Then** é recusado como hoje.

---

### User Story 3 - Rodar e acompanhar as importações do SCPI dentro de Automações (Priority: P1)

Tudo o que hoje se faz em Catálogo continua possível em Automações: "Atualizar agora", a carga
inicial completa (com "Estou ciente"), cada robô de importação com seus parâmetros (baixar do SCPI
ou enviar CSV, modo do cadastro, período das saídas), o que precisa de conferência, os números dos
formulários e o histórico.

**Why this priority**: As importações alimentam os formulários e a curva ABC; perder qualquer
controle delas na mudança seria uma regressão.

**Independent Test**: Em Automações, iniciar "Atualizar agora", acompanhar até o fim, depois enviar
um CSV de estoque pelo robô de estoque; conferir que cada passo dá o mesmo resultado de hoje.

**Acceptance Scenarios**:

1. **Given** nenhuma importação em andamento, **When** o operador escolhe "Atualizar agora", **Then**
   as três importações começam, a página avisa e acompanha o andamento como hoje.
2. **Given** o robô de cadastro aberto com parâmetros preenchidos, **When** uma importação está em
   andamento e a situação se atualiza sozinha, **Then** o que o operador digitou não se perde e o
   botão do robô fica desabilitado até a importação terminar.
3. **Given** parâmetros inválidos num robô de importação, **When** o operador envia, **Then** os erros
   aparecem no próprio robô e a página continua nele.
4. **Given** a carga inicial completa sem "Estou ciente", **When** o operador a envia, **Then** nada
   começa, como hoje.

---

### User Story 4 - Um histórico só, com filtros (Priority: P2)

O histórico deixa de ser dois (o das importações em Catálogo e as últimas execuções em Lançamentos
SCPI) e vira um só, na visão geral, com as execuções de todos os robôs da mais recente para a mais
antiga. O operador filtra por robô, situação e período, e busca por texto, com os mesmos filtros
recolhíveis do painel de pedidos, e cada robô tem um
atalho para o histórico já filtrado por ele.

**Why this priority**: Quando algo deu errado, a pergunta é "o que rodou e quando?", sem importar
qual robô. Com um histórico só, a resposta está num lugar; os filtros evitam que a lista misturada
atrapalhe quem procura um robô específico.

**Independent Test**: Com execuções dos quatro robôs (sucessos, uma falha de estoque e uma
simulação do lançamento), abrir a visão geral, conferir a lista combinada em ordem, filtrar por
"Estoque" e "Falhou" e conferir que só a falha do estoque fica; abrir o endereço com os filtros e
conferir que volta igual.

**Acceptance Scenarios**:

1. **Given** execuções dos quatro robôs, **When** o operador abre a visão geral, **Then** vê no
   histórico as execuções de todos, da mais recente para a mais antiga, cada uma com o robô, o modo
   (no lançamento: simulação ou lançamento real; no cadastro: só os novos ou recarga completa), o
   início, a duração, a situação em texto e o resumo.
2. **Given** o histórico, **When** o operador escolhe o robô "Estoque", **Then** só aparecem
   execuções do estoque, e a lista diz que está filtrada e quantas encontrou.
3. **Given** o histórico, **When** o operador escolhe a situação "Falhou" (ou "Com avisos",
   "Interrompida", "Em andamento", "Concluída"), **Then** só aparecem execuções nessa situação;
   robô e situação se combinam.
4. **Given** o histórico, **When** o operador o usa, **Then** os filtros se comportam como os do
   painel de pedidos: uma barra com a busca, o botão "Filtros" com a contagem dos ativos, que abre e
   fecha o painel com robô, situação e período (lembrado no aparelho), "Limpar filtros" e, com o
   painel fechado, um chip por filtro ativo que o remove; a lista se atualiza ao mudar um filtro,
   sem recarregar a página.
5. **Given** filtros escolhidos, **When** o operador copia o endereço ou recarrega a página, **Then**
   o histórico volta com os mesmos filtros.
6. **Given** filtros que não acham nada, **When** o operador olha o histórico, **Then** lê que nenhuma
   execução corresponde e tem como limpar os filtros num passo.
7. **Given** a aba de um robô (por exemplo, Lançamento no SCPI), **When** o operador escolhe "Ver
   histórico", **Then** chega ao histórico da visão geral já filtrado por esse robô.
8. **Given** uma execução que falhou no histórico, **When** o operador a olha, **Then** vê a frase do
   erro e pode abrir o detalhe técnico, como hoje.
9. **Given** mais execuções do que a lista mostra, **When** o operador chega ao fim dela, **Then** pode
   ver as seguintes, mantendo os filtros.

---

### User Story 5 - Links internos levam direto a Automações (Priority: P2)

Os links de outras telas que hoje levam a Catálogo ou a Lançamentos SCPI (atalhos do painel, link
de resolução no detalhe do pedido) passam a levar direto ao lugar certo em Automações.

**Why this priority**: As páginas antigas deixam de existir; um link interno esquecido daria em
página não encontrada.

**Independent Test**: No painel, seguir o atalho "para conferir" do lançamento e o link do catálogo;
no detalhe de um pedido com lote travado, seguir o link de resolução; conferir que cada um abre a
aba certa de Automações.

**Acceptance Scenarios**:

1. **Given** o painel com o atalho "para conferir" do lançamento, **When** o operador o segue,
   **Then** chega à aba do lançamento em Automações.
2. **Given** o painel com o link do catálogo, **When** o operador o segue, **Then** chega à visão
   geral de Automações.
3. **Given** o detalhe de um pedido com lote travado, **When** o operador segue o link de resolução,
   **Then** chega às travas na aba do lançamento.
4. **Given** os endereços antigos de Catálogo e de Lançamentos SCPI, **When** alguém os abre,
   **Then** recebe "página não encontrada" (as páginas foram apagadas).

---

### User Story 6 - Um destino só na barra lateral (Priority: P2)

A barra lateral passa a ter um item "Automações" no lugar de "Catálogo" e "Lançamentos SCPI". O
item fica marcado como atual em qualquer lugar dentro de Automações.

**Why this priority**: Menos destinos para o mesmo assunto deixa a navegação mais curta, mas o valor
principal já vem das histórias anteriores.

**Independent Test**: Abrir a área interna e conferir os itens da barra lateral e a marcação de
item atual dentro de Automações.

**Acceptance Scenarios**:

1. **Given** o operador logado, **When** olha a barra lateral, **Then** vê "Automações" e não vê mais
   "Catálogo" nem "Lançamentos SCPI"; "Curva ABC" continua no seu lugar.
2. **Given** o operador no lançamento ou num robô de importação, **When** olha a barra lateral,
   **Then** "Automações" aparece como o item atual.

---

### Edge Cases

- Uma importação e o lançamento em andamento ao mesmo tempo: a visão geral mostra os dois em
  andamento e cada um se atualiza; terminar um não interrompe o acompanhamento do outro.
- Execução interrompida (processo morto, janela fechada à força): aparece como interrompida na
  visão geral e no lugar do robô, e libera os botões, como hoje.
- Nenhuma importação nem execução ainda (banco recém-criado): a visão geral diz isso para cada
  automação e oferece o primeiro passo, sem erro.
- Operador sem JavaScript: todas as partes de Automações continuam alcançáveis por links e os
  formulários continuam enviando; a troca de lugar sem recarregar é só um conforto.
- Celular estreito (375 px): a visão geral e os lugares de cada robô cabem sem rolagem horizontal da
  página.
- Endereço de Automações com uma aba que não existe: abre a visão geral.
- Filtro que não acha nada, ou endereço com um valor de filtro que não existe: o histórico diz que
  nada corresponde (ou ignora o valor desconhecido) e oferece limpar os filtros, sem erro.
- Uma execução em andamento no histórico: aparece no topo como "Em andamento" e muda de situação
  quando termina, sem mexer nos filtros escolhidos.
- Envio de formulário de um robô que volta com erro: a página abre de novo no robô que o enviou, não
  na visão geral.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A área interna DEVE ter uma página Automações que reúne tudo o que hoje está nas
  páginas Catálogo e Lançamentos SCPI.
- **FR-002**: Automações DEVE abrir numa visão geral com uma linha por automação: importação do
  cadastro, do estoque, das saídas e lançamento no SCPI.
- **FR-003**: Cada linha da visão geral DEVE mostrar, em texto, o estado da automação (em dia, em
  andamento, com avisos, falhou, interrompida; "sem dados" na importação que nunca rodou e "sem
  execuções" no lançamento que nunca rodou; no lançamento, também quantas requisições
  aguardam e quantas estão para conferir) e quando ela rodou pela última vez.
- **FR-004**: Cada linha que pede ação DEVE oferecer um caminho direto para o lugar onde a ação se
  faz (tentar a importação de novo, conferir as travas).
- **FR-005**: A visão geral DEVE manter as ações gerais do catálogo que hoje ficam na aba Situação:
  "Atualizar agora", a carga inicial completa recolhida com "Estou ciente", o que precisa de
  conferência e os números dos formulários.
- **FR-006**: Automações DEVE ter um lugar próprio para o lançamento no SCPI, com tudo o que a página
  Lançamentos SCPI tem hoje (ações, limite, fila, andamento e travas com suas resoluções), com o
  mesmo comportamento; as últimas execuções passam para o histórico combinado (FR-017).
- **FR-007**: Automações DEVE ter um lugar próprio para cada robô de importação (cadastro, estoque,
  saídas), com os mesmos parâmetros, validações e avisos de hoje.
- **FR-008**: Cada lugar DEVE ter um endereço próprio, que pode ser aberto direto, guardado como
  favorito e usado como destino de link.
- **FR-009**: Enquanto qualquer automação estiver em andamento, o que mostra o estado dela DEVE se
  atualizar sozinho e parar ao terminar; a atualização NÃO PODE apagar o que o operador digitou num
  formulário.
- **FR-010**: Depois de enviar um formulário (iniciar, importar, resolver), o operador DEVE voltar ao
  mesmo lugar de onde enviou, com o aviso do resultado.
- **FR-011**: As páginas Catálogo e Lançamentos SCPI e todos os seus endereços (páginas e ações)
  DEVEM ser apagados, sem redirecionamento; as ações passam a ter endereço sob Automações.
- **FR-012**: Os links internos que hoje apontam para Catálogo ou Lançamentos SCPI (atalhos do painel,
  detalhe do pedido) DEVEM apontar direto para o lugar equivalente em Automações.
- **FR-013**: A barra lateral DEVE trocar "Catálogo" e "Lançamentos SCPI" por um único item
  "Automações", marcado como atual em todos os lugares de Automações.
- **FR-014**: A página DEVE exigir login, como as duas páginas de hoje.
- **FR-015**: As regras de cada robô NÃO PODEM mudar: o que cada importação grava e recusa, uma
  execução de cada robô por vez, as travas contra lançar duas vezes no SCPI e o bloqueio do
  lançamento real até a virada continuam como estão.
- **FR-016**: A Curva ABC continua uma página própria, fora de Automações.
- **FR-017**: A visão geral DEVE ter um histórico único com as execuções de todos os robôs
  (importações do cadastro, do estoque e das saídas, carga inicial, carga dos pares de/para da
  planilha e lançamento no SCPI, simulado ou real), da mais recente para a mais antiga, no lugar dos dois históricos de hoje.
- **FR-018**: Cada execução no histórico DEVE mostrar o robô, o modo, o início, a duração, a
  situação em texto e o resumo; a que falhou, também a frase do erro com o detalhe técnico
  recolhido.
- **FR-019**: O histórico DEVE usar o mesmo padrão de filtros do painel de pedidos (busca por texto
  no erro, nos avisos e no registro da execução; filtros recolhíveis por robô, situação e período, com contagem dos ativos,
  chips com o painel fechado e "Limpar filtros"; lista atualizada ao mudar um filtro), combináveis e
  dizendo quantas execuções acharam.
- **FR-020**: Os filtros do histórico DEVEM ficar no endereço da página, para recarregar, guardar e
  compartilhar a lista filtrada, e DEVEM funcionar sem JavaScript.
- **FR-021**: O histórico DEVE mostrar as execuções mais recentes e permitir ver as seguintes,
  mantendo os filtros.
- **FR-022**: Cada aba de robô DEVE ter um atalho "Ver histórico" que abre o histórico filtrado por
  esse robô.

### Key Entities

- **Automação**: um robô que o almoxarifado acompanha (importação do cadastro, do estoque, das
  saídas; lançamento no SCPI). Tem estado atual, última execução e, quando pede ação, um caminho
  para resolver. Não é um dado novo: é como a página apresenta as importações e execuções que já
  são registradas hoje.
- **Execução**: cada vez que uma automação rodou, com robô, modo, situação, início, fim, resumo e
  erro. Já existe hoje em dois registros (importações e execuções do robô de lançamento); o
  histórico combinado os mostra juntos, sem criar um registro novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Saber se alguma automação pede ação exige abrir uma página só, em vez de duas.
- **SC-002**: A partir da visão geral, o operador chega ao lugar onde resolve um problema apontado
  com um clique.
- **SC-003**: 100% das ações que existiam em Catálogo e Lançamentos SCPI continuam disponíveis em
  Automações, com o mesmo resultado (conferido pela suíte de testes atual das duas páginas, adaptada
  aos novos endereços).
- **SC-004**: Nenhum link interno do sistema leva a uma página que não existe mais.
- **SC-005**: A barra lateral tem um destino a menos.
- **SC-006**: Em celular de 375 px, nenhuma parte de Automações tem rolagem horizontal da página.
- **SC-007**: Achar a última falha de qualquer robô exige abrir uma página e escolher no máximo dois
  filtros.

## Assumptions

- O nome do destino e da página é "Automações", como o usuário pediu; o título da página e o item da
  barra lateral usam esse nome.
- Os lugares dentro de Automações seguem o padrão de abas que a página Catálogo já usa: "Visão
  geral", "Lançamento no SCPI", "Cadastro", "Estoque" e "Saídas", nessa ordem (o lançamento vem logo
  depois da visão geral por ser o uso diário mais crítico). Selo de atenção na aba, como hoje.
- A visão geral é o lugar de entrada; não há preferência lembrada de qual aba abrir.
- "Atualizar agora", a carga inicial completa, "Para conferir" (avisos do catálogo), os números dos
  formulários e o histórico combinado ficam na visão geral. As travas do lançamento ficam no lugar
  do lançamento, com um resumo (quantas para conferir) na visão geral.
- O padrão de filtros é o do painel de pedidos, sem variação própria: o operador já o conhece, e o
  estado aberto ou fechado do painel de filtros é lembrado no aparelho como lá.
- O período filtra pelo início da execução.
- O histórico mostra 20 execuções por vez. A carga inicial completa e o "Atualizar agora" aparecem
  como as importações que disparam (uma linha por robô), como já são registrados hoje.
- As situações do filtro juntam as dos dois registros de hoje num vocabulário só: Concluída, Com
  avisos, Falhou, Interrompida e Em andamento (a simulação concluída conta como Concluída).
- O cartão de atalhos do painel (lançar dali mesmo, "para conferir") continua no painel; só passa a
  apontar para Automações.
- O acesso é o mesmo de hoje: qualquer usuário logado da área interna.
- Os robôs rodados pelo Agendador de Tarefas aparecem na visão geral pelas execuções que registram,
  como hoje; agendar ou mudar horários pela página está fora do escopo.
- O sistema ainda não está em produção: ninguém depende dos endereços antigos, então não há
  redirecionamento nem período de transição.

# Feature Specification: Clareza e facilidade de uso dos formulários públicos de pedido

**Feature Branch**: `002-formularios-publicos-clareza`

**Created**: 2026-10-13

**Status**: Implementada

**Input**: User description: "quero aplicar tudo" — aplicar as 11 propostas da revisão de
usabilidade dos formulários públicos de pedido de materiais (início, formulário de limpeza,
formulário AB e tela de sucesso).

## Contexto

Os funcionários pedem materiais ao almoxarifado por dois formulários públicos, quase sempre no
celular: o de limpeza, copa/cozinha e escritório e o de "Materiais AB". Uma revisão feita no
navegador (celular de 375 px e desktop) achou pontos que travam ou confundem quem pede:

- no celular, a gaveta "Seu pedido" não tem como enviar; o botão de envio fica no fim da página;
- os erros de envio só aparecem numa caixa no topo, e os campos com problema não ficam marcados;
- a página inicial fala em "Formulário 1/2" e "Materiais AB", termos que o funcionário não conhece;
- nome e destino são digitados de novo a cada pedido;
- sair da página (trocar de formulário, voltar no celular) apaga o pedido sem aviso;
- detalhes menores na busca, no carrinho, na indicação de campo obrigatório e na tela de sucesso.

Esta funcionalidade muda só a apresentação e o comportamento da tela. As regras de negócio, os
textos das mensagens de erro, os limites anti-abuso e o que é gravado no pedido continuam iguais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enviar o pedido pela gaveta no celular (Priority: P1)

No celular, o funcionário busca e adiciona materiais, abre "Seu pedido" pela barra fixa no rodapé,
confere as quantidades e envia dali mesmo, sem ter que fechar a gaveta e procurar o botão no fim
da página.

**Why this priority**: É o ponto em que o funcionário mais se perde: monta o pedido e não acha
como terminá-lo. A maioria dos pedidos é feita no celular.

**Independent Test**: No celular, com nome e destino preenchidos, adicionar um material, abrir
a gaveta e enviar por ela; o pedido é registrado e a tela de sucesso aparece.

**Acceptance Scenarios**:

1. **Given** o formulário aberto no celular com um material no pedido, **When** o funcionário abre
   a gaveta, **Then** ela mostra "Enviar pedido" como ação principal e "Adicionar mais materiais"
   como ação secundária.
2. **Given** a gaveta aberta e nome e destino preenchidos, **When** o funcionário toca em "Enviar
   pedido", **Then** o pedido é enviado e a tela de sucesso aparece.
3. **Given** a gaveta aberta e o nome em branco, **When** o funcionário toca em "Enviar pedido",
   **Then** a gaveta fecha, a página mostra os erros (User Story 2) e nada é registrado.
4. **Given** o pedido com 2 materiais, **When** o funcionário olha a barra fixa, **Then** ela mostra
   a quantidade de materiais e a ação "Revisar e enviar".
5. **Given** o pedido vazio, **When** o funcionário olha a barra fixa, **Then** ela diz que nenhum
   material foi adicionado e não convida a "ver" um pedido vazio.

---

### User Story 2 - Ver cada erro junto do campo (Priority: P1)

Quando o envio é recusado, o funcionário vê no topo um resumo com o que falta, cada item levando
ao campo, e vê a mensagem embaixo do próprio campo, que fica destacado.

**Why this priority**: Hoje, no celular, quem rola até o campo já não vê o erro; o funcionário
reenvia sem entender por que não foi. Junto com a User Story 1, fecha o caminho do envio.

**Independent Test**: Enviar sem nome e com destino fora da lista e conferir o resumo no topo,
as mensagens embaixo dos dois campos e os campos marcados.

**Acceptance Scenarios**:

1. **Given** nome em branco e destino vazio, **When** o pedido é enviado, **Then** o resumo no topo
   diz quantos problemas há e lista "Nome completo" e "Destino", e cada campo mostra embaixo a
   mesma mensagem de hoje ("Informe o nome completo.", "Escolha o destino dos materiais na lista
   de centros de custo.").
2. **Given** o resumo de erros na tela, **When** o funcionário toca num item do resumo, **Then** a
   página vai até o campo e o põe em foco.
3. **Given** um envio recusado, **When** a resposta aparece, **Then** o foco vai para o resumo,
   para que leitores de tela anunciem os erros.
4. **Given** um erro de material (quantidade inválida, sem estoque, fora do catálogo), **When** o
   pedido é recusado, **Then** a mensagem aparece no resumo e a linha do material no pedido fica
   marcada "Corrigir", como hoje.
5. **Given** o campo nome com erro, **When** o funcionário o preenche, **Then** o destaque de erro
   daquele campo some sem precisar reenviar.

---

### User Story 3 - Escolher o formulário certo pela página inicial (Priority: P2)

Na página inicial, o funcionário entende pelo título e pelos exemplos qual formulário tem o que
ele procura.

**Why this priority**: Escolher o formulário errado faz o funcionário procurar um material que não
está ali e desistir ou ligar para o almoxarifado. Não impede o envio, por isso P2.

**Independent Test**: Abrir a página inicial e conferir que nenhum cartão usa "Formulário 1/2" nem
"AB", e que cada cartão traz exemplos de materiais.

**Acceptance Scenarios**:

1. **Given** a página inicial, **When** o funcionário a abre, **Then** cada cartão mostra um título
   pelo conteúdo e de 3 a 4 exemplos de materiais, sem "Formulário 1" ou "Formulário 2".
2. **Given** o cartão do formulário AB, **When** o funcionário o lê, **Then** o título é "Ferramentas,
   peças e materiais".
3. **Given** um dos formulários aberto, **When** o funcionário olha o título da página, **Then** ele
   repete o título do cartão escolhido.

---

### User Story 4 - Nome e destino lembrados no aparelho (Priority: P2)

Quem pede com frequência abre o formulário e encontra nome e destino já preenchidos com os do
último pedido feito naquele aparelho, e pode limpá-los se não for a mesma pessoa.

**Why this priority**: Poupa o trecho mais trabalhoso do formulário (o destino tem cerca de 385
opções) para quem pede toda semana.

**Independent Test**: Enviar um pedido, abrir o formulário de novo no mesmo navegador e conferir
nome e destino preenchidos; tocar em "Não é você?" e conferir os campos vazios.

**Acceptance Scenarios**:

1. **Given** um pedido enviado com sucesso neste aparelho, **When** o funcionário abre qualquer um
   dos dois formulários, **Then** nome e destino vêm preenchidos com os desse pedido.
2. **Given** nome e destino lembrados, **When** o funcionário toca em "Não é você? Limpar",
   **Then** os dois campos ficam vazios e o aparelho deixa de lembrá-los.
3. **Given** um envio recusado, **When** o funcionário abre o formulário de novo depois, **Then**
   nada novo foi lembrado (só pedido registrado atualiza o que fica salvo).
4. **Given** o destino lembrado deixou de existir no cadastro, **When** o formulário abre, **Then**
   o destino vem vazio e o nome continua preenchido.
5. **Given** a tela de sucesso, **When** o funcionário toca em "Fazer outro pedido", **Then** o novo
   formulário já vem com o mesmo nome e destino.

---

### User Story 5 - Não perder o pedido sem querer (Priority: P2)

Se o funcionário tenta sair da página com materiais no pedido, o navegador pergunta antes.

**Why this priority**: O pedido em montagem não é guardado em lugar nenhum; perdê-lo obriga a
buscar tudo de novo.

**Independent Test**: Adicionar um material e tocar em "Trocar tipo de material"; o navegador pede
confirmação. Com o pedido vazio, sai direto.

**Acceptance Scenarios**:

1. **Given** um material no pedido, **When** o funcionário tenta sair da página (link, voltar,
   fechar), **Then** o navegador pede confirmação.
2. **Given** o pedido vazio, **When** o funcionário sai da página, **Then** não há confirmação.
3. **Given** o pedido enviado com sucesso, **When** o funcionário sai da tela de sucesso, **Then** não
   há confirmação.

---

### User Story 6 - Campos e destino mais simples (Priority: P3)

O funcionário entende sem esforço o que é obrigatório e o que pôr no destino.

**Why this priority**: Melhora de leitura, sem bloqueio real.

**Independent Test**: Abrir o formulário e conferir: sem asteriscos, "Observações (opcional)", e a
explicação longa do destino recolhida.

**Acceptance Scenarios**:

1. **Given** o formulário, **When** o funcionário o lê, **Then** só o campo opcional é marcado
   "(opcional)" e não há asteriscos sem legenda.
2. **Given** o campo destino vazio, **When** o funcionário o olha, **Then** vê uma dica curta
   ("setor, viatura ou placa") e um "O que pôr aqui?" que, tocado, mostra a explicação completa.

---

### User Story 7 - Busca e carrinho mais claros (Priority: P3)

Na busca, o funcionário vê primeiro o que pode pedir, entende o estoque e a unidade, e tem retorno
claro ao adicionar; o carrinho e os resultados não mostram códigos internos ao público.

**Why this priority**: Pequenas fricções somadas; nenhuma impede o pedido.

**Independent Test**: No formulário AB, buscar "luva" e conferir a ordem, os textos de estoque e
unidade e o retorno do botão ao adicionar.

**Acceptance Scenarios**:

1. **Given** uma busca com materiais com e sem estoque, **When** os resultados aparecem, **Then** os
   que podem ser pedidos vêm primeiro e os sem estoque vêm no fim, ainda com o selo "Sem estoque".
2. **Given** um material com 356 UN em estoque no formulário AB, **When** aparece nos resultados,
   **Then** lê-se "356 UN disponíveis".
3. **Given** um resultado, **When** o funcionário o lê, **Then** a unidade aparece só embaixo do
   nome (no AB, junto do estoque), e a linha da quantidade e do "Adicionar" cabe no painel.
4. **Given** o toque em "Adicionar", **When** o material entra no pedido, **Then** o botão mostra
   "Adicionado" em destaque verde por cerca de 2 segundos e volta a "Adicionar".
5. **Given** o pedido num formulário público, **When** o funcionário o confere, **Then** não aparece
   o código do material (CADPRO), só nome, quantidade e unidade.
6. **Given** um resultado num formulário público, **When** o funcionário o olha, **Then** vê só o
   botão "Adicionar"; **When** toca nele, **Then** a quantidade abre (em 1, com o campo em foco),
   com "Confirmar" e um ✕ para cancelar, e só uma quantidade fica aberta por vez.
7. **Given** a quantidade aberta, **When** o funcionário confirma (botão ou Enter), **Then** o
   material entra no pedido e a quantidade fecha; com erro (ex.: acima do estoque), ela continua
   aberta e o motivo aparece no pedido. Esc ou o ✕ fecham sem adicionar.
8. **Given** um material já no pedido, **When** o funcionário toca em "Alterar", **Then** a
   quantidade abre com a do pedido e "Atualizar" a substitui (não soma).
9. **Given** um material no pedido (gaveta ou coluna "Seu pedido"), **When** o funcionário olha a
   linha, **Then** vê a quantidade como texto, com "Alterar" e "Remover"; **When** toca em
   "Alterar", **Then** o − / + abre com "Confirmar" e ✕, e nada vai ao servidor até confirmar; o ✕
   ou o Esc voltam ao valor anterior sem fechar a gaveta.

---

### User Story 8 - Página pública mais limpa e sucesso conferível (Priority: P3)

O cabeçalho público não chama o funcionário para a área interna, e a tela de sucesso lista o que
foi pedido.

**Why this priority**: Acabamento.

**Independent Test**: Conferir o cabeçalho público sem o link "Área do almoxarifado" e a tela de
sucesso com a lista de materiais.

**Acceptance Scenarios**:

1. **Given** uma página pública, **When** o funcionário a abre, **Then** o cabeçalho não tem o link
   "Área do almoxarifado", que continua no rodapé.
2. **Given** um pedido registrado, **When** a tela de sucesso aparece, **Then** ela mostra, além do
   número, a lista de materiais com quantidade e unidade, o destino, e o mesmo aviso de que a
   saída só é registrada no atendimento.
3. **Given** um reenvio do mesmo pedido, **When** a tela de sucesso aparece, **Then** ela mostra a
   mesma lista do pedido já registrado.

---

### Edge Cases

- Sem JavaScript: a gaveta não existe; o pedido aparece na página com o botão de envio no fim,
  como hoje. Nome e destino não são lembrados e não há confirmação ao sair; o resto funciona.
- Navegador que não deixa guardar dados (aba anônima, armazenamento bloqueado): o formulário abre
  vazio, sem erro, e "Não é você?" não aparece.
- Aparelho compartilhado: o nome lembrado é visível a quem abrir o formulário depois; o "Não é
  você? Limpar" é a saída. Nenhum dado além de nome e destino é lembrado.
- Envio divergente (mesmo identificador, conteúdo diferente): o botão "Já conferi com o
  almoxarifado — enviar como novo pedido" aparece também na gaveta, no lugar de "Enviar pedido".
- Limite de envios por IP ou por nome atingido: a mensagem continua no resumo do topo, sem campo
  associado.
- Erro que não pertence a um campo nem a um material (pedido vazio, limite de itens): fica só no
  resumo.
- Desktop (pedido na coluna ao lado): o botão de envio continua no cartão "Seu pedido"; os erros
  por campo valem igual.
- Saída da página pelo próprio envio do formulário ou pelos links da tela de sucesso não pede
  confirmação.
- Busca que só acha materiais sem estoque: a lista mostra todos, com o selo, sem botão Adicionar.
- Formulário indisponível (catálogo ou estoque não carregou): mantém o aviso de hoje; nada é
  lembrado nem pedido.

## Requirements *(mandatory)*

### Functional Requirements

**Envio no celular**

- **FR-001**: A gaveta "Seu pedido" do celular DEVE ter "Enviar pedido" como ação principal e
  "Adicionar mais materiais" como ação secundária (que fecha a gaveta).
- **FR-002**: Enviar pela gaveta DEVE enviar o formulário inteiro (nome, destino, observações e
  materiais), exatamente como o botão do fim da página.
- **FR-003**: Se o envio pela gaveta for recusado, a gaveta DEVE fechar e a página DEVE mostrar os
  erros como na FR-005.
- **FR-004**: A barra fixa do celular DEVE mostrar o número de materiais e a ação "Revisar e
  enviar"; com o pedido vazio, DEVE dizer que nenhum material foi adicionado, sem a ação.

**Erros**

- **FR-005**: Envio recusado DEVE mostrar no topo um resumo com o número de problemas e um item
  por problema; o item de um problema de campo DEVE levar ao campo e pô-lo em foco.
- **FR-006**: Erros de nome e de destino DEVEM aparecer também embaixo do próprio campo, que DEVE
  ficar destacado e ser anunciado como inválido a leitores de tela.
- **FR-007**: Depois de um envio recusado, o foco DEVE ir para o resumo de erros.
- **FR-008**: Os textos das mensagens de erro DEVEM ser os mesmos de hoje.
- **FR-009**: O destaque de erro de um campo DEVE sumir quando o funcionário altera esse campo.
- **FR-010**: O destaque de erro não pode ser só cor: DEVE ter ícone e texto.

**Página inicial e títulos**

- **FR-011**: A página inicial DEVE trocar "Formulário 1/2" por títulos pelo conteúdo, com 3 a 4
  exemplos de materiais em cada cartão.
- **FR-012**: O formulário AB DEVE se chamar "Ferramentas, peças e materiais" em todas as telas
  públicas (cartão, título e título da aba do navegador). O nome interno usado pelo almoxarifado
  (painel, detalhe do pedido, recibos) e o endereço do formulário não mudam.
- **FR-013**: O formulário de limpeza DEVE se chamar "Limpeza, copa e escritório" nas telas
  públicas.

**Dados lembrados**

- **FR-014**: Depois de um pedido registrado, o aparelho DEVE lembrar nome e destino desse pedido,
  e só eles.
- **FR-015**: Ao abrir qualquer formulário público, nome e destino lembrados DEVEM vir preenchidos;
  destino lembrado que não está mais na lista DEVE ficar vazio.
- **FR-016**: Com dados lembrados, o formulário DEVE oferecer "Não é você? Limpar", que esvazia os
  campos e esquece os dados.
- **FR-017**: Se o aparelho não deixar guardar dados, o formulário DEVE funcionar como hoje, sem
  mensagem de erro.

**Saída da página**

- **FR-018**: Com ao menos um material no pedido, sair da página DEVE pedir confirmação do
  navegador; sem material, ao enviar ou na tela de sucesso, não.

**Campos**

- **FR-019**: Os campos obrigatórios DEVEM ficar sem asterisco, e o campo de observações DEVE ser
  rotulado "(opcional)".
- **FR-020**: O campo destino DEVE ter uma dica curta visível e a explicação completa recolhida
  num "O que pôr aqui?" que abre ao toque e funciona sem JavaScript.

**Busca e carrinho**

- **FR-021**: Os resultados DEVEM listar primeiro os materiais que podem ser pedidos e depois os
  bloqueados, mantendo a ordem atual dentro de cada grupo.
- **FR-022**: No formulário AB, o estoque DEVE aparecer como "<quantidade> <unidade>
  disponíveis".
- **FR-023**: A unidade do material DEVE aparecer só embaixo do nome, nunca ao lado do controle de quantidade nos
  resultados.
- **FR-024**: Ao adicionar um material, o botão DEVE mostrar "Adicionado" em destaque verde, sem
  ícone (o botão tem largura fixa para a linha não mudar de altura; o texto dá o estado, não só a
  cor), por cerca de 2 segundos e voltar a "Adicionar"; a mudança DEVE ser anunciada a leitores de tela.
- **FR-030**: Nos formulários públicos, adicionar DEVE ter dois passos: "Adicionar" abre a quantidade
  do material (uma aberta por vez, em foco), que se confirma ("Confirmar", ou "Atualizar" quando o
  material já está no pedido, que substitui a quantidade) ou se cancela (✕ ou Esc). Sem JavaScript,
  a quantidade e o botão de adicionar ficam à vista. A saída avulsa adiciona direto, como hoje.
- **FR-031**: Nos formulários públicos, a quantidade de cada linha do pedido DEVE seguir o mesmo
  padrão: texto com "Alterar", que abre o − / + com "Confirmar" (só então a alteração vai ao
  servidor) e ✕/Esc (volta ao valor anterior). Uma alteração aberta e não confirmada não vale no
  envio do pedido. Sem JavaScript, o − / + fica à vista; na saída avulsa, cada mudança vai direto.
- **FR-025**: O carrinho dos formulários públicos NÃO DEVE mostrar o código do material; a saída
  avulsa (área interna) continua mostrando.

**Cabeçalho e sucesso**

- **FR-026**: O cabeçalho das páginas públicas NÃO DEVE ter o link "Área do almoxarifado"; o
  rodapé mantém o link.
- **FR-027**: A tela de sucesso DEVE listar os materiais registrados (nome, quantidade e unidade)
  e o destino, além do número e dos avisos de hoje, também num reenvio.

**Restrições**

- **FR-028**: Nada desta funcionalidade pode mudar regras de validação, limites anti-abuso,
  numeração, o que é gravado no pedido nem o aviso ao almoxarifado.
- **FR-029**: A saída avulsa (área interna), que usa a mesma busca e o mesmo carrinho, DEVE
  continuar como hoje, salvo a ordem dos resultados (FR-021), a unidade só embaixo do nome
  (FR-023) e o retorno do botão Adicionar (FR-024).

### Key Entities

- **Dados lembrados do solicitante**: nome e destino do último pedido registrado, guardados só no
  aparelho de quem pediu; nunca no servidor, nunca compartilhados entre aparelhos.
- **Erro de envio**: mensagem de recusa associada a um campo (nome, destino), a um material ou ao
  pedido como um todo; decide onde a mensagem aparece.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No celular, um funcionário que já adicionou materiais chega ao envio a partir da
  gaveta com 1 toque, sem rolar a página.
- **SC-002**: Depois de um envio recusado, todos os campos com problema ficam identificados na
  própria tela, e cada um é alcançado com 1 toque a partir do resumo.
- **SC-003**: Num segundo pedido feito no mesmo aparelho, o funcionário preenche nome e destino em
  0 toques.
- **SC-004**: Em teste com 5 funcionários que não conhecem o sistema, ao menos 4 escolhem na página
  inicial o formulário certo para um material dado (ex.: "fita veda-rosca") na primeira tentativa.
- **SC-005**: Nenhuma página pública mostra "Formulário 1", "Formulário 2" ou "AB" ao funcionário.
- **SC-006**: Nenhum pedido em montagem é perdido por sair da página sem confirmação.
- **SC-007**: As telas mudadas continuam utilizáveis só pelo teclado e com leitor de tela, e o
  envio continua funcionando sem JavaScript.

## Assumptions

- O nome público do formulário AB é "Ferramentas, peças e materiais", proposto na revisão; o
  João pode trocar o texto sem mudar o restante da spec. Os exemplos de cada cartão são tirados
  dos materiais mais pedidos de cada catálogo.
- Lembrar nome e destino no aparelho é aceitável mesmo em aparelhos compartilhados, porque são
  dados que o funcionário já vê nas sugestões do campo nome; o "Não é você? Limpar" cobre a troca
  de pessoa. Nada é lembrado no servidor.
- Os códigos de material deixam de aparecer no carrinho público para combinar com a busca pública,
  que já os esconde; o almoxarifado continua vendo os códigos no painel.
- O botão de envio do fim da página só aparece sem JavaScript; com JavaScript o envio é pela gaveta
  (celular) ou pelo cartão "Seu pedido" (desktop). Ele continua na página, escondido, porque a
  gaveta envia por meio dele (decisão do João na revisão).
- O design system Clean (`docs/DESIGN.md`) continua valendo: só tema claro, ícones do conjunto
  atual, fontes locais.
- O trabalho atual da branch `feat/busca-rola-celular` (folga da busca no celular) é integrado antes
  desta funcionalidade; a posição do painel de resultados não faz parte desta spec.

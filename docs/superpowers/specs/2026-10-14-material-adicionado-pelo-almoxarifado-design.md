# Material adicionado pelo almoxarifado no atendimento — design

Data: 2026-10-14 · Situação: implementada

## 1. Objetivo

No atendimento de um pedido, o almoxarifado passa a poder acrescentar materiais, sem perder o
registro do que o solicitante pediu. Serve para dois casos:

- **Troca:** o solicitante pediu o material errado. O errado fica com 0 entregue e o almoxarifado
  acrescenta o certo, "no lugar de" o errado.
- **Acréscimo:** o material não estava nas listas dos formulários e veio na observação do pedido
  (ou o almoxarifado entrega um a mais). Ele só é acrescentado, sem substituir nenhum.

**Sucesso:**
- o que o solicitante pediu continua gravado como foi pedido, para sempre;
- o que o almoxarifado acrescentou fica separado e marcado como tal, na tela, no recibo e no banco;
- cada material acrescentado com quantidade maior que zero vira uma `LinhaSaida` no mesmo lote, e o
  robô do SCPI lança sem mudança nenhuma;
- nunca sai para o SCPI uma linha com quantidade menor ou igual a zero;
- a suíte segue verde.

### Decisões tomadas

| Tema | Decisão |
|---|---|
| Vínculo "no lugar de" | **Opcional.** A troca começa no material errado ("Trocar") e grava o vínculo; "Adicionar material" acrescenta sem vínculo. |
| Catálogo da busca | **O da saída avulsa** (`catalogo_de(AVULSA)`), com a mesma busca, os mesmos bloqueios e as mesmas regras de quantidade da saída avulsa. |
| Quando acontece | Só no atendimento, enquanto o pedido está aguardando. Depois de confirmado, nada muda (como hoje). |
| Estado no servidor | Nenhum até o envio: os acrescentados vivem em campos do formulário (como o carrinho) e são gravados por `confirmar_atendimento`, na mesma transação do atendimento. |
| Quem acrescentou | Gravado no banco e visível no admin. O recibo **não** mostra (o recibo nunca mostra quem registrou). |
| Quantidade ≤ 0 | Nunca vira linha de saída: `_gravar_linhas` já pula, o robô já recusa, e entra uma `CheckConstraint` no banco. |

### Fora do escopo

- Acrescentar material a pedido já atendido, a saída avulsa ou pelo admin.
- Mudar a quantidade pedida pelo solicitante.
- Avisar o solicitante (Telegram ou outro) da troca.
- Acrescentar sem JavaScript (ver 4.6).

## 2. Dados

### 2.1 `ItemPedido`

Três campos novos:

| Campo | Tipo | Regra |
|---|---|---|
| `origem` | `CharField` com choices `PEDIDO` ("Pedido pelo solicitante") e `ALMOXARIFADO` ("Adicionado pelo almoxarifado"); padrão `PEDIDO` | Os itens do envio público (e os da saída avulsa) são `PEDIDO`. |
| `no_lugar_de` | `ForeignKey("self", null=True, blank=True, on_delete=restringir_troca, related_name="trocado_por")` | Só em item `ALMOXARIFADO`; aponta para um item `PEDIDO` do **mesmo** pedido. `restringir_troca` (em `pedidos/models.py`) é o `RESTRICT`: barra apagar sozinho o item trocado e deixa apagar o pedido inteiro (o acrescentado vai junto na cascata), o que o `PROTECT` barraria. O `models.RESTRICT` não serve no auto-relacionamento com o MySQL (a ordenação da exclusão desiste e a chave é conferida linha a linha); por isso, quando a exclusão segue, o `no_lugar_de` vira nulo antes dos `DELETE`. |
| `adicionado_por` | `ForeignKey(AUTH_USER_MODEL, null=True, blank=True, on_delete=PROTECT, related_name="+")` | Preenchido em todo item `ALMOXARIFADO`; vazio nos `PEDIDO`. |

E `qtd_pedida` passa a aceitar nulo: **nulo só nos itens `ALMOXARIFADO`** (ninguém pediu). Nos
`PEDIDO`, continua obrigatória.

Restrições no banco (`Meta.constraints`):
- `qtd_pedida` nula se e somente se `origem = ALMOXARIFADO`;
- `no_lugar_de` e `adicionado_por` só com `origem = ALMOXARIFADO`, e `adicionado_por` obrigatório nela;
- `(pedido, codigo)` único: um código aparece uma vez por pedido (os campos do formulário são
  `entregue-<codigo>`, e a mesma unidade de conta não pode estar em duas linhas).

O "mesmo pedido" do `no_lugar_de` e o "item `PEDIDO`" do alvo são conferidos no serviço (o banco não
expressa isso) e no `clean` do modelo.

### 2.2 `LinhaSaida`

Nova `CheckConstraint`: `qtd > 0`. É a terceira trava contra linha zerada ou negativa:
1. `servicos._gravar_linhas` só cria linha com quantidade maior que zero (já existe, testado);
2. `scpi/requisicoes.py` recusa o lote com quantidade ≤ 0 e o marca `ERRO` sem abrir o navegador
   (já existe, testado);
3. o banco recusa a gravação (nova), inclusive pelo admin.

### 2.3 Migrations

> **Histórico.** A regeneração abaixo valeu só antes da importação das planilhas no
> servidor. Hoje o servidor está em produção: toda mudança de modelo ganha migration nova,
> nunca regenerada (`CLAUDE.md`, Convenções).

Ainda não houve a importação das planilhas no servidor (passo 3 de `deploy/VIRADA.md`): a migration
de `pedidos` é **regenerada** e o banco local recriado, como manda o CLAUDE.md. A `implantacao`
(conversão das planilhas) grava todos os itens importados com `origem = PEDIDO`, e o código repetido
num mesmo pedido da planilha (que a nova restrição de unicidade recusaria) vira erro da conversão,
com o pedido e o código, como os outros erros que bloqueiam a importação.

## 3. Regras e serviço

### 3.1 Envio do atendimento

`confirmar_atendimento` recebe, além de `qtds` (`{codigo: texto}`, agora com os códigos acrescentados
também), a lista dos acrescentados: `[(codigo, no_lugar_de_codigo_ou_vazio)]`. Os campos do
formulário:

- `adicionado` (repetido): o código de cada material acrescentado, na ordem em que entrou;
- `no-lugar-de-<codigo>`: o código do item pedido que ele substitui, ou vazio;
- `entregue-<codigo>`: a quantidade entregue, igual aos itens pedidos.

Validação, junto com a de hoje (mesma `Resposta` com a lista de erros, `Erro.codigo` apontando a
linha):
- o código acrescentado tem de estar no catálogo da saída avulsa, sem duplicidade de cadastro (as
  mesmas mensagens de `validar_saida` com `catalogo=`);
- não pode repetir código do pedido nem de outro acrescentado: "CAFÉ SOLÚVEL (008.001.005) já está no
  pedido: altere a quantidade nele.";
- `no-lugar-de` vazio, ou o código de um item `PEDIDO` deste pedido; um item pedido só pode ser
  trocado uma vez;
- quantidade do acrescentado: a regra da origem do pedido (AB só inteiros; limpeza com vírgula) e
  maior que zero (acrescentar com 0 não tem sentido: "Informe a quantidade de …");
- sem o limite "maior que a quantidade pedida" (não há pedida) e sem limite de estoque, como na
  saída avulsa (`FLUXOS["avulsa"].com_estoque` é falso: o material só é bloqueado por cadastro
  duplicado);
- o item **pedido** trocado continua com a regra de hoje (0 a pedida).

Se tudo valida, numa transação: cria os `ItemPedido` `ALMOXARIFADO` (retrato do catálogo como na
saída avulsa: `material`, `unidade`, `grupo`; `qtd_pedida` nula; `qtd_entregue`; `no_lugar_de`;
`adicionado_por = usuario`), grava a quantidade entregue dos pedidos e chama `_gravar_linhas` com
todos, na ordem: pedidos, depois acrescentados.

### 3.2 Reenvio

`atendimento_confere` passa a comparar também os acrescentados: o mesmo conjunto de
`(codigo, no_lugar_de, qtd_entregue)`. Igual, confirma (reenvio); diferente, recusa como hoje
("já tem um atendimento registrado. Nada foi gravado.").

### 3.3 Situação do pedido

Hoje um pedido atendido com algum item abaixo do pedido é "Atendido parcialmente". Com a troca, o
item trocado não conta como entregue a menos: `regras.situacao_pedido` só considera os itens
`PEDIDO` **sem** um acrescentado que os substitua com quantidade maior que zero. O `Exists` de
`consultas.filtrar_situacao` repete a regra (o teste que confere que os dois concordam ganha os casos
de troca). Itens `ALMOXARIFADO` nunca tornam o pedido parcial.

### 3.4 Outros usos de `qtd_pedida`

Revisados para aceitar o nulo dos acrescentados:
- `_recibo.html` (coluna Pedido mostra "—"; o `data-pedido` do campo fica vazio e o estado
  total/parcial/acima não se aplica: o campo mostra só "Confirmar");
- `views/almoxarifado._contexto_detalhe` (`entregues` só dos itens existentes; os acrescentados vêm
  do POST na recusa);
- `servicos` linha 114 (catálogo do reenvio do envio público: só itens `PEDIDO`);
- `telegram.py` e `_sucesso.html` (só existem antes do atendimento: sem mudança, mas filtram
  `PEDIDO` por segurança);
- admin (`ItemPedidoInline`): mostra `origem`, `no_lugar_de` e `adicionado_por`, só leitura.

## 4. Tela

Referência: o esboço revisado desta conversa (Trocar na linha, painel de busca embaixo dela, grupo
dos acrescentados, Adicionar material com a observação à vista). Tudo no vocabulário do
`docs/DESIGN.md`; classes novas registradas lá.

### 4.1 Trocar

Cada material pedido ganha "Trocar" (`botao-texto` com o ícone de troca), ao lado do
Confirmar/Alterar. Ao clicar, abre embaixo da linha um painel (`atendimento-painel`):

- título "Trocar CAFÉ TORRADO E MOÍDO por:" e a frase "ele fica com 0 entregue, e o pedido original
  continua registrado.";
- campo **Material** (busca, rótulo visível) com o painel de resultados de sempre
  (`_resultados.html`, catálogo da saída avulsa, mesmos bloqueios);
- campo **Quantidade** (rótulo visível), já com a quantidade pedida do item trocado;
- botões "Trocar" (primário) e "Desistir".

Ao trocar: o item pedido vai para 0, confirmado ("Não entregue"), com a nota "Trocado por CAFÉ
SOLÚVEL"; o novo entra no grupo dos acrescentados, ainda **por confirmar**, com a nota "No lugar de
CAFÉ TORRADO E MOÍDO · Desfazer troca". "Desfazer troca" remove o acrescentado e devolve ao item
pedido a quantidade que ele tinha antes, por confirmar. Um item já trocado não mostra "Trocar".

### 4.2 Adicionar material

Abaixo da tabela, com a **observação do pedido à vista** logo acima (quando houver): botão
"Adicionar material", com a dica "para o que veio na observação ou um a mais, sem trocar nenhum".
Abre o mesmo painel, sem o título de troca ("Adicionar material"), com Quantidade vazia. O
acrescentado entra no grupo, por confirmar, com "Remover".

### 4.3 Grupo dos acrescentados

Abaixo dos materiais pedidos, uma linha de grupo com o selo "Adicionado pelo almoxarifado"
(`selo-info`), e as linhas no mesmo formato da tabela: código e nome, "—" na coluna Pedido, o campo
da quantidade entregue com a unidade do SCPI dentro, Confirmar/Alterar. O título passa a contar
todos: "Materiais (3)". "Entregar tudo o que foi pedido" não mexe nos acrescentados nem nos itens
trocados.

### 4.4 Confirmação e envio

Os acrescentados também precisam ser confirmados antes de "Confirmar e registrar saída" (a regra de
hoje vale para todos). Se o servidor recusar, a página volta com os acrescentados no lugar, com o
erro embaixo da linha (`entrega-erro`) e no resumo.

### 4.5 Acessibilidade

- cada troca, acréscimo, remoção e desfazer é anunciado num `role="status"` único da tabela
  ("CAFÉ SOLÚVEL entrou no lugar de CAFÉ TORRADO E MOÍDO."), sem mover o foco;
- ao abrir o painel, o foco vai para o campo Material; ao trocar ou adicionar, para o campo da
  quantidade entregue da nova linha; ao desistir, de volta para o botão que abriu;
- campos com rótulo visível, erro embaixo do campo e ligado por `aria-describedby`;
- estado nunca só por cor: selo com texto, notas "Trocado por" / "No lugar de".

### 4.6 Sem JavaScript

"Trocar" e "Adicionar material" não aparecem (precisam da busca dinâmica); o atendimento funciona
como hoje.

### 4.7 Recibo (depois de atendido, na tela e no papel)

Dois grupos: "Pedido pelo solicitante" e "Adicionado pelo almoxarifado", só quando o pedido tem
algum acrescentado (sem acrescentado, a tabela fica como hoje). A saída avulsa não tem solicitante
nem acrescentados: seu recibo não muda. O item trocado mostra 0 e
"Trocado por …"; o acrescentado, "—" na coluna Pedido e "No lugar de …" quando houver. Sem quem
acrescentou. A unidade é a do SCPI (regra de hoje da área interna).

## 5. Testes

Contra MySQL/MariaDB, como a suíte.

- **Modelo:** as restrições do 2.1 e o `qtd > 0` do 2.2 (gravar fora da regra levanta
  `IntegrityError`); `clean` recusa `no_lugar_de` de outro pedido ou de item `ALMOXARIFADO`.
- **Serviço:** troca grava o acrescentado com `origem`, `no_lugar_de`, `adicionado_por` e
  `qtd_pedida` nula, o trocado com 0 e as linhas de saída só dos com quantidade > 0, no mesmo lote;
  acréscimo sem vínculo; recusas (código fora do catálogo, duplicado, repetido no pedido, segundo
  "no lugar de" para o mesmo item, quantidade 0 ou inválida, AB não inteiro); nada
  gravado quando recusa; reenvio igual confirma e diferente recusa.
- **Situação:** pedido com troca não é parcial; com item pedido abaixo e sem troca continua parcial;
  `situacao_pedido` e `filtrar_situacao` concordam nos casos novos.
- **Robô:** um lote com acrescentado vira uma requisição com os itens na ordem do lote.
- **Tela:** detalhe pendente tem "Trocar" por item pedido e "Adicionar material" (escondidos sem
  JavaScript), a observação à vista; a recusa devolve os acrescentados nos campos; o recibo atendido
  mostra os dois grupos, as notas e nunca quem acrescentou.
- **Implantação:** itens importados das planilhas entram com `origem = PEDIDO`.

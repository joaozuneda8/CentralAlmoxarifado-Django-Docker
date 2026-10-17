# Edição do atendimento até o lançamento no SCPI

Data: 2026-10-17 · Situação: implementada. Acrescenta à área do almoxarifado a edição de um pedido já atendido (ou de uma
saída avulsa) enquanto as linhas de saída ainda não foram lançadas no SCPI. Os esboços de baixa
fidelidade estão em `docs/superpowers/esbocos/2026-10-17-edicao-pedido/` (ver a seção 9 para o
que mudou depois deles).

## 1. Objetivo

Hoje um atendimento confirmado não muda: o `confirmar_atendimento` recusa um segundo atendimento,
e um erro de digitação (quantidade entregue, recebedor, centro de custo, material trocado) só se
corrige pelo admin, linha a linha. O objetivo é deixar quem usa o painel reabrir o atendimento,
corrigir e salvar, enquanto o robô não lançou o lote no SCPI. Depois do lançamento, a edição é
bloqueada e a correção é feita no próprio SCPI.

### Decisões tomadas

- **D1. Lugar**: modo de edição explícito, numa URL própria (`/painel/pedidos/<numero>/editar/`),
  que é a página de detalhe com o formulário de atendimento preenchido. Descartadas a gaveta
  lateral no painel (não comporta a tabela de materiais com troca e busca; componente novo) e a
  edição inline na lista (muitos campos; cada gravação parcial abriria uma janela para o robô).
- **D2. Quem**: todo usuário com acesso ao painel, como no atendimento. Não há papel de aprovador.
- **D3. O que é editável**: só o que o atendimento grava (seção 3). O que veio do funcionário
  (solicitante, destino, observação do pedido, a lista de materiais pedidos e as quantidades
  pedidas) nunca muda. O formulário de atendimento continua como está.
- **D4. Saída avulsa**: editável do mesmo jeito (dados da saída e materiais).
- **D5. Conflito com o robô**: concorrência otimista; o robô vence. A edição é conferida ao salvar
  e recusada se o lote entrou em lançamento. Não há trava de "em edição".
- **D6. Recibo impresso**: qualquer edição salva devolve o recibo a "não impresso"
  (`recibo_impresso_em = None`), com aviso antes de salvar.
- **D7. Lote com `ERRO`**: editável; salvar recria as linhas como `PENDENTE`, e o lote volta à fila
  sem o "liberar" de Automações.
- **D8. Histórico**: um registro por edição salva (quem, quando, diferenças), visível no detalhe,
  nunca no recibo.
- **D9. Depois do lançamento**: só o bloqueio, com o número da requisição e "correções são feitas
  no SCPI".

### Fora do escopo

- Alterar requisição retroativamente no SCPI ou lançar requisição de entrada de devolução atrelada
  a uma saída (o SCPI permite os dois; fica para o futuro).
- Editar o cabeçalho ou os materiais pedidos pelo funcionário, em qualquer estado.
- Qualquer mudança no formulário de atendimento, nos formulários públicos e no painel de pedidos
  (lista).
- Aviso no Telegram de edição.

## 2. Estados da edição

Derivados das linhas de saída do lote (um pedido é um lote, `lote = pedido.numero`), sem campo
novo de estado. Uma função pura em `regras.py`, `edicao_permitida(atendido, linhas) -> Edicao`,
devolve a chave (`antes_do_atendimento`, `editavel`, `suspensa`, `bloqueada`), o texto do motivo e
os números de requisição, e é usada pelo detalhe, pelo modo de edição e pelo serviço.

| Linhas do lote | Chave | Na tela |
|---|---|---|
| Sem atendimento | `antes_do_atendimento` | Sem botão de editar; a página já mostra o atendimento. |
| Todas `PENDENTE`, `NAO_LANCAR` ou `ERRO`, nenhuma com `requisicao_scpi` | `editavel` | Botão ativo; avisos da seção 4. |
| Alguma `EM_LANCAMENTO` ou `VERIFICAR` | `suspensa` | Botão desabilitado com cadeado e motivo; link "Resolver em Automações". |
| Alguma `LANCADA` ou com `requisicao_scpi` (inclui o parcial) | `bloqueada` | Botão desabilitado: "Lançado na requisição N em dd/mm/aaaa hh:mm; correções são feitas no SCPI". |

`suspensa` volta a `editavel` se, na conferência em Automações, o lote for liberado para relançar.

## 3. Dados e regras

### O que se edita

- Dados da saída: data efetiva, recebedor, centro de custo, tipo de saída, placa, observações,
  "Não lançar no SCPI".
- Quantidade entregue de cada material pedido.
- Materiais do almoxarifado: trocar um material pedido, desfazer uma troca, acrescentar um
  material, remover um acrescentado.

Na saída avulsa não há coluna "pedido": editam-se os dados da saída e os materiais.
`atendido_por` e `atendido_em` continuam os do atendimento original.

### Modelo (migration nova, aditiva)

O servidor está em produção: a mudança vem numa **migration nova** em `pedidos`, nunca regenerando
a `0001_initial`, e sem operação sobre dados.

- `Pedido.versao`: `PositiveIntegerField(default=0)`. Os pedidos existentes começam na versão 0.
  Cada edição salva soma 1. O formulário de edição a leva num campo escondido.
- `AlteracaoPedido`: `pedido` (FK, `CASCADE`, `related_name="alteracoes"`), `usuario` (FK para o
  usuário, `PROTECT`), `em` (`DateTimeField`, padrão agora), `versao` (a versão gravada por esta
  edição), `diferencas` (`JSONField`: lista de `{"campo", "antes", "depois"}` e, por material,
  `{"codigo", "material", "mudanca", "antes", "depois"}`), `scpi_antes` (`JSONField`: situação e
  mensagem das linhas substituídas). Ordenação `-em`. Só leitura no admin.
- Pedido editado antes desta versão não tem histórico: a tela diz "Nenhuma alteração registrada".

### Diferenças

`regras.diferencas_atendimento(gravado, enviado) -> list[dict]`, pura: compara o cabeçalho da
saída, as quantidades entregues, as trocas e os acréscimos gravados com os enviados. Serve ao
histórico, à mensagem de sucesso e à lista de alterações não gravadas nas recusas. Lista vazia
quer dizer "nada mudou".

### Serviço

`servicos.editar_atendimento(pedido_id, versao, dados, qtds, *, nao_lancar, adicionados, usuario,
hoje=None) -> Resposta`, numa transação:

1. Trava o pedido (`select_for_update`). Sem atendimento, recusa ("Pedido não encontrado").
2. Trava as linhas do atendimento (`select_for_update`) e calcula `edicao_permitida`. Fora de
   `editavel`, recusa com `motivo="lancamento"` e o texto da seção 2.
3. Se `versao` difere da gravada: se o que está gravado é igual ao enviado (diferenças vazias),
   devolve sucesso como reenvio; senão, recusa com `motivo="versao"`, o nome de quem salvou e a
   hora (da última `AlteracaoPedido`).
4. Valida com as mesmas regras do `confirmar_atendimento`. A validação dele sai para uma função
   comum (`_validar_atendimento`), sem mudar o comportamento do atendimento. Diferenças:
   - um acrescentado já gravado e inalterado (mesmo código, mesma troca) é aceito mesmo fora do
     catálogo atual da saída avulsa; um acrescentado novo precisa estar no catálogo;
   - valor gravado que deixou de existir (centro de custo, tipo de saída, placa) é recusado mesmo
     sem alteração, com o texto "O valor gravado não existe mais: escolha outro".
5. Sem diferenças, não grava nada e devolve sucesso com "Nada mudou; nada foi gravado".
6. Grava: quantidades entregues dos itens `PEDIDO`; acrescentados (apaga os removidos, cria os
   novos, atualiza a quantidade dos mantidos; o `no_lugar_de` acompanha a troca); cabeçalho do
   atendimento e `nao_lancar`; `recibo_impresso_em = None`; `versao + 1`; a `AlteracaoPedido`.
7. **Apaga e recria as linhas de saída** do lote pelo `_gravar_linhas` (IDs novos, `PENDENTE` ou
   `NAO_LANCAR`), com `mensagem` "Refeita na edição de dd/mm/aaaa hh:mm por <usuário>". Nunca
   atualiza as linhas no lugar: a troca de IDs é o que faz o robô pular um lote que leu antes da
   edição.

Os campos de cabeçalho e de quantidade pedida que vierem no POST são ignorados.

### "Não lançar" marcado em Automações

O `resolver_lote` com `nao_lancar` muda as linhas mas não o `Atendimento.nao_lancar`. O formulário
de edição abre com "Não lançar no SCPI" marcado quando todas as linhas ativas estão `NAO_LANCAR`,
e o salvar grava o valor no atendimento; assim a recriação das linhas não desfaz essa decisão.

### Confirmação de recibo impresso

O formulário "Saiu na impressora" passa a levar a `versao` do pedido. `marcar_recibos_impressos`
ignora o atendimento cujo pedido mudou de versão, e a view avisa "O pedido foi alterado depois de
abrir esta página; imprima de novo". Assim uma impressão da versão anterior, feita em outra aba,
não marca a versão nova.

## 4. Interface

Segue o `docs/DESIGN.md` e o que já está no código; estado nunca só por cor.

### Detalhe (leitura)

- Botão secundário "Editar atendimento" ("Editar saída" na avulsa) ao lado do "Imprimir recibo",
  que continua o primário. Só existe depois do atendimento.
- `editavel`: aviso curto "Pode ser editado até o robô lançar no SCPI". Com o recibo impresso,
  acrescenta "salvar alterações devolve o recibo para impressão". Com lote `ERRO`, "Corrija e
  salve: o lote volta para a fila do próximo lançamento".
- `suspensa` e `bloqueada`: o botão continua no lugar, com `aria-disabled`, cadeado e a dica do
  motivo, como o "Lançar no SCPI" bloqueado.
- Bloco recolhido "Alterações depois do atendimento" (`nao-imprimir`): uma linha por
  `AlteracaoPedido`, com quem, quando e as diferenças em frase.

### Modo de edição (`pedidos:editar`)

- O detalhe com o formulário de atendimento preenchido: quantidades entregues já confirmadas,
  trocas e acréscimos reconstruídos nos campos escondidos (`adicionado`, `no-lugar-de-<codigo>`,
  `data-qtd-antes`) e os dados da saída. O `pedidos.js` aplica a esse estado inicial o mesmo
  tratamento que já aplica à página devolvida pela recusa.
- Faixa no topo: "Editando <número>. Nada é gravado até você salvar." O voltar diz "Voltar ao
  pedido (descarta as alterações)". O `beforeunload` pede confirmação quando há algo mudado.
- Campo alterado em relação ao valor de abertura ganha destaque (borda e o texto "alterado"). O
  rodapé mostra "N alterações", "Descartar" (volta ao detalhe) e "Salvar alterações".
- `atendimento_materiais` e `atendimento_adicionar` aceitam o pedido não atendido (como hoje) ou
  atendido e `editavel`; recusam os demais.
- Abrir `/editar/` de um pedido fora de `editavel` redireciona ao detalhe com a mensagem do motivo.

### Depois de salvar

Redireciona ao detalhe com a mensagem "Alterações salvas no pedido <número>" e a lista das
diferenças; com recibo que estava impresso, "O recibo voltou para impressão" (o pedido reaparece
no `?recibo=pendente`).

### Recusas (a página do formulário volta, nunca a lista)

- Validação: como no atendimento (resumo no topo, erro no campo).
- `motivo="lancamento"`: o formulário vira leitura, o "Salvar" sai, a faixa vermelha diz a hora e
  a execução do robô, e embaixo "Alterações não gravadas" lista as diferenças, com "Copiar resumo".
- `motivo="versao"`: "<Nome> salvou alterações às hh:mm". As diferenças da pessoa ficam listadas,
  com o botão "Editar de novo a partir do que está gravado".

### Robô rodando durante a edição

Só enquanto há execução em andamento (`ExecucaoRobo.em_andamento`), a faixa do modo de edição se
recarrega a cada 5 s, pedindo a própria página com o `HX-Target` (a técnica de Automações). Ela
avisa "Um lançamento está em andamento; se chegar a este pedido, suas alterações serão recusadas"
e passa ao estado de recusa por lançamento se o lote travar. Sem execução, não há consulta.

## 5. Concorrência

- Ordem das travas: a edição trava o pedido e depois as linhas. O robô (`_travar`) e o
  `resolver_lote` travam só as linhas, em transações curtas. Não há espera em círculo.
- O robô lê a fila e a edição salva antes do `_travar`: as linhas foram recriadas, o `_travar`
  encontra menos linhas que `req.ids` e pula o lote; as linhas novas entram no próximo lançamento.
- O robô trava antes: a edição encontra `EM_LANCAMENTO` e recusa.
- A simulação (`--dry-run`) não toca nas linhas e não bloqueia a edição.
- Duas pessoas (ou duas abas): a `versao` decide; o reenvio igual é sucesso.

## 6. Testes

- `tests/test_regras_edicao.py` (puro): `diferencas_atendimento` (cabeçalho, entregue, troca feita
  e desfeita, acréscimo incluído e removido, "não lançar", sem mudança) e `edicao_permitida` (cada
  linha da tabela da seção 2).
- `tests/test_editar_atendimento.py`:
  - serviço: caminho feliz (entregas, linhas com IDs novos, versão, histórico, recibo zerado); as
    recusas de validação do atendimento; um teste por estado das linhas; versão diferente; reenvio
    igual; sem mudança; "não lançar" do `resolver_lote` preservado; acrescentado oculto inalterado
    aceito e novo recusado; mensagem das linhas refeitas e `scpi_antes`; cabeçalho e quantidade
    pedida inalterados mesmo vindo no POST; saída avulsa;
  - views: login exigido; 404 sem pedido; redirecionamento fora de `editavel`; formulário
    preenchido; botão do detalhe em cada estado; histórico no detalhe e fora do recibo; recusa por
    lançamento sem "Salvar" e com as diferenças; busca e "Adicionar" aceitando o pedido editável e
    recusando o bloqueado; confirmação de impresso com versão antiga ignorada.
- `tests/test_lancamento.py`: `agrupar`, editar e `lancar` (o lote é pulado e sai no lançamento
  seguinte com o conteúdo novo); robô trava e editar (recusa, linhas `EM_LANCAMENTO` intactas).
- Migration: `makemigrations --check` passa, e um teste confere que a migration nova só tem
  `AddField` e `CreateModel`.
- `tests/test_prefixo.py` continua passando.
- Conferência no navegador, com screenshot: detalhe editável, suspenso e lançado; modo de edição
  com campos destacados; recusa por lançamento (lote posto em `EM_LANCAMENTO` pelo admin); 375 px;
  `beforeunload` e "Descartar".

## 7. Documentação

- `CLAUDE.md`: a edição na seção de arquitetura da área do almoxarifado e, em Convenções, a regra
  das migrations atualizada (o servidor está em produção: migration nova, nunca regenerada; a
  virada deixa de aparecer como pendente).

## 8. Premissas

- Quem tem acesso ao painel é quem atende; não existe papel de gestor ou aprovador.
- O caminho de correção depois do lançamento é o SCPI.
- Um lote só fica parcialmente lançado por intervenção manual (`resolver_lote` ou admin); qualquer
  linha lançada bloqueia o pedido inteiro.

## 9. Esboços

`a-detalhe-modo-edicao.html` e `b-painel-lateral.html` foram feitos antes das decisões. Valem a
estrutura do A e os estados A1, A3, A4, A5 e A6, com estas mudanças:
- o bloco "dados do pedido" do A2 não é editável (D3);
- o painel "resumo das alterações" ao vivo do A2 foi substituído pelo destaque dos campos alterados
  e pela lista de diferenças calculada no servidor (seção 4);
- o botão se chama "Editar atendimento" (A1, A5, A6 dizem "Editar pedido").

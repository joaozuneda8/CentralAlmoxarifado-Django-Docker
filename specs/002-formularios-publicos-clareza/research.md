# Research: Clareza e facilidade de uso dos formulários públicos de pedido

Não havia nenhum NEEDS CLARIFICATION no Technical Context: a funcionalidade só usa o que o projeto
já tem (Django templates, HTMX 4 vendorizado, `pedidos.js`, `dropdown.js`, design system Clean).
As decisões abaixo resolvem as dúvidas de projeto levantadas ao ler o código.

## R1. Como saber a qual campo pertence cada erro (FR-005, FR-006)

- **Decision**: acrescentar ao `regras.Erro` um terceiro campo opcional, `campo: str | None = None`
  (nome do campo do formulário: `solicitante`, `destino` ou `obs`). `validar_pedido_limpeza` e
  `validar_pedido_ab` passam `campo="solicitante"`/`"destino"` nos erros desses campos;
  `servicos.erros_de_tamanho` passa o campo de cada rótulo (`Nome completo` → `solicitante`,
  `Destino` → `destino`, `Observação` → `obs`). A view monta `erros_por_campo`
  (`{campo: [texto, ...]}`) para o template.
- **Rationale**: a regra continua pura e com os mesmos textos (Princípio I); o campo é um dado a
  mais, com padrão `None`, então quem cria `Erro(codigo, texto)` não muda. Nenhum teste constrói
  `Erro` diretamente.
- **Alternatives considered**: classificar pelo texto na view (frágil: qualquer ajuste de texto
  quebra em silêncio); devolver um dicionário separado do serviço (duplica a lista de erros e muda
  a assinatura de `Resposta`).

## R2. Botão de envio dentro da gaveta (FR-001 a FR-003)

- **Decision**: a gaveta (`_carrinho.html`) ganha um botão `type="button"` com
  `data-carrinho-enviar`. O `pedidos.js` fecha a gaveta e chama
  `form.requestSubmit(botaoFinal)`, usando o botão de envio do fim do formulário (`.acoes-final
  button[type=submit]`). O rótulo do botão da gaveta é copiado do botão final ao abrir a gaveta,
  para que o caso divergente ("Já conferi com o almoxarifado — enviar como novo pedido") apareça
  igual. O "Continuar pedindo" vira "Adicionar mais materiais", secundário.
- **Rationale**: o `_carrinho.html` é devolvido pela view do carrinho, que não sabe se o envio
  anterior foi divergente; reaproveitar o botão final evita levar esse estado ao carrinho. Fechar
  a gaveta antes do envio deixa a resposta (sucesso ou erros) visível na página. Sem JavaScript
  não existe gaveta, então nada muda nesse caso.
- **Alternatives considered**: `type="submit"` direto na gaveta (o `<dialog>` está dentro do
  `<form>`, funcionaria, mas o rótulo divergente exigiria passar `divergente` à view do carrinho);
  `form="..."` com id (mesmo problema do rótulo).

## R3. Barra fixa do celular (FR-004)

- **Decision**: com linhas, a barra mostra "Seu pedido" e, embaixo, "N materiais" (singular com 1; duas linhas para caber em 375px) e o botão
  "Revisar e enviar" (abre a gaveta). Sem linhas, mostra "Nenhum material adicionado" e não mostra
  o botão. Tudo no `_carrinho.html`, que já é re-renderizado a cada mudança do carrinho.
- **Rationale**: o estado vazio deixa de convidar a abrir um pedido vazio; o texto da ação diz o
  próximo passo real.

## R4. Foco e links do resumo de erros (FR-005, FR-007, FR-009)

- **Decision**: o resumo vira `<div class="aviso aviso-erro" role="alert" tabindex="-1"
  data-resumo-erros>` com um título ("Faltam N coisas para enviar" / "Falta 1 coisa para enviar")
  e uma lista; erros com `campo` viram `<a href="#<campo>">`. Depois do swap do HTMX, o
  `pedidos.js` põe o foco no resumo (`preventScroll`, porque o `show:top` já rola). Clicar num
  link do resumo foca o campo (comportamento nativo da âncora; o JS só garante o foco no campo
  combo). Ao digitar num campo `aria-invalid="true"`, o JS remove `aria-invalid` e a classe
  `campo-com-erro` do `.campo` pai (a mensagem embaixo fica, como registro, até o próximo envio).
  A mensagem geral do serviço ("Corrija os itens abaixo e envie de novo.") continua no resumo,
  abaixo do título.
- **Rationale**: segue a orientação de resumo focável com links mais erro junto ao campo; usa as
  classes que o design system já tem (`campo-com-erro`, `campo-erro`). O `dropdown.js` mantém o
  `<input>` original como controle do combo, então `aria-invalid` e a borda valem também no
  destino.
- **Alternatives considered**: tirar a mensagem embaixo do campo ao digitar (some a explicação no
  meio da correção); validar ao sair do campo no cliente (duplicaria regras do servidor).

## R5. Nome e destino lembrados (FR-014 a FR-017)

- **Decision**: `localStorage`, chave `almoxarifado.solicitante`, valor JSON
  `{"solicitante": "...", "destino": "..."}`. A tela de sucesso traz
  `data-lembrar-solicitante` e `data-lembrar-destino` (o destino como está no cadastro); o
  `pedidos.js` grava ao ver esse elemento (após o swap ou no carregamento). Ao abrir o formulário,
  preenche só os campos vazios (não sobrescreve o que o servidor devolveu num envio recusado); o
  destino só é preenchido se estiver nas opções do `<datalist id="destinos">`. Com dados
  preenchidos assim, mostra o link "Não é você? Limpar" (no template com `hidden`), que esvazia os
  dois campos e apaga a chave. Toda leitura e escrita fica em `try/catch`; sem armazenamento, nada
  acontece.
- **Rationale**: conveniência por aparelho, sem estado no servidor (o servidor continua sem
  guardar nada do solicitante fora do pedido). O mesmo padrão do `filtros.js`.
- **Alternatives considered**: cookie (iria ao servidor a cada pedido, sem necessidade);
  lembrar ao digitar (guardaria nomes de envios recusados ou abandonados).

## R6. Confirmar antes de sair (FR-018)

- **Decision**: `beforeunload` no `pedidos.js`, ativo só quando há `.carrinho-linha[data-codigo]`
  na página de um formulário público (`[data-formulario-pedido]`) e o formulário não está sendo
  enviado (um `submit` sem HTMX liga uma marca que desliga o aviso). Na tela de sucesso o carrinho
  não existe mais, então não há aviso. A saída avulsa (área interna) não ganha o aviso.
- **Rationale**: o carrinho só existe na página; é a única forma de não perdê-lo. O navegador
  mostra o texto padrão dele (não dá para personalizar).
- **Alternatives considered**: guardar o carrinho no `localStorage` para restaurar (mais complexo,
  e o estoque pode ter mudado; fica para depois, se o aviso não bastar).

## R7. Ordem dos resultados (FR-021)

- **Decision**: em `fluxos.buscar`, ordenar os achados de forma estável por "bloqueado ou não"
  (`motivo_bloqueio`) **antes** de cortar nos `LIMITE_RESULTADOS` (50). Dentro de cada grupo a
  ordem do catálogo continua (no AB, pelo número de saídas consolidadas).
- **Rationale**: ordenar depois do corte poderia deixar de fora um material pedível que estava
  além do 50º. Vale para os três fluxos (na avulsa, `motivo_bloqueio` só bloqueia duplicados).

## R8. Textos de estoque e unidade (FR-022, FR-023)

- **Decision**: `fluxos.resultados` passa a montar `info` do AB como `"<n> <unidade>
  disponíveis"` (sem unidade: `"<n> disponíveis"`). O template de resultados mostra a unidade
  (`r.item.unidade`) num `<span>` logo depois do controle − / +, nos três fluxos, quando houver
  unidade.

## R9. Retorno do botão "Adicionar" (FR-024)

- **Decision**: no `pedidos.js`, guardar o botão que disparou o `hx-post` de adicionar
  (`htmx:before:request`, alvo com `hx-vals` de `adicionar`) e, depois do swap do `#carrinho`, se
  a resposta não trouxe erro (`[data-carrinho-alerta].aviso-erro`), trocar o conteúdo do botão por
  ícone de check + "Adicionado" por 2 s e voltar ao original. Uma região `role="status"`
  escondida (`visually-hidden`) recebe "<nome> adicionado ao pedido." para leitores de tela.
- **Rationale**: o selo "✓1" continua (diz quanto já está no pedido); o botão dá o retorno
  imediato no ponto do toque.
- **Notes**: os nomes de evento do HTMX 4 seguem o padrão `htmx:before:request` /
  `htmx:after:swap` já usado no projeto; conferir no `htmx` vendorizado durante a implementação.

## R10. Títulos e página inicial (FR-011 a FR-013)

- **Decision**: em `fluxos.FLUXOS`, `titulo` de limpeza vira "Limpeza, copa e escritório" e o de
  AB, "Ferramentas, peças e materiais"; o campo `formulario` ("Formulário 1/2") sai do `Fluxo`, e
  o bloco `rotulo` do formulário passa a "Pedido de materiais". A página inicial usa os mesmos
  títulos, com os exemplos escritos no template (escolhidos uma vez entre os materiais mais pedidos
  de cada catálogo). O rótulo interno
  (`Pedido.Origem` "Materiais AB", Telegram, painel) não muda; URLs (`/pedido/ab/`,
  `/pedido/limpeza/`) também não.
- **Rationale**: o `Fluxo.titulo` só aparece nas telas públicas (`formulario.html`); a avulsa usa
  o próprio template.

## R11. Código fora do carrinho público, cabeçalho e sucesso (FR-025 a FR-027)

- **Decision**: `_carrinho.html` só mostra o código com `not fluxo.publico`. O link "Área do
  almoxarifado" sai do cabeçalho de `base_publico.html` (o rodapé fica). A view de sucesso passa
  `itens` (`resposta.pedido.itens` com material, quantidade e unidade, na ordem gravada) e o
  destino; `_sucesso.html` lista-os. No reenvio, `resposta.pedido` já é o pedido gravado, então a
  lista é a mesma.

## R12. Asteriscos, "(opcional)" e dica do destino (FR-019, FR-020)

- **Decision**: rótulos sem asterisco; o título do passo 3 vira "Observações (opcional)". A dica
  do destino fica "Setor, posto, viatura ou placa." e a explicação completa vai para um
  `<details class="campo-ajuda"><summary>O que pôr aqui?</summary>…</details>` (funciona sem
  JavaScript). O `aria-describedby` do destino aponta para a dica curta e para o erro, quando
  houver.

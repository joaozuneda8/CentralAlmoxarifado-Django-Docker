# Contrato: telas públicas de pedido

As rotas, os métodos, os nomes de campo do `<form>` e o que é gravado **não mudam**. Este
contrato descreve o que cada tela mostra e os ganchos (`data-*`) que o `pedidos.js` usa, para que
os testes de template conferam a estrutura sem abrir o navegador.

## `GET /` → `pedidos:inicio`

- Sem "Formulário 1" nem "Formulário 2".
- Cartão de limpeza: título "Limpeza, copa e escritório", linha de exemplos
  ("Ex.: detergente, café, papel A4, caneta" ou equivalente).
- Cartão AB: título "Ferramentas, peças e materiais", linha de exemplos
  ("Ex.: luva, fita veda-rosca, lâmpada, cano" ou equivalente).
- Aviso de que pedir não é a saída do material (como hoje).

## Layout público (`base_publico.html`)

- Cabeçalho: só a marca. Rodapé: mantém "Área do almoxarifado".

## `GET /pedido/<fluxo>/` → `pedidos:formulario`

- `<title>` e `<h1>`: o `Fluxo.titulo`; rótulo acima do título: "Pedido de materiais".
- Passo 1:
  - `#solicitante` com rótulo "Nome completo" (sem `*`).
  - `#destino` com rótulo "Destino dos materiais" (sem `*`), dica curta
    `#destino-dica` ("Setor, posto, viatura ou placa.") e
    `<details class="campo-ajuda">` com `<summary>O que pôr aqui?</summary>` e a explicação de hoje.
  - `[data-esquecer-solicitante]`: link/botão "Não é você? Limpar", com `hidden` (o JS mostra).
- Passo 3: título "Observações (opcional)".
- `#formulario [data-formulario-pedido]` como hoje.

### Barra e gaveta (`_carrinho.html`, devolvido também por `POST pedidos:carrinho`)

| Estado | Barra | Gaveta |
|---|---|---|
| sem linhas | "Nenhum material adicionado"; **sem** `[data-carrinho-abrir]` | texto de vazio; `[data-carrinho-continuar]` |
| com N linhas | "Seu pedido" e, embaixo, "N material/materiais" (duas linhas curtas, para o botão caber em 375px) e `[data-carrinho-abrir]` "Revisar e enviar" | lista; `[data-carrinho-enviar]` "Enviar pedido" (primário); `[data-carrinho-continuar]` "Adicionar mais materiais" (secundário) |

- Formulário público: a linha do carrinho **não** mostra o código. Saída avulsa: mostra (como hoje).
- Linha do pedido nos formulários públicos (FR-031): `span.carrinho-acoes[data-alterar]` com
  `span.carrinho-qtd-texto` ("<n> <unidade>"), `button[data-alterar-abrir]` "Alterar"
  (`aria-expanded`, `aria-controls="carrinho-qtd-area-N"`), `span.carrinho-qtd-area#carrinho-qtd-area-N`
  com o − / +, o `input[name=item_qtd][data-qtd-carrinho]` (`hx-trigger="confirmar-quantidade"`),
  `button[data-alterar-confirmar]` e `button[data-alterar-cancelar]`; e o "Remover". Na saída
  avulsa, o campo tem `hx-trigger="change"` e não há `data-alterar`.
- A barra e a gaveta novas valem só com `fluxo.publico`; a saída avulsa mantém "Ver pedido" e "Continuar pedindo", sem `data-carrinho-enviar` (FR-029).
- `[data-carrinho-enviar]` é `type="button"` e só existe com linhas.

### Resultados (`_resultados.html`)

- Ordem: pedíveis primeiro, bloqueados depois (mesma ordem relativa do catálogo).
- AB: texto de estoque "<n> <unidade> disponíveis".
- A unidade fica só embaixo do nome (no AB, em "<n> <unidade> disponíveis"); nada ao lado do controle − / + (unidades longas da limpeza, como "EMBALAGEM 5 Kg", empurravam o "Adicionar" para fora do painel).
- Formulários públicos (FR-030): `div.material-acao[data-adicionar]` com
  `button[data-adicionar-abrir]` "Adicionar" (`aria-expanded`, `aria-controls="qtd-area-N"`) e
  `div.material-qtd#qtd-area-N` com a quantidade, `button[data-adicionar-confirmar]` (o `hx-post`;
  sem JavaScript diz "Adicionar") e `button[data-adicionar-cancelar]` (✕, `aria-label="Cancelar"`).
  Saída avulsa: sem `data-adicionar`, sem abrir nem cancelar.
- Região `[data-anuncio-adicionado]` com `role="status"` e `visually-hidden`, uma por página
  (fora de `#resultados`, para não ser trocada pelo swap).

### Envio recusado (resposta de `POST pedidos:formulario`)

- Resumo: `[data-resumo-erros]` com `role="alert"` e `tabindex="-1"`:
  - título "Falta 1 coisa para enviar" / "Faltam N coisas para enviar" (N = número de itens da lista, isto é, todos os erros, de campo e de material);
  - a mensagem do serviço;
  - lista: erro com `campo` → `<a href="#<campo>">texto</a>`; demais → texto.
- Mensagem geral sem lista (expirado, isca, limite, divergente): resumo só com a mensagem, como
  hoje.
- Campo com erro: o `.campo` ganha `campo-com-erro`; o controle ganha `aria-invalid="true"` e
  `aria-describedby` inclui `<campo>-erro`; abaixo, `<p id="<campo>-erro" class="campo-erro">` com
  ícone de alerta e o texto.
- Observações com erro de tamanho: idem, no `#obs`.
- Linhas de material com erro: selo "Corrigir" (como hoje).

### Sucesso (`_sucesso.html`)

- Número, "Pedido registrado" ou "Pedido já estava registrado", avisos de hoje.
- Destino do pedido e lista dos materiais (nome, quantidade, unidade).
- Elemento com `data-lembrar-solicitante="<nome>"` e `data-lembrar-destino="<destino do cadastro>"`.
- "Fazer outro pedido" e "Voltar ao início", como hoje.

## Comportamento do `pedidos.js` (só com JavaScript)

| Gancho | Comportamento |
|---|---|
| `[data-carrinho-enviar]` | fecha a gaveta e envia o formulário pelo botão final (`requestSubmit`); o rótulo é copiado do botão final ao abrir a gaveta |
| `[data-resumo-erros]` | recebe o foco depois do swap |
| campo com `aria-invalid` | ao digitar, perde `aria-invalid` e o `.campo` perde `campo-com-erro` |
| `[data-lembrar-solicitante]` | grava nome e destino no `localStorage` |
| ao carregar o formulário | preenche nome e destino vazios com os lembrados (destino só se estiver no `#destinos`); mostra `[data-esquecer-solicitante]` |
| `[data-esquecer-solicitante]` | esvazia os dois campos, apaga a chave, esconde o link |
| `beforeunload` | pede confirmação se há `.carrinho-linha[data-codigo]` num `[data-formulario-pedido]` e não há envio em curso |
| `[data-adicionar-abrir]` | abre a quantidade (fecha a outra aberta), em 1 ou com a do pedido; rótulo "Adicionar" ou "Alterar"; o confirmar vira "Confirmar" ou "Atualizar" |
| `[data-adicionar-confirmar]` | "Confirmar": manda o `adicionar`; sem erro, fecha e mostra "Adicionado" por 2 s no abrir; com erro, fica aberta. "Atualizar": põe a quantidade na linha do pedido (`alterar`, substitui); aceita, fecha e mostra "Atualizado", recusada, fica aberta; anúncio em `[data-anuncio-adicionado]` |
| `[data-alterar-abrir]` / `[data-alterar-confirmar]` / `[data-alterar-cancelar]`, Esc | abre o − / + da linha do pedido (fecha a outra aberta); "Confirmar" (ou Enter) dispara `confirmar-quantidade`, que manda o `alterar`; ✕/Esc voltam ao valor anterior sem fechar a gaveta; o envio do pedido desfaz a alteração aberta |
| `[data-adicionar-cancelar]`, Esc | fecham a quantidade sem adicionar (o Esc não fecha o painel de resultados) |

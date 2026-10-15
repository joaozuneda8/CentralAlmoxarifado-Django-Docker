# Interface no estilo Clean — design

Data: 2026-10-10 · Situação: aguardando revisão

## 1. Objetivo

Refazer toda a interface do Central Almoxarifado em cima do design system "Clean"
(`.claude/skills/clean-design/`, cópia de `C:\Users\Joao\Documents\Dev\Skills`). A fundação
visual que veio do WMS-Almoxarifado sai inteira. Os formulários públicos estão feios, e o
sistema deve ter cara de produto bem acabado, no celular e no computador.

**Sucesso:**
- páginas públicas, login e área do almoxarifado seguem o Clean, com um vocabulário de CSS
  próprio;
- comportamento, fluxos, URLs e textos continuam os mesmos, salvo onde está dito abaixo;
- a suíte de testes segue verde.

### Decisões tomadas

| Tema | Decisão |
|---|---|
| Escopo | Páginas públicas (início, formulários, sucesso), login, área do almoxarifado (casca, painel, detalhe/atendimento, saída avulsa, recibos, catálogo). Fora: admin do Django e páginas 404/500. |
| Abordagem | Vocabulário de CSS **novo**: CSS, `shell.js` e templates reescritos; da fundação do WMS só ficam as template tags de paginação e ordenação que continuarem em uso (`interface_extras.py`). |
| Tema | **Só claro.** Sai a alternância claro/escuro (botão, chave `almox-tema`, script anterior à pintura). |
| Fontes | Geist (títulos), DM Sans (texto), Geist Mono (códigos), **servidas localmente** em `.woff2` (OFL). Nada de Google Fonts ou CDN. |
| Destaque | Azul do guia `#2563EB` (hover `#1D4ED8`) em botões primários, links e foco. |
| Densidade | **Dois ritmos** com os mesmos tokens: público arejado (corpo 17px); almoxarifado compacto (corpo 15px, tabelas densas). |
| Skill | `.claude/skills/clean-design/` versionada, para telas futuras seguirem o mesmo estilo. |

### Fora do escopo

- Seções de landing page do guia (hero com prova social, preços, depoimentos, FAQ, marquee).
- *Scroll reveal* e animações de entrada em listas: atrapalham um sistema de uso diário.
- Mudanças de regra de negócio, de URL ou de texto (exceto as listadas na seção 5).

## 2. Fundação

### Arquivos

Saem `interface/static/interface/css/tokens.css`, `base.css`, `components.css` e
`publico.css`. Entram, em `interface/static/interface/css/`:

- `clean.css`: reset, `@font-face`, tokens (`:root`), tipografia, foco, utilitários
  (`.mono`, `.visually-hidden`, `.texto-suave`, `.rotulo-secao`), ritmos.
- `componentes.css`: botões, campos, cards, badges, avisos, tabela, paginação, filtros, passos
  numerados, lista de resultados e carrinho, estado vazio.
- `layouts.css`: layout público (`.publico-*`) e casca do almoxarifado (`.app-*`), menu móvel
  e impressão.

`pedidos/static/pedidos/css/pedidos.css`, `catalogo/static/catalogo/css/catalogo.css` e
`contas/static/contas/css/entrar.css` são reescritos em cima do novo vocabulário e ficam só
com o que é próprio de cada app.

### Tokens

- **Neutros (do guia):**
  - fundo `#FFFFFF`;
  - superfície alternada `#F7F6F2`;
  - texto `#0F0E0C`, texto secundário `#6B6760` e texto suave `#A8A49F`;
  - borda `#E8E6E1`.
- **Destaque:** `#2563EB`; hover `#1D4ED8`; texto sobre o destaque `#FFFFFF`; superfície
  `#EFF4FF`.
- **Status** (sempre com texto, nunca só cor), cada um com superfície clara e texto escuro da
  mesma família:
  - ok: `#ECF7EE` / `#1E6B34`;
  - aviso: `#FDF4E3` / `#8A5A00`;
  - erro: `#FCEDEC` / `#A3261D`;
  - informação: superfície do destaque / `#1D4ED8`;
  - neutro: `#F7F6F2` / `#6B6760`.
  - O contraste do texto sobre a superfície atende WCAG AA.
- **Espaço:** múltiplos de 8 (`--esp-1` = 8px … `--esp-16` = 128px), com `--esp-meio` = 4px
  para ajustes finos.
- **Raios:** cards 12px; botões e campos 8px; badges 100px.
- **Sombras (do guia):**
  - card `0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.04)`;
  - hover `0 6px 20px rgba(0,0,0,.08)`;
  - painel elevado `0 8px 30px rgba(0,0,0,.09)`.
- **Tipografia:**
  - Geist 600/700 nos títulos, com tracking negativo (-0.02em);
  - DM Sans 400/500/600 no texto, entrelinha 1.6;
  - rótulo de seção: DM Sans 500, 12px, maiúsculas, tracking 0.08em, cor suave;
  - Geist Mono 400/500 para CADPRO, Nº, placa, matrícula e requisição.
- **Ritmos:**
  - `.ritmo-publico`: corpo 17px, H1 `clamp(32px, 5vw, 48px)`, cards com recheio de 32px,
    blocos separados por 48 a 64px;
  - `.ritmo-almox`: corpo 15px, H1 24px, cards com recheio de 24px, células de tabela 10px/12px.

### Fontes

Arquivos `.woff2` com subconjunto latino em `interface/static/interface/fonts/`:
- Geist 600 e 700;
- DM Sans 400, 500 e 600;
- Geist Mono 400 e 500.

Cada `@font-face` usa `font-display: swap`. A licença OFL de cada família entra em
`THIRD-PARTY-NOTICES.md`, e os arquivos de licença ficam ao lado das fontes.

### Ícones

`interface/templates/interface/_icone.html` (`{% include "interface/_icone.html" with nome="busca" %}`):
- SVG inline no estilo Lucide: viewBox 24, `stroke="currentColor"`, traço 1.5, pontas
  arredondadas, `aria-hidden="true"`;
- conjunto fechado: `caixa`, `busca`, `mais`, `menos`, `lixeira`, `impressora`, `sair`,
  `seta-direita`, `seta-esquerda`, `alerta`, `check`, `menu`, `fechar`, `painel`, `recibo`,
  `catalogo`, `cadastros`, `saida`;
- nome desconhecido não renderiza nada; um teste cobre isso;
- sem emoji na interface. O texto do aviso no Telegram (📦, 📝) não é interface e fica como
  está.

### Movimento

- Transições de 0.18s em hover e foco; `transform: scale(.98)` no clique dos botões.
- O cartão de sucesso do pedido entra com `fadeUp` de 0.4s.
- `@media (prefers-reduced-motion: reduce)` zera transições e animações.

### Regras do projeto que continuam

- Estado nunca só por cor.
- Códigos em `.mono`.
- Foco visível: anel de 2px no destaque, com 2px de afastamento.
- Alvos de toque com no mínimo 44px no celular.
- Tabelas com rolagem lateral no celular.
- Scripts no `<head>` com `defer`.
- Logout por POST num formulário único.
- O `htmx-config` com `noSwap` para 4xx/5xx continua no `base.html`.

## 3. Páginas públicas e login

Todas com `.ritmo-publico` e coluna central de até 720px.

- **Cabeçalho público:**
  - ícone `caixa` e "Central Almoxarifado" (Geist 600);
  - à direita, o link "Área do almoxarifado";
  - uma linha de borda embaixo.
- **Rodapé:** texto suave, com o mesmo link. O botão de tema some.
- **Início:**
  - rótulo "ALMOXARIFADO SAEP", H1 "Pedir materiais ao almoxarifado" e o subtítulo atual;
  - dois cartões-link (`.cartao-opcao`), cada um com ícone, rótulo "FORMULÁRIO 1/2", título,
    descrição e `seta-direita`, que anda 4px no hover. O cartão sobe 2px no hover;
  - os cartões ficam empilhados abaixo de 640px;
  - a nota "Enviar um pedido não é a saída do material…" em texto pequeno e suave.
- **Formulário (limpeza e AB):**
  - cabeçalho com rótulo "FORMULÁRIO 1/2", H1 com o título do fluxo e link
    "Trocar tipo de material" com `seta-esquerda`;
  - bloco de erros no **topo** do formulário (`.aviso-erro`, `role="alert"`), com a mensagem
    e a lista; a caixa `[data-erro-envio]` também fica no topo;
  - três **passos numerados** (`.passo`): número grande em Geist e cor suave (`01`, `02`,
    `03`) à esquerda do título; no celular, o número fica acima do título;
    - **01 Quem pede:** "Nome completo *";
    - **02 Materiais:**
      - busca com ícone `busca` dentro do campo;
      - o filtro (categoria ou grupo) **acima da busca, recolhido num `<details>`** (revisto em
        13/10/2026; antes ficava num `<select>` ao lado): o resumo é um botão compacto
        "Grupo e subgrupo: Todos" que mostra o grupo escolhido, em azul quando há um; abrir o
        filtro já abre a lista de grupos, e escolher fecha o filtro e abre os resultados logo
        abaixo da busca. A busca fica em coluna única em todas as larguras. A lista de grupos
        é uma árvore (`data-dropdown-arvore` no `dropdown.js`), sem caixa de busca: cada grupo é
        uma pasta fechada, com a quantidade de subgrupos, que abre na seta ou com → e mostra os
        subgrupos ligados por ├─ └─; escolher a pasta escolhe o grupo inteiro. Os nomes aparecem
        só com a primeira letra maiúscula (filtro `frase`), e o grupo com um único subgrupo de
        mesmo nome fica sem filhos;
      - lista de resultados (`.lista-materiais`): cada linha com nome, código em mono e
        estoque ou unidade em texto suave; à direita, o controle de quantidade (`menos`,
        campo, `mais`) e o botão "Adicionar";
      - item bloqueado: texto suave e badge de aviso com o motivo, sem controles;
      - o contador "N materiais" / "Mostrando 50 de N…" acima da lista;
    - **"Seu pedido (N)"** (`.carrinho`, fundo `#F7F6F2`, raio 12px):
      - linhas com nome, código, quantidade e unidade, e "Remover" como botão de texto com
        ícone `lixeira`;
      - "Corrigir" como badge de erro, com borda de erro na linha;
      - vazio: "Nenhum material adicionado ainda.";
    - **03 Entrega:** "Destino dos materiais *" (com a datalist na limpeza) e "Observação";
  - botão primário "Enviar pedido" (ou o rótulo do caso divergente), com largura total abaixo
    de 640px.
- **Sucesso:**
  - card centralizado com ícone `check` em círculo neutro;
  - rótulo "PEDIDO REGISTRADO" / "PEDIDO JÁ ESTAVA REGISTRADO";
  - o número em Geist Mono, 40px;
  - o resumo, a nota do Telegram e o aviso "Guarde o número…";
  - botões "Fazer outro pedido" (primário) e "Voltar ao início" (secundário).
- **Indisponível:** aviso de atenção com ícone `alerta` e o texto atual, sem formulário.
- **Login:**
  - página sem barra lateral, fundo `#F7F6F2`;
  - card de 400px centralizado com a marca, o título "Área do almoxarifado", os campos
    "Matrícula" e "Senha" e o botão primário "Entrar" de largura total;
  - o erro em `.aviso-erro` no topo do card e o texto de recuperação em texto suave.

## 4. Área do almoxarifado

Todas com `.ritmo-almox`.

- **Casca:**
  - **barra lateral branca** de 248px, com borda à direita:
    - marca no topo;
    - itens de `ITENS_MENU` com ícone, cada item ganhando um campo `icone` em `ItemMenu`:
      Painel `painel`, Saída avulsa `saida`, Recibos `recibo`, Catálogo `catalogo`,
      Cadastros `cadastros`;
    - item atual em fundo `#F7F6F2`, texto principal, marcador de 3px no destaque à
      esquerda e `aria-current="page"`;
    - no pé, o nome e a matrícula do usuário e o botão "Sair" (`sair`) no formulário POST
      único;
  - **área de trabalho** em fundo `#F7F6F2`, com o conteúdo em cards brancos;
  - **cabeçalho da página:** rótulo opcional, H1, subtítulo em texto suave e ações à direita;
  - **abaixo de 900px**, a barra lateral vira cabeçalho com `menu`/`fechar`. O
    `shell.js` fica só com o menu móvel.
- **Painel:**
  - ações "Saída avulsa" (primário, ícone `mais`) e "Imprimir recibos pendentes (N)"
    (secundário, `impressora`) ou o texto suave "Nenhum recibo pendente";
  - card "Saúde do catálogo": "Catálogo em dia." com ícone `check`, ou a lista com badges,
    e o link "Ver catálogo";
  - faixa de filtros (`.filtros`) em card: busca com `busca`, Origem, Situação do pedido,
    Integração SCPI, De, Até, o botão "Filtrar" e o link "Limpar filtros";
  - tabela densa em card:
    - cabeçalho em versalete 12px suave;
    - linhas com hover `#F7F6F2`;
    - Nº em mono, como link no destaque;
    - origem em badge neutro e situações em badges-pílula de status;
  - paginação: anterior/próxima e números, página atual em fundo escuro. A estrutura e os ids
    estáveis de hoje se mantêm.
- **Detalhe do pedido:**
  - ações "Imprimir recibo" (primário, `impressora`), "Registrar outra saída" (na avulsa) e
    "Voltar ao painel" (secundário, `seta-esquerda`);
  - linha "Registrado por…" / "Atendido por…" em texto suave (`.nao-imprimir`);
  - card do recibo (`_recibo.html`):
    - cabeçalho com rótulo e Nº em Geist Mono 28px;
    - dois quadros (situação do pedido e integração com o SCPI) com badge e descrição;
    - os dados em grade de rótulo e valor, com o rótulo em versalete suave;
    - a tabela de materiais;
    - o bloco "Saída registrada";
    - as assinaturas;
  - card "Confirmar atendimento":
    - campos da saída em grade de duas colunas, uma no celular;
    - o botão de texto "Quem recebe é o solicitante (…)";
    - a lista "Quantidade entregue por material", com o pedido em texto suave e o campo
      alinhado à direita;
    - a caixa "Não lançar no SCPI", com a descrição "Use para material fora de estoque.";
    - erros em `.aviso-erro` acima do botão;
    - o botão primário "Confirmar e registrar saída".
- **Saída avulsa:**
  - passos "01 Dados da saída" e "02 Materiais", com os mesmos componentes de busca,
    resultados e "Seu pedido" do formulário público;
  - botão primário "Registrar saída".
- **Catálogo:** mesma página de hoje, com o botão "Atualizar agora", o card de saúde e a
  tabela de importações nos componentes novos.
- **Recibos:**
  - na tela, uma barra com "Imprimir" (primário) e "Os recibos saíram na impressora — marcar
    como impressos (N)" (secundário), e os recibos em cards;
  - na impressão: sem fundos nem sombras, texto preto, bordas finas, um recibo por folha,
    `.nao-imprimir`/`.so-tela` escondidos, e a casca (barra lateral, cabeçalho, mensagens)
    escondida.

## 5. Mudanças de comportamento

- Botões − e + na quantidade dos resultados de busca (formulários públicos e saída avulsa),
  só no navegador (`pedidos.js`). O inteiro sobe ou desce de 1, com mínimo de 1; no decimal,
  o − e o + mexem na parte inteira, também com mínimo de 1. Nada muda no servidor.
- Sai o botão de tema e a leitura de `almox-tema`.
- O filtro de busca deixou de ficar escondido num `<details>` e, em 13/10/2026, voltou a ser
  recolhido, agora acima da busca e com um resumo que mostra o grupo escolhido (o
  `<details>` antigo escondia o filtro sem dizer qual estava valendo).

## 6. Testes e verificação

- A suíte atual continua valendo.
  - Asserções que procuram classe ou HTML da fundação antiga (`class="side`, `error-box`,
    `alert-info`, `badge-*`, `pagination-*` etc.) são atualizadas para o vocabulário novo,
    sem perder o que verificam.
  - Os testes de template tags do WMS (`tests/test_interface.py`) continuam enquanto as tags
    existirem; tag sem uso sai junto com o teste.
- Testes novos:
  - nenhuma página carrega `data-theme-toggle` nem `almox-tema`;
  - `clean.css`, `componentes.css`, `layouts.css` e cada `.woff2` são achados pelo
    `staticfiles`;
  - `_icone.html` renderiza um SVG `aria-hidden` para um nome conhecido e nada para um nome
    desconhecido;
  - o item atual do menu traz `aria-current="page"` e o ícone.
- Conferência visual: o servidor sobe e o usuário confere (esta sessão não tem navegador). É
  preciso olhar 375px, 768px e 1280px, o formulário inteiro, o painel e a pré-visualização de
  impressão dos recibos.
- `collectstatic` depois da troca, para o teste que lê o manifesto (`test_config`).

## 7. Documentação

- `docs/DESIGN.md` é reescrito: o Clean aplicado ao sistema (tokens, componentes, ritmos,
  ícones e regras).
- A spec principal (`2026-10-10-central-almoxarifado-django-design.md`, seção 2, "Interface"
  e "Decisões já tomadas") passa a citar o Clean no lugar da fundação do WMS-Almoxarifado.
- `CLAUDE.md`: o parágrafo de `interface` é atualizado (sem tema escuro; vocabulário Clean; a
  skill `.claude/skills/clean-design/`).
- `THIRD-PARTY-NOTICES.md`: sai o aviso MIT do WMS/django-observatory se não sobrar código
  copiado; entram as licenças OFL das fontes. As template tags copiadas do WMS que continuarem
  em uso mantêm o aviso.

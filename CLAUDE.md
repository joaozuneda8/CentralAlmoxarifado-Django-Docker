# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O projeto

Reescrita em Django do Central Almoxarifado (hoje Google Apps Script + Google Sheets), sem
nenhuma dependência do Google. Fluxo: funcionários fazem pedidos em formulários públicos → o
almoxarifado atende → as saídas viram linhas que um robô (Playwright) lança no SCPI.

- Spec principal: `docs/superpowers/specs/2026-10-10-central-almoxarifado-django-design.md`.
  As decisões posteriores estão nas specs mais novas de `docs/superpowers/specs/` e de `specs/`,
  que vencem a principal onde a alteram. A seção 9 divide o trabalho em 5 subprojetos, cada um
  com plano próprio em `docs/superpowers/plans/`. Os subprojetos 1 (Fundação), 2 (Catálogo e
  importadores), 3 (Pedidos) e 4 (Lançamento no SCPI) estão feitos; o 5 (implantação e
  migração) também: o código (app `implantacao`, `deploy/`, `LANCAMENTO_REAL`), a instalação no
  servidor e a virada (`deploy/VIRADA.md`, que tem a situação de cada passo). A implantação é
  em Docker Compose (`docs/superpowers/specs/2026-10-15-docker-design.md`), no lugar do
  NSSM e do Agendador do Windows da spec principal. O Django é o sistema em uso, em produção com
  dados reais; o Apps Script está congelado e arquivado, e o robô antigo, desativado. A
  simulação do 4 contra o SCPI real (`lancar_saidas --dry-run`) já passou; falta liberar o
  lançamento real e conferir o primeiro (`deploy/VIRADA.md`, seção 6). Até lá, nenhum robô lança
  no SCPI e as saídas ficam na fila como `PENDENTE`.
- Pendências conhecidas ficam nas issues do GitHub, não neste arquivo nem nas specs.
- Referências fora deste repositório: o Apps Script antigo, arquivado (`../CentralAlmoxarifado`,
  com `Regras.gs`, `Catalogo.gs` e os testes em Node), o WMS-Almoxarifado
  (`joaorighetto/WMS-Almoxarifado`), de onde veio a fundação visual, e o extrair-relatorio
  (`joaorighetto/extrair-relatorio`, privado), de onde veio o código do SCPI.

## Comandos

Exigem um MySQL 8 ou MariaDB local (o SQL de criação do banco e do usuário está no README) e
um `.env` copiado de `.env.example`.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest                                   # suíte inteira
uv run pytest tests/test_acesso.py::test_painel_exige_login   # um teste
uv run ruff check . && uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
uv run playwright install chromium              # uma vez, para os robôs do SCPI
uv run python manage.py importar_estoque --arquivo tests/fixtures/scpi/estoque.csv
```

`uv run python manage.py lancar_saidas --dry-run --limite 1` abre o SCPI, preenche a primeira
requisição pendente e a descarta sem salvar; **sem `--dry-run` lança de verdade no SCPI**, e só
com `LANCAMENTO_REAL=1` no `.env` (sem ele, o comando recusa).

Comandos da implantação (app `implantacao`): `importar_planilhas --arquivo <xlsx> [--dry-run]`
importa o `.xlsx` exportado das planilhas do Apps Script (migração única; o `--dry-run` é um
ensaio fiel: roda a gravação numa transação e a desfaz, com as travas e as restrições do banco);
`backup_banco` faz o dump
comprimido em `BACKUP_DIR` e apaga os de mais de 60 dias (a senha vai num arquivo de opções
temporário, `--defaults-extra-file`, nunca nos argumentos nem no ambiente); `robos_em_andamento` sai com erro se há
lançamento ou importação em andamento (o `deploy/atualizar.sh` o usa);
`importar_depara --arquivo <xlsx> [--dry-run]` carrega os pares de/para da planilha MAPEAMENTO
DE/PARA CONSOLIDADO (carga única). No servidor os comandos rodam no container
(`docker compose exec web python manage.py ...`), não pelo `uv run`.

Os comandos `importar_cadastro`, `importar_estoque`, `importar_saidas_scpi` (`--desde`/`--ate`)
e `atualizar_catalogo` (os três em sequência, num navegador só; com `--carga-inicial`, o cadastro
inteiro e as saídas desde `curva.INICIO_DADOS_CONFIAVEIS`, também no botão "Carga inicial
completa" da página Automações) abrem o SCPI pelo Playwright; com `--arquivo`
leem um CSV já baixado. Os testes nunca abrem o navegador.

O pytest usa `config.settings_test` (definido no `pyproject.toml`) e cria o banco
`test_almoxarifado`. Testes rodam contra MySQL/MariaDB, nunca SQLite: `select_for_update` e
transações precisam se comportar como no servidor. O
`test_config.py::test_atras_do_apache_com_waitress_documentado_nao_entra_em_laco` abre uma
página com a configuração de produção (`DEBUG=0`, estáticos com manifesto) num subprocesso e lê
o manifesto de `staticfiles/`: depois de mexer em estáticos, rode
`uv run python manage.py collectstatic --noinput` antes da suíte, senão ele falha com a entrada
que falta no manifesto.

## Arquitetura

- `config/settings.py` é um módulo único para todos os ambientes, lido do `.env`
  (`python-dotenv`; variável já presente no ambiente vence) via `config/env.py`
  (`ler_bool`, `ler_lista`). Com `DEBUG=0` ligam as proteções de produção e
  `check --deploy` precisa passar sem avisos (há um teste para isso). `settings_test.py` ajusta
  o hasher, os cookies seguros, o storage de estáticos (sem manifesto, com
  `WHITENOISE_AUTOREFRESH`), uma `SECRET_KEY` padrão, o Telegram vazio, o site na raiz
  (`PREFIXO_URL`, `FORCE_SCRIPT_NAME`, `STATIC_URL`) e `LANCAMENTO_REAL=True`.
- A área interna (login, painel, automações, curva ABC e saída avulsa) fica em
  `/painel/`, e o admin em `/admin/`; os formulários públicos ficam na raiz. Os nomes das rotas
  não mudam (as páginas Catálogo e Lançamentos SCPI foram apagadas, com suas rotas, quando viraram
  Automações). O site sai atrás do Apache em `/almoxarifado` (`--url-prefix` do waitress), o que dá
  `servidor/almoxarifado/` (formulários), `servidor/almoxarifado/painel/` e
  `servidor/almoxarifado/admin/`; o login é `/painel/entrar/`. O prefixo vem de duas pontas que
  precisam bater: o `--url-prefix=/almoxarifado` do waitress (que passa `SCRIPT_NAME` a cada
  pedido) e o `PREFIXO_URL=/almoxarifado` do `.env`, que vira `FORCE_SCRIPT_NAME` e o `STATIC_URL`. O
  `STATIC_URL` é lido na partida, antes de qualquer pedido: só com o `--url-prefix` os links
  dos estáticos sairiam como `/static/...`, fora do `/almoxarifado`, e o Apache os recusaria.
  Nenhum template tem caminho fixo (`tests/test_prefixo.py`). O guia de instalação é
  `deploy/INSTALACAO.md`.
- A variável que liga o HTTPS se chama `USAR_HTTPS`, nunca `HTTPS`: o wsgiref do `runserver`
  copia `os.environ` para a requisição, e `HTTPS=1` faria tudo parecer https e quebraria o
  CSRF. Atrás do Apache, o waitress precisa de
  `--trusted-proxy=<proxy> --trusted-proxy-headers="x-forwarded-proto x-forwarded-for"`
  (no compose, `<proxy>` é `*`: o Apache chega por um IP interno do Docker que muda)
  junto com `PROXY_HTTPS=1`: sem o primeiro cabeçalho o redirecionamento para https entra em
  laço; sem o segundo, todo pedido parece vir do Apache e divide um único limite por IP.
- `contas.Usuario` é o `AUTH_USER_MODEL`: `AbstractUser` com o `username` rotulado
  "matrícula". O login (`/painel/entrar/`) e o login do admin usam formulários próprios
  (`contas/forms.py`) só para a recusa sair em português correto.
- `interface` é só apresentação (sem modelos nem regras), no design system Clean (skill
  `.claude/skills/clean-design/`; regras e vocabulário de classes em `docs/DESIGN.md`):
  `clean.css` (tokens, fontes, tipografia e os ritmos `ritmo-publico`/`ritmo-almox`),
  `componentes.css` e `layouts.css`, ícones Lucide em `_icone.html`, fontes `.woff2` locais
  (Geist, DM Sans, Geist Mono), HTMX 4.0.0 vendorizado, parciais e template tags. Só tema
  claro; o `shell.js` só cuida do menu móvel. O `dropdown.js` troca todo `select.campo-entrada` e
  `input.campo-entrada[list]` por um painel no estilo do de resultados da busca de materiais, sem
  caixa de busca (no `select`, digitar pula para a opção que começa com o texto); é a base de todo
  painel flutuante: a casca (`.painel-flutuante`, em `componentes.css`) e o abrir e fechar animados
  (`window.Dropdown.abrirPainel`/`fecharPainel`) também servem ao painel de resultados da busca de
  materiais (`pedidos.js`), e os tipos (select, campo com lista, select digitável, árvore) só montam o controle; o
  elemento original fica escondido e continua guardando o valor e disparando `change` (script
  que troca o valor de um `select` precisa disparar `change`). O `abas.js` (`[data-abas]`, `?aba=` na URL) dá as abas em pasta: a ativa se funde ao primeiro cartão
  do painel. O `filtros.js` recolhe o painel de
  um `form[data-filtros]` (filtros do painel de pedidos e do histórico de Automações): botão com a contagem, estado lembrado no
  `localStorage` e, fechado, um chip por filtro ativo; sem JavaScript o painel fica aberto. Dois layouts: `base_publico.html` (sem login,
  pensado para o celular) e `base_almoxarifado.html` (barra lateral), os dois com o bloco `voltar`
  (`link-voltar`, acima do rótulo; no almoxarifado, "Voltar ao painel" por padrão, vazio no painel). Cada subprojeto
  acrescenta seus destinos (com ícone) a `ITENS_MENU` em `interface/navegacao.py`. Scripts
  ficam no `<head>` com `defer`, nunca no `<body>` (o HTMX re-executa scripts do corpo ao
  restaurar o histórico).
- `pedidos/regras.py` recebe as regras de negócio de `Regras.gs`/`Util.gs`: funções puras, sem
  ORM, traduzidas uma a uma com os mesmos resultados e textos de erro (só os que citavam abas
  da planilha mudaram). Quantidades são `Decimal` (pt-BR estrito, "1.5" é recusado).
- `pedidos/servicos.py` é o único lugar que grava pedidos: `registrar_pedido`,
  `confirmar_atendimento`, `registrar_saida_avulsa` e `marcar_recibos_impressos`, cada um numa
  transação. Todo registro trava a linha única da `Sequencia` (`select_for_update`), que numera
  P- e AV- juntos e serializa os envios; o atendimento trava o pedido. O `Pedido.id` é o
  identificador do envio, gerado quando a página abre: reenvio igual confirma, diferente é
  "divergente", e nada duplica. Erro de negócio volta numa `Resposta` com a lista de erros. O
  aviso no Telegram (`telegram.py`) sai por `transaction.on_commit` e nunca desfaz o pedido.
- Formulários públicos (`views/publico.py`): token assinado com o envio e o momento da
  abertura, campo isca e tempo mínimo (`protecao.py`); limites por IP e por nome contados no
  banco (`settings.PEDIDOS_*`). O envio vai pelo HTMX e a resposta substitui o formulário; o
  `htmx-config` do `base.html` impede que respostas 4xx/5xx apaguem a página. Busca de
  materiais e carrinho (`fluxos.py`, `carrinho.py`, `views/materiais.py`) são comuns a limpeza,
  AB e saída avulsa: o carrinho vive em campos escondidos e o servidor não guarda estado. A busca
  lista primeiro o que pode ser pedido e os bloqueados no fim, antes do corte de 50. Para o
  funcionário, os formulários se chamam "Limpeza, copa e escritório" e "Ferramentas, peças e
  materiais" (`Fluxo.titulo`); o nome interno (painel, Telegram, `Pedido.Origem`) continua
  "Materiais AB". `regras.Erro` tem `campo` (`solicitante`, `destino`, `obs`) nos erros de um campo:
  a view monta `erros_por_campo`, e o formulário mostra o resumo no topo (focado pelo `pedidos.js`,
  com link para o campo) e o erro embaixo do próprio campo. No celular, a gaveta do pedido envia
  (`data-carrinho-enviar`, que aciona o botão do fim do formulário por `requestSubmit`; esse botão
  fica escondido com JavaScript e só aparece sem ele), também na saída avulsa, com os textos da
  saída (`Fluxo.rotulo_carrinho` e afins: "Materiais da saída", "Revisar e registrar"). O "Nome completo" é texto livre, sem sugestões de nomes. O `pedidos.js`
  lembra no `localStorage` do aparelho (`almoxarifado.solicitante`) o último nome digitado (gravado
  ao digitar) e o destino do último pedido registrado (gravado pela tela de sucesso,
  `data-lembrar-*`), preenche só campos vazios e pede confirmação (`beforeunload`) para
  sair com material no pedido. Nos formulários públicos e na saída avulsa, adicionar tem dois passos
  (`[data-adicionar]` em `_resultados.html`): tocar na linha do material (o `material-abrir`, um botão
  transparente esticado sobre a linha; o "+" só indica que clica) abre a quantidade, que se confirma
  (o `hx-post` de sempre) ou, com o material já no pedido (selo azul claro "N no pedido" ao lado da
  informação, `data-selo-pedido`), "Atualizar" troca a linha do pedido; tocar de novo na linha aberta a
  fecha. Aberta, a linha mostra a quantidade à esquerda e o "Confirmar" no canto inferior direito, com o
  ✕ vermelho no superior direito; as outras linhas recuam (opacidade 0,6) mas seguem clicáveis. A
  informação do material quebra por dentro e o selo desce para a linha de baixo quando a unidade é
  longa (limpeza). Sem JavaScript a quantidade fica à vista, e o painel do atendimento (`um_passo`)
  adiciona ou troca direto, com botão. A coluna do `.passo-corpo` é `minmax(0, 1fr)`, para a busca não
  alargar com o conteúdo. O painel de resultados fica no fluxo da página, em qualquer tela (nunca
  absoluto: o cartão do passo cresce com ele, sem painel pendurado para fora); ao abrir, o pedidos.js
  rola o campo ao topo (`trazerAoTopo`, descontando a barra do topo no celular) e dá ao painel a altura
  do cabeçalho e de 5 linhas (`alturaDoPainel`, `LINHAS_VISIVEIS`, `--busca-limite`), a mesma no
  computador, no tablet e no celular, medida de novo quando os resultados ou a largura mudam; o resto
  rola dentro do painel. Há duas buscas de materiais: a pública (formulários) não mostra código nem
  grupo; a do almoxarifado (saída avulsa e atendimento) mostra. A linha do pedido
  (`_carrinho.html`) tem o mesmo desenho do resultado da busca, na coluna do desktop, no tablet e na
  gaveta do celular: a linha inteira abre a quantidade (`material-abrir`, `data-alterar-abrir`; o lápis
  só indica que clica), com a quantidade e o "Remover" embaixo; aberta, o − / + fica à esquerda, o
  "Confirmar" à direita (no lugar do "Remover") e o ✕ vermelho em cima, com a barra azul à esquerda e as
  outras linhas recuadas, mas clicáveis. O campo só manda o `alterar` no "Confirmar"
  (`hx-trigger="confirmar-quantidade"`), também na saída avulsa.
- Área do almoxarifado (`views/almoxarifado.py`): painel com filtros em SQL
  (`consultas.py`, que repete `regras.situacao_*` como `Exists`; um teste confere que
  concordam), detalhe com o atendimento, saída avulsa e recibos (`_recibo.html`, que nunca
  mostra quem registrou). Não há página de recibos: o "Imprimir recibo" do detalhe imprime a própria
  página (`data-imprimir`, escondido sem JavaScript) e, depois, mostra ali a confirmação de impresso
  (`marcar_impressos`); o atalho do painel filtra os não impressos (`?recibo=pendente`). Cada material entregue vira uma `LinhaSaida` (`PENDENTE`, ou
  `NAO_LANCAR` com a opção marcada): é o contrato com o robô do subprojeto 4. Na área interna a
  unidade é a do cadastro do SCPI (`consultas.unidades_scpi`), nunca a unidade exibida do
  formulário de limpeza (`ItemPedido.unidade`, que só vale para código fora do cadastro), e vai
  dentro do campo da quantidade entregue. Com JavaScript, cada quantidade entregue é confirmada
  ("Confirmar" ou Enter; o − e o + somem e a própria caixa, com um lápis, vira o "Alterar", com o lugar do "Confirmar" guardado; inválida ou acima do pedido não confirma;
  "Entregar tudo" preenche e confirma) e o `pedidos.js` barra o envio com alguma pendente.
  No atendimento, o almoxarifado troca um material pedido por outro ou acrescenta um
  (`ItemPedido.origem` `PEDIDO` ou `ALMOXARIFADO`; o acrescentado tem `qtd_pedida` nula,
  `adicionado_por` e, na troca, `no_lugar_de`, e o trocado fica com 0 sem deixar o pedido parcial),
  do catálogo da saída avulsa, sem limite de estoque. A busca (`atendimento_materiais`) e o
  "Adicionar" (`atendimento_adicionar`, que devolve a linha `_adicionado.html` ou a recusa para
  `#adicionar-erro`) não gravam nada: as linhas vivem em campos escondidos do formulário do
  atendimento (`adicionado`, `no-lugar-de-<codigo>`) e só o envio grava. O `pedidos.js` abre o
  painel de busca embaixo do material trocado, zera e confirma o trocado já ao abrir a troca (o "Cancelar troca" devolve a quantidade e a confirmação; a quantidade de antes
  fica em `data-qtd-antes`, para o "Desfazer troca"; até lá o trocado fica travado, sem o lápis,
  e "Entregar tudo" o pula; o servidor também recusa trocado com quantidade maior que 0),
  anuncia cada mudança no `role="status"` da
  tabela e reaplica tudo na página devolvida pela recusa. O recibo separa "Pedido pelo solicitante"
  de "Adicionado pelo almoxarifado" e nunca mostra quem acrescentou. Três travas contra linha de
  saída com quantidade ≤ 0: `servicos._gravar_linhas`, `scpi/requisicoes.py` (lote vira `ERRO`) e
  a `CheckConstraint` `qtd > 0` da `LinhaSaida`.
- Edição do atendimento (spec `2026-10-17-edicao-pedido-design.md`): até o robô lançar o lote, o
  "Editar atendimento" ("Editar saída" na avulsa) do detalhe abre `pedidos:editar`
  (`/painel/pedidos/<n>/editar/`), o formulário do atendimento (ou o da saída avulsa) preenchido
  com o que está gravado (`editando`). Edita só o que o atendimento grava (dados da saída,
  quantidades entregues, trocas e acréscimos); o que veio do funcionário (cabeçalho, materiais e
  quantidades pedidas) nunca muda. `regras.edicao_permitida` (puro) diz pelas linhas do lote se
  edita (`PENDENTE`, `NAO_LANCAR`, `ERRO` sem número), se está suspensa (`EM_LANCAMENTO`,
  `VERIFICAR`) ou bloqueada (lançada ou com número). `servicos.editar_atendimento` e
  `editar_saida_avulsa` travam o pedido e as linhas, conferem a `Pedido.versao` (concorrência
  otimista: outra pessoa salvou antes é recusa `versao`; o reenvio igual é sucesso), recusam o lote
  que entrou em lançamento (`lancamento`), validam como o atendimento, gravam a `AlteracaoPedido`
  (diferenças de `regras.diferencas_atendimento`, só na tela, nunca no recibo), devolvem o recibo a
  "não impresso" e **apagam e recriam as `LinhaSaida`**: com IDs novos, o robô que leu o lote antes
  da edição o pula no `_travar`; nunca atualize as linhas no lugar. `ERRO` volta a `PENDENTE`. O
  "Saiu na impressora" leva a versão (`versao-<atendimento>`) e não marca a versão nova. No modo de
  edição o `pedidos.js` abre as quantidades confirmadas, destaca o campo alterado, conta as
  alterações e pede confirmação para sair; com o robô rodando, a faixa (`_edicao_faixa.html`,
  `div#edicao-faixa` pelo `HX-Target`) se recarrega a cada 5 s e, se o lote travar, tira o
  "Salvar".
- `catalogo` guarda os cadastros. `Material` e `SaidaSCPI` vêm do SCPI pelos importadores e
  são só leitura no admin, como o registro de cada execução (`Importacao`). `ItemLimpeza`,
  `CentroCusto` e `Opcao` são mantidos à mão no admin. A placa do `CentroCusto` é normalizada
  (`norm_placa`), única no banco, e vazia vira NULL. `catalogos.py` monta os catálogos dos
  formulários (limpeza, AB pelo número de saídas consolidadas pelo de/para, avulsa) direto do
  banco, sem cache;
  `saude.py` diz o que está errado ou velho: `saude_do_catalogo` é a lista curta do painel e
  `situacao_do_catalogo` a mesma informação arrumada para a visão geral de Automações (uma linha
  por fonte de dados em colunas com cabeçalho: selo, fonte, o número em uso com o `complemento` mais
  apagado, "há quanto tempo" e uma ação, que leva aos avisos ou à aba do robô, "Tentar de novo" quando
  falhou; os avisos agrupados pelo começo do texto com
  `agrupar_avisos` e os números dos formulários; o erro inesperado do
  Playwright vira uma frase, `resumo_do_erro`, com o texto técnico recolhido). A visão geral tem o
  botão "Atualizar agora" (que inicia `atualizar_catalogo` em processo separado) e, recolhida, a
  carga inicial completa, que só inicia com a caixa "Estou ciente" marcada (`confirmar`). Cada robô
  de importação (Cadastro, Estoque, Saídas) tem sua aba em Automações, com um formulário de
  parâmetros (`catalogo/forms.py`: origem "baixar do SCPI" ou CSV enviado; no
  cadastro, o modo "só os novos" ou "recarga completa", com o "forçar" só se há material visível; no
  das saídas, o período). `automacoes.views.importar` valida e chama
  `scpi.disparo.iniciar_importacao`, que roda o comando do tipo em processo separado, com log próprio
  (`importar_<tipo>.log`) e uma importação por vez; o CSV enviado vai para `LOG_DIR/uploads` e o
  comando o apaga ao fim (`--apagar-arquivo`, mesmo se falhar). Os formulários ficam fora do trecho
  que o HTMX recarrega; o `importacoes.js` segue o `data-em-andamento` da situação para habilitar os botões.
- `automacoes` (sem modelos nem migrations) é a página Automações (`/painel/automacoes/`,
  `automacoes:pagina`), que junta o que eram as páginas Catálogo e Lançamentos SCPI: abas
  (`interface/js/abas.js`, `?aba=`) Visão geral, Lançamento no SCPI, Cadastro, Estoque e Saídas. A
  view só lê: `contexto_pagina` junta `contexto_catalogo`, `contexto_lancamento`, a linha do
  lançamento na visão geral (`visao_geral.linha_lancamento`, pura, ao lado das `saude.Fonte`) e o
  histórico; os parciais continuam em `catalogo/_situacao.html`, `catalogo/_robo.html` e
  `pedidos/_lancamentos.html`. As regiões que se recarregam sozinhas (situação a cada 5 s, também
  enquanto o lançamento roda; lançamento a cada 3 s; histórico a cada 5 s com a mesma query) pedem a
  própria página, e a view escolhe o trecho pelo cabeçalho `HX-Target` do HTMX 4 (`tag#id`,
  `REGIOES`). As ações (`atualizar`, `importar`, `lancar`, `resolver`) ficam aqui, com o mesmo corpo de
  quando eram das páginas antigas, e voltam para a aba de onde vieram. O histórico (`historico.py`)
  junta `Importacao` e `ExecucaoRobo`: filtros em SQL por modelo (`FiltrosHistorico`: busca no erro,
  nos avisos e no registro; robô; situação num vocabulário só, Concluída, Com avisos, Falhou,
  Interrompida e Em andamento, com "sem avisos" comparado como texto `"[]"`; período), e
  `SequenciaHistorico` intercala as duas por início e serve ao `Paginator` de 20; os filtros são
  os do painel (`filtros.js`) e cada aba tem "Ver histórico", que abre a lista filtrada pelo robô.
- `scpi` traz o código do extrair-relatorio. `browser.py` e `relatorios.py` (Playwright) vêm da
  navegação do original, com estas mudanças. As esperas pela geração do relatório são maiores
  (`ESPERA_GERACAO_*_MS`: o cadastro inteiro da primeira carga leva minutos). O `interceptar_csv`
  cancela o pedido do CSV (`route.abort`) depois de guardar os bytes: devolvido à página, ele virava
  um download que fechava o navegador. O `atualizar_catalogo` baixa os três relatórios num navegador
  só (`relatorios.sessao_compartilhada`, perfil `catalogo`, aberto só se algum relatório precisar;
  um relatório que falha descarta a sessão e o seguinte abre outra; enquanto ela existe, o
  `DJANGO_ALLOW_ASYNC_UNSAFE` fica ligado, porque a API síncrona do Playwright mantém um laço asyncio
  na thread e o Django recusaria as gravações); fora dele, cada comando abre e
  fecha o seu (perfil do tipo). O login (`abrir_sessao`) também acha os campos sem ID (o de senha, o último combo para o ano) e
  espera a tela parar de ser redesenhada: num perfil novo o SCPI a monta com outra numeração. Os
  campos do Relatório de Produtos são achados pelo que
  está na tela (legenda do quadro, rótulo acima do campo, `JS_CAMPO_ABAIXO_DO_ROTULO`), nunca pelo
  ID: o SCPI numera os IDs na ordem em que as telas são criadas na sessão, e a segunda abertura já
  tem outros; e cada relatório termina como começou ("Fechar relatório" e "Sair": reaberto, o
  formulário volta com os padrões). Sem nada no filtro o SCPI só avisa "Nada a exibir!!!"
  (`_gerar` clica OK): no cadastro o tipo é pulado, no estoque e nas saídas é erro. O cadastro pede
  um relatório por tipo de produto de `TIPOS_CADASTRO` (Produtos, Peças, Lubrificantes e Pneus, sem
  Serviços nem Combustíveis), trocando só o tipo no mesmo formulário; o `ler_cadastro` junta as
  linhas antes da gravação, inclusive no "só os novos", e descarta as dos `GRUPOS_DESCARTADOS` (o
  800, dos serviços, que o SCPI deixa sair nos tipos de produto; a coluna `GRUPO` é obrigatória),
  também no CSV enviado; o parcial sem nenhum material é sucesso com 0. `normalizadores.py` recola os registros quebrados
  em várias linhas; `leitura.py` (puro) vira bytes do CSV em linhas tipadas, achando as
  colunas pelo nome. Aceita o CSV do SCPI (`;`, campos sem aspas, recolado pelo
  `normalizadores.py`) e o mesmo relatório salvo por uma planilha (cabeçalho com `,`: lido pelo
  `csv` padrão, que trata aspas e quebras de linha dentro do campo, sem recolagem);
  `gravacao.py` grava; `execucao.py` registra cada execução em
  `Importacao`, com a gravação numa transação (falha não altera nada) e uma trava `GET_LOCK`
  por tipo (uma importação de cada tipo por vez, entre processos); "em andamento"
  (`Importacao.em_andamento`) vem dessa trava: sem sua trava ocupada, só a criada há menos de 60 s
  conta, e as demais (processo morto, janela fechada à força) aparecem como interrompidas e liberam
  os botões. Regras que valem:
  cadastro completo que deixaria de fora mais de 20% dos materiais visíveis aborta (salvo
  `--forcar`). O cadastro é carregado uma vez por inteiro (CSV enviado, sem datas) e depois o robô
  só traz os novos: sem datas e baixando do SCPI, o padrão é incremental (de 7 dias antes do corte
  da última carga bem-sucedida até hoje, `gravacao.periodo_cadastro_padrao`), que grava só o que o
  CSV traz e nunca oculta nem aborta (importação parcial, também com `--desde`/`--ate`). A recarga
  completa é explícita (`--completo`, ou `--forcar`; sem nenhuma carga anterior ou com `--arquivo`
  sem datas também é completa) e é a única que oculta o que sumiu. Período não combina com
  `--completo`/`--forcar`;
  material que some do cadastro fica oculto, nunca é apagado; estoque substitui todos os
  saldos (ausente = 0) e CSV vazio aborta; saídas voltam 7 dias antes do fim da última
  importação (o robô lança com a data efetiva) e não duplicam (`id_requi`, `cadpro`, `item`:
  o mesmo material repetido na requisição, com outra placa ou destino, é outra saída, numerada
  pela ordem no relatório; a requisição vem sempre inteira, então a numeração se repete).
  Códigos são comparados por `norm_u`, como a collation `utf8mb4_unicode_ci` do banco.
- Lançamento no SCPI (`lancar_saidas`, que abre o SCPI pelo Playwright): `scpi/requisicoes.py`
  (puro, sem ORM) agrupa as `LinhaSaida` `PENDENTE` por lote (um lote = uma requisição), valida
  cabeçalho e itens (centro de custo, tipo, CADPRO, quantidade no formato do SCPI) e deixa de
  fora o lote inteiro que tenha alguma linha `EM_LANCAMENTO`, `VERIFICAR` ou `ERRO` (as
  travas) ou `PENDENTE` já com número de requisição (já lançada); lote inválido vira `ERRO` sem abrir o navegador. `scpi/lancamento.py` fala com o SCPI
  pelo protocolo `SCPI` (o Playwright em produção, um simulado nos testes) e garante nunca
  lançar um lote duas vezes pela ordem das gravações: `EM_LANCAMENTO` é confirmado no banco
  (transação fechada, só se todas as linhas ainda estão `PENDENTE` e sem número de requisição)
  antes do clique em Salvar;
  qualquer falha depois do clique vira `VERIFICAR`, nunca `PENDENTE`; o número da requisição vai
  para o journal `logs/lancar_saidas_journal.jsonl` antes de ir para o banco, e se o banco
  recusar a gravação a execução para (`FalhaCritica`) com o lote travado. Uma trava `GET_LOCK`
  (`pedidos.models.TRAVA_LANCAMENTO`) permite uma execução por vez; a trava ignora o erro de
  banco (`django.db.Error`) ao ser liberada. `scpi/lancador.py` é a navegação copiada do
  extrair-relatorio (perfil do navegador em `SCPI_PERFIL_DIR/lancamento`; o `navegador()` liga o
  `DJANGO_ALLOW_ASYNC_UNSAFE` enquanto está aberto, `browser.orm_liberado`, como a sessão
  compartilhada do catálogo, porque o lançamento grava no banco com ele aberto); os testes só
  conferem a estrutura (implementa o protocolo, não importa o Playwright no topo), sem testes
  da navegação: só a simulação no SCPI real a exercita. `pedidos.ExecucaoRobo` registra cada execução (situação, resumo, log acumulado
  durante o laço, erro); o `--dry-run` preenche e descarta sem tocar em nenhuma linha. A aba
  Lançamento no SCPI de Automações (`pedidos/_lancamentos.html`) tem um formulário só: os botões
  "Simular" e "Lançar no SCPI" mandam o modo (`name="modo"`) e o limite "Só as primeiras [N]
  requisições" vale para o botão clicado (`pedidos/forms.py`; `--limite` no comando). A ação em
  destaque é a que dá para executar: com o lançamento real bloqueado, "Simular", e o "Lançar no
  SCPI" fica `aria-disabled` com cadeado e a dica do motivo, como no cartão do painel. O robô roda
  em processo separado (`scpi/disparo.py`, saída em `logs/lancar_saidas.log`). Logo abaixo dos
  botões fica a fila do robô (`consultas.fila_do_robo`: até 20 requisições e o total, em SQL que
  repete `requisicoes.agrupar`, a regra única do que está na fila; `tests/test_consultas_fila.py`
  confere que concordam). A última execução vira uma frase, com quem iniciou, a duração e só os
  contadores diferentes de zero (`pedidos/andamento.py`, puro); a falha é explicada em português
  (`explicar_falha`: erro conhecido como vem, "Falha inesperada:" vira erro do sistema ou demora
  do SCPI, processo que não subiu vira "não chegou a iniciar"), com o texto técnico e o registro
  num "Detalhe técnico" recolhido, "Simular de novo" só na simulação e, no lançamento real, o
  atalho para as travas. As execuções anteriores ficam no histórico de Automações. A aba atualiza
  a cada 3 s só enquanto há execução em andamento e resolve os lotes travados com
  `servicos.resolver_lote` (informar a requisição, liberar para relançar, o que apaga o número
  e a data de lançamento, ou marcar para não lançar; liberar um lote
  `VERIFICAR`/`EM_LANCAMENTO` exige marcar "Conferi no SCPI"; recusada com execução em
  andamento). "Não lançar" vai em dois passos, também sem JavaScript: um `<details>` com um
  formulário próprio que manda `confirmado=1`, e a view recusa `nao_lancar` sem ele antes de
  chamar `resolver_lote` (o "Desistir" do `pedidos.js` fecha o painel). "Em andamento" (`ExecucaoRobo.em_andamento`) vem da trava: com ela ocupada
  (`IS_USED_LOCK`), toda execução sem fim; sem ela, só a criada há menos de 60 s (o processo
  ainda subindo). As demais sem fim aparecem como interrompidas e liberam o botão. Se o
  disparo não consegue iniciar o processo, a execução já nasce `FALHA`. `consultas.lotes_pendentes` (o total da fila, pela mesma regra) e `lotes_travados`
  alimentam o cartão do painel e a aba Lançamento no SCPI. Fora de `servicos.py`, só o robô grava
  em `pedidos`, e só mexe em `status`, `requisicao_scpi`, `lancado_em` e `mensagem` das
  `LinhaSaida` (o superusuário também edita esses quatro no admin); a única outra exceção é a
  migração única das planilhas (`implantacao/migracao.py`), que substitui os pedidos.
- `LANCAMENTO_REAL` (`.env`) libera o lançamento real no SCPI; com `0` (o padrão), o lançamento
  real fica bloqueado e só a simulação roda. Ele existiu para o Django e o Apps Script não
  lançarem em dobro no período em paralelo; o robô antigo já foi desativado, e o bloqueio agora
  só espera a liberação do lançamento real. Em produção ainda está bloqueado (`=0`); a liberação
  é `LANCAMENTO_REAL=1` no `.env` do servidor e `docker compose up -d` (`deploy/VIRADA.md`,
  seção 6), sem mudar o padrão do código. Bloqueado, o comando `lancar_saidas` recusa sem
  `--dry-run`, a aba Lançamento no SCPI recusa o modo "Lançar" (só "Simular") e o painel avisa
  que está bloqueado. O `settings_test` o liga, porque os testes do robô lançam no SCPI simulado;
  os testes do bloqueio o desligam com o fixture `settings`.
- `implantacao` (sem modelos nem migrations) é a migração única das planilhas do Apps Script e
  pode ser apagada depois da virada, salvo o backup. `planilha.py` (puro) lê o `.xlsx` com as
  colunas achadas pelo nome do cabeçalho; `conversao.py` (sem banco) vira registros não salvos e
  junta todos os problemas (erro bloqueia, aviso não; saída pendente que se perderia é erro; texto
  maior que o `max_length` do campo e `Atendimento_ID` repetido também são erro, conferidos por um
  helper único sobre os modelos); `migracao.py` grava numa transação (travando a `Sequencia` antes
  das travas), substituindo pedidos, centros de custo, opções e itens de limpeza, e recusa com
  `LANCAMENTO_REAL` ligado, com pedido no banco que não está na planilha, com atendimento feito no
  Django (`atendido_por` que não é o usuário `planilha`: a reimportação o apagaria) ou sem nenhum
  material (o cadastro do SCPI vem antes). O `--dry-run` chama `gravar` dentro de uma transação e
  a desfaz (`set_rollback`), e erro de banco vira `CommandError`. O status das linhas de saída vem da
  requisição, das observações e do "Status SCPI", nessa ordem, e na dúvida fica `VERIFICAR`,
  nunca `PENDENTE`. Atendimentos e saídas avulsas importados apontam para o usuário inativo
  `planilha`; a aba "Almoxarifado" (e-mails) não é importada, as contas do painel são criadas
  no admin. `backup.py` faz o dump (`MYSQLDUMP`, retenção de 60 dias pelo nome do arquivo, a
  limpeza só depois de um backup completo). `depara.py` (sem banco) lê os pares do `.xlsx` da
  planilha MAPEAMENTO DE/PARA CONSOLIDADO: a primeira aba cujo nome começa por "Planilha de
  mapeamento" (o `.xlsx` não aceita "/" no nome de aba) com as regras do `DEPARA_MAP` (formato
  000.000.000, antigo diferente do novo, primeira ocorrência), e a aba `DEPARA`, que vence e traz
  o fator; o `importar_depara` substitui todos os pares numa transação, registra uma
  `Importacao` `DEPARA` e recusa se há par de origem `SISTEMA` ou registro do admin (`LogEntry`)
  depois da última carga: depois dela, o sistema é a fonte dos pares.
- De/para e curva ABC (`specs/001-depara-curva-abc/`, feita pelo Spec Kit): `ParDePara` (código
  antigo único → novo, com fator de quantidade; validação, sem 1:N e sem ciclo no `clean`; o
  admin grava origem `SISTEMA`) e as funções puras de `catalogo/depara.py` (`validar_par`,
  `resolver_canonicos`, que segue a cadeia até o fim e multiplica os fatores, e `consolidar`).
  Toda contagem de saídas usa o canônico: `consultas_curva.py` agrega `SaidaSCPI` por código
  numa consulta e consolida em Python. O período é uma janela móvel (`ConfiguracaoCurva`, linha
  única via `atual()`: janela, prazo de entrega e cobertura alvo gerais) que nunca começa antes
  de 01/01/2026 (`curva.INICIO_DADOS_CONFIAVEIS`); o formulário AB usa a mesma janela e mostra o
  saldo do canônico. A página Painel › Curva ABC (`catalogo:curva`, `?aba=` e `?meses=`) mostra
  as curvas por frequência e por valor (`curva.curva`: A até 78% do acumulado, B até 95%), a
  reposição (`curva.reposicao`, fórmulas da planilha com o fator no consumo; o estoque soma o
  canônico e os antigos; `ParametroReposicao` substitui prazo e cobertura por material), os
  pendentes de mapeamento (código com saída, sem par, oculto ou fora do cadastro) e a
  reconciliação dos totais. As divergências deliberadas da planilha estão na spec.
- Implantação em Docker Compose (`compose.yaml`, `Dockerfile`; spec
  `2026-10-15-docker-design.md`): uma imagem (Python 3.13, `.venv` do uv sem dev, Chromium do
  Playwright, `mariadb-client`, supercronic, estáticos coletados no build, usuário `almox`
  UID 1000 que só escreve em `/dados`) para os serviços `web` (waitress com
  `--url-prefix=${PREFIXO_URL}` e `--trusted-proxy=*`, publicado em `${PORTA_PUBLICADA}`, que
  só o Apache pode alcançar) e `agendador` (supercronic com `deploy/crontab`, que chama
  `deploy/tarefa.sh`, saída em `dados/logs/agendador.log`); o `banco` é o MariaDB 11.4, sem
  porta publicada. O compose força `DB_HOST`, `SCPI_HEADLESS=1`, `MYSQLDUMP=mariadb-dump` e as
  pastas (`/dados/logs`, `/dados/backups`, `/dados/perfil` e o `PLAYWRIGHT_BROWSERS_PATH` da
  imagem) por cima do `.env`; `dados/` do host guarda logs, backups e `dados/importacao`, onde
  ficaram os `.xlsx` da virada (já apagados). Os robôs da página são filhos do waitress
  no container `web` (`disparo.py` abre sessão própria fora do Windows), então recriar o `web`
  os mata: o `deploy/atualizar.sh` confere `robos_em_andamento` (por `docker compose run
  --rm`, que funciona com o `web` parado) antes do `git pull` e antes do `up -d`, e tem o corpo
  numa função porque o bash lê o script aos poucos. `deploy/*.sh`, `deploy/crontab`,
  `Dockerfile` e `compose.yaml` são LF (`.gitattributes`). Guias em `deploy/INSTALACAO.md`
  (para quem administra o servidor; Linux ou WSL2) e `deploy/VIRADA.md`.
- O log usa `ConcurrentRotatingFileHandler` porque o waitress e os comandos gravam no mesmo
  arquivo (no container também: `web` e `agendador` dividem `dados/logs`); no Windows o
  `RotatingFileHandler` não consegue girar um arquivo aberto por outro processo.

## Convenções

- Nomes de código, textos de interface, mensagens e commits em português (pt-BR).
- Logout só por POST com CSRF, num único formulário por página. Requisição HTMX que grava vai
  dentro de um `<form>` com `{% csrf_token %}`.
- Estado nunca só por cor; códigos (CADPRO, matrícula, placa) em fonte mono (`.mono`).
- Todo ajuste de UI/UX usa três skills juntas: `clean-design` (no repositório) com o
  `docs/DESIGN.md`, que são a referência fixa de estilo e vencem as outras duas;
  `ui-ux-pro-max` (plugin), para conferir usabilidade e acessibilidade pelo buscador; e
  `frontend-design` (plugin), para hierarquia, contenção, textos de interface e a conferência
  por screenshot. Onde discordarem, valem o DESIGN.md e o que já está no código. Não refazer o
  questionário inicial da `clean-design` (o projeto já o respondeu) nem gerar ou gravar um
  design system novo das skills sem pedido.
- O servidor está em produção com dados reais: mudança de modelo ganha **migration nova**,
  nunca regenerada (nem `migrate <app> zero`).

# Research: Clareza e segurança da página Lançamentos SCPI

Sem NEEDS CLARIFICATION no contexto técnico. As decisões abaixo saem da leitura do código atual
(`pedidos/views/lancamentos.py`, `_lancamentos.html`, `pedidos/forms.py`, `pedidos/consultas.py`,
`scpi/requisicoes.py`, `scpi/lancamento.py`, `scpi/disparo.py` e o cartão do painel).

## R1 — Um formulário com os dois botões e o limite

**Decision**: um único `<form>` para `pedidos:lancar`, com o campo "Só as primeiras [N]
requisições" (vazio = todas) e dois botões `type="submit" name="modo"` com `value="simular"` e
`value="lancar"`. A classe de destaque (`botao-primario`) vai para "Simular" com o bloqueio ligado
e para "Lançar no SCPI" com ele desligado. Bloqueado, "Lançar no SCPI" é `type="button"`,
`aria-disabled="true"`, com cadeado e `aria-describedby` para a dica (`.dica-flutuante`), cópia do
botão do cartão do painel. Com execução em andamento ou fila vazia, os dois botões ficam
`disabled` e o campo do limite também (nada digitado se perde na recarga), com o motivo em texto
ao lado. O `LancamentoForm` perde o `RadioSelect` (o template não o usa) e mantém
`clean_modo` e `da_requisicao` (botões antigos com `simulacao=1` continuam aceitos).

**Rationale**: o botão clicado já diz o modo; um seletor a mais era a mesma escolha repetida
(FR-004). Com o limite no mesmo formulário, ele vale para o botão escolhido (FR-005) sem
validação nova. Reaproveitar o padrão do painel mantém um comportamento só para o bloqueio.

**Texto da dica**: "Lançamento real bloqueado até a virada: só a simulação roda." (spec, US1). O
cartão do painel acrescenta "(LANCAMENTO_REAL no .env)"; na página, esse detalhe técnico vai para
o `campo-dica` sob os botões, junto do que a simulação faz, para quem administra o servidor.

**Alternatives considered**: manter o `<details>` só com o limite (esconde a única opção nova);
`disabled` no botão bloqueado (sai do Tab e não mostra a dica); modo em `<select>` (dois passos
para a ação mais comum).

## R2 — Fila do robô em SQL, com a regra do robô

**Decision**: `consultas.fila_do_robo(limite=20) -> Fila(total, requisicoes)`. Um lote está na
fila se tem alguma linha `PENDENTE` e nenhuma linha em `ESTADOS_TRAVA` nem `PENDENTE` com
`requisicao_scpi` preenchido — a mesma regra de `requisicoes.selecionar`. Em SQL: `values("lote")`
das linhas `PENDENTE`, com `~Exists(...)` sobre as linhas do mesmo lote que travam, anotado com
`Min("id")` e `Count("id")`, ordenado por `Min("id")` (a ordem em que o robô percorre). O total é
o `count()` dessa consulta; as 20 primeiras trazem a primeira linha de cada lote (data,
recebedor, centro de custo) numa segunda consulta `id__in`. O número de materiais é a contagem de
linhas `PENDENTE` do lote.

Para a regra ter um dono só, a parte de agrupar de `selecionar` vira `requisicoes.agrupar(linhas)
-> (grupos, travados)` (puro, mesmo resultado; `selecionar` passa a chamá-la e só valida). Um
teste monta linhas em todos os estados e confere que os lotes de `fila_do_robo` são os de
`agrupar`, na mesma ordem — como o teste que confere `consultas` × `regras.situacao_*`.

**Rationale**: antes da virada a fila tem todas as saídas atendidas desde a importação; carregar
todas as linhas a cada recarga de 3 s seria caro. A consulta agrega no banco e só traz 20 linhas.

**Validação de dados não entra**: a fila mostra o que o robô tentaria lançar; um lote com dado
inválido vira `ERRO` na execução e aparece nas travas, como hoje. Validar na página exigiria os
centros de custo e duplicaria `validar` sem pedido da spec.

**Link de origem**: o `lote` é o número do pedido ou da saída avulsa, e `pedidos:detalhe` já o
recebe (as travas usam o mesmo link).

**Alternatives considered**: carregar as linhas e chamar `agrupar` na view (simples, mas lê
milhares de linhas por recarga); só a contagem (não atende FR-006).

## R3 — `lotes_pendentes()` com a mesma regra

**Decision**: `lotes_pendentes()` passa a ser `fila_do_robo(limite=0).total` (ou a mesma consulta
só com `count()`), e o cartão do painel e a página mostram o mesmo número (spec FR-023). O texto
do cartão também troca "lote(s) aguardando o robô" por "requisição/requisições aguardando o robô"
e "Nenhum lote aguardando o robô." por "Nada aguardando o robô.".

**Rationale**: hoje ele conta todo lote com alguma linha `PENDENTE`, inclusive o travado em parte
ou já com número de requisição; a página diria "3 aguardando" e listaria 2. A mudança só afeta o
número exibido (e, no painel, se o botão "Simular lançamento" fica habilitado); o robô já
ignorava esses lotes.

**Alternatives considered**: deixar o painel como está (dois números para a mesma coisa).

## R4 — A execução em frase: `pedidos/andamento.py`

**Decision**: módulo puro (sem ORM, recebe a `ExecucaoRobo` ou só seus campos e `agora`):

- `feitas(execucao) -> int`: `simuladas` na simulação, `lancadas` no lançamento real;
- `n_de_m(execucao) -> str | None`: "3 de 3"; `None` quando `requisicoes` é 0 e a execução falhou
  ou está começando (nunca "0 de 0");
- `duracao(inicio, fim) -> str`: "45 s", "2 min 5 s", "1 h 3 min"; "—" sem `fim`;
- `momento(inicio, agora) -> str`: "hoje, 13:25", "ontem, 13:25" ou "07/10, 13:25" (hora local);
- `contadores(resumo, simulacao) -> list[(rotulo, valor)]`: só os diferentes de zero, na ordem
  lançadas/simuladas, "com erro" (`falhas`), "para verificar" (`verificar`), "deixadas de fora"
  (`ignoradas`), com plural certo;
- `frase(execucao, agora, interrompida) -> str`:
  - concluída: "Simulação de hoje, 13:25, concluída: 3 de 3 requisições preenchidas." /
    "Lançamento de hoje, 13:25, concluído com pendências: 1 de 2 requisições lançadas.";
  - nada a fazer (`requisicoes` 0, sucesso): "… concluída: nada a lançar.";
  - em andamento: "Simulação em andamento: requisição 2 de 5." (`processadas + 1`, limitado a
    `requisicoes`); sem total ainda: "… em andamento: preparando a fila.";
  - interrompida: "… interrompida: o robô parou sem registrar o fim.";
  - falha: ver R5;
- `precisa_conferir(execucao) -> bool`: `falhas` ou `verificar` > 0, ou falha de lançamento real
  (FR-016, atalho `#travas`).

**Rationale**: funções puras testam todos os casos sem banco nem template; o template só exibe.
"Interrompida" continua vindo de `ExecucaoRobo.interrompida` (consulta a trava), passada como
argumento para a função ficar pura.

**Alternatives considered**: template tags (difíceis de testar caso a caso); propriedades no
modelo (misturam texto de tela com o registro do robô).

## R5 — Falha em português, detalhe recolhido

**Decision**: `explicar_falha(execucao) -> Falha(frase, proximo_passo, tecnico: bool)`, nesta ordem:

1. erro conhecido em português (`LANCAMENTO_BLOQUEADO`, "Outro lançamento já está em andamento.",
   e os de `FalhaCritica`/`ErroImportacao`, que já são frases): mostrado como vem, sem detalhe
   técnico (spec, Assumptions);
2. começa por "Falha inesperada:" (`executar_lancamento`): "O robô parou por um erro do sistema."
   — ou, com "Timeout" na primeira linha, "O SCPI demorou demais para responder e o robô parou."
   (mesmo critério de `catalogo.saude.resumo_do_erro`); técnico;
3. sem registro e sem resumo (o `disparo` não conseguiu iniciar o processo e gravou `str(exc)`):
   "O robô não chegou a iniciar."; técnico;
4. qualquer outro texto: mostrado como vem; técnico se tiver mais de uma linha.

Depois da frase, até onde chegou: "Chegou a processar 2 de 5 requisições." ou "Parou antes de
começar." (resumo vazio ou `requisicoes` 0). Na simulação, "Nenhuma linha mudou de estado." e o
próximo passo "Pode simular de novo; se o erro se repetir, avise quem cuida do sistema." com o
botão "Simular de novo". No lançamento real, "Confira as travas abaixo antes de lançar de novo."
e o link para `#travas`, sem botão (FR-013).

O "Detalhe técnico" é um `<details>` (fechado) com o erro original e o registro recente
(`log_recente`, 40 linhas, como hoje), num `<pre>` com `white-space: pre-wrap` e
`overflow-wrap: anywhere` para não criar rolagem horizontal. O aviso tem `role="alert"` e a
palavra "Falhou" escrita no selo.

**Rationale**: a página só explica; nenhum texto gravado muda (FR-022). Reaproveitar o critério do
catálogo deixa as duas páginas falando igual do mesmo tipo de erro.

**"Simular de novo"**: um `<form>` para `pedidos:lancar` com `modo=simular`, sem limite, dentro do
aviso; as regras são as do botão "Simular" (trava, fila vazia), porque é a mesma view.

**Alternatives considered**: traduzir exceções conhecidas do Playwright (frágil, sem lista
estável); mudar o texto gravado pelo robô (fora do escopo, FR-022).

## R6 — Histórico

**Decision**: colunas Início, Modo, Quem, Situação, Requisições (`n_de_m` ou "—") e Duração
(`duracao`). Saem "Lançadas", "Falhas" e "Verificar" (as pendências aparecem na situação
"Concluída com pendências" e nas travas). O modo continua escrito. No celular a tabela segue na
`tabela-rolagem` de hoje.

**Rationale**: FR-019 e SC-006; as colunas antigas mostravam 0 para toda simulação.

## R7 — "Não lançar" em dois passos, também sem JavaScript

**Decision**: em cada trava, "Não lançar" deixa de ser um botão do formulário de resolução e vira
um `<details class="confirmar-nao-lancar">` cujo `<summary>` é "Não lançar…" (estilo
`botao-texto botao-perigo`). Aberto, mostra o aviso "A requisição de {lote} não será lançada no
SCPI. As linhas ficam marcadas como Não lançar." e um formulário **próprio** para
`pedidos:resolver` com `acao=nao_lancar`, `confirmado=1` (escondido) e o botão "Confirmar: não
lançar". "Desistir" é o próprio `<summary>` (fecha o painel); com JavaScript, um botão
"Desistir" no painel o fecha e devolve o foco ao `summary` (`pedidos.js`, carregado na página).

A view `resolver` recusa `acao=nao_lancar` sem `confirmado` com "Confirme antes de marcar para
não lançar." e não chama `resolver_lote`. Um formulário próprio evita que o campo da requisição e
a caixa "Conferi no SCPI" do formulário de resolução vão juntos.

**Rationale**: o primeiro clique só abre o painel; gravar exige o segundo (FR-009, FR-010,
SC-003), sem depender de `confirm()`, que some sem JavaScript e é ignorado por quem clica rápido.
A recusa na view cobre um formulário antigo em cache ou um POST montado à mão.

**FR-011**: os formulários de resolução, e portanto a confirmação, só aparecem sem execução em
andamento; sem execução, a seção não tem `hx-trigger` e não é recarregada. Isso se mantém, e um
teste confere que a resposta com formulários de resolução nunca leva `hx-trigger`. Uma execução
iniciada por outra pessoa depois da carga não liga a recarga nesta página (o `hx-trigger` só vem
na resposta).

**Alternatives considered**: `confirm()` do navegador (não funciona sem JavaScript, FR-010);
página intermediária de confirmação (mais uma navegação, perde o contexto da trava); caixa
"Estou ciente" como no catálogo (bom para uma ação rara e única; aqui há uma por trava e o
`<details>` deixa o perigo fechado por padrão).

## R8 — Textos, cabeçalho e travas vazias

**Decision**:

- "lote(s)" some dos textos da página: "1 requisição aguardando o robô" / "N requisições
  aguardando o robô" (`pluralize`), "requisição N de M"; mensagens das resoluções (gravadas pelo
  `resolver_lote`, "Lote … marcado …") continuam iguais (FR-022);
- o bloco `rotulo` sai de `lancamentos.html` (como nas páginas do catálogo);
- sem travas, a seção vira só `<p class="texto-secundario" id="travas">Nenhuma trava para
  conferir.</p>`, sem o cartão; com travas, o cartão ganha `id="travas"` para o atalho;
- sem execução registrada e com fila vazia: "Nada aguardando o robô." e "Nenhuma execução ainda.",
  sem cartões vazios (andamento e histórico somem juntos);
- as mensagens de `lancar` ("Limite: N requisição(ões).") passam a ter plural certo.

**Ordem na página**: ação (botões, limite, motivo) → fila → andamento → travas → histórico. A
fila fica logo abaixo dos botões porque é o que se confere antes de clicar (SC-002).

**Rationale**: FR-020, FR-021 e os casos de borda da spec.

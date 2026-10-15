# Contrato: página Lançamentos SCPI

Rotas e nomes não mudam (`pedidos:lancamentos`, `pedidos:lancar`, `pedidos:resolver`), todas com
login. Nenhum caminho fixo nos templates (`tests/test_prefixo.py`).

## GET `pedidos:lancamentos`

- Sem `HX-Request` (ou com `HX-History-Restore-Request`): página inteira (`lancamentos.html`).
- Com `HX-Request`: só `<section id="lancamentos">` (`_lancamentos.html`), como hoje.
- A seção leva `hx-get`/`hx-trigger="every 3s"`/`hx-swap="outerHTML"` **só** com execução em
  andamento. Resposta com formulário de resolução ou de confirmação nunca leva `hx-trigger`.
- Cabeçalho: título "Lançamentos SCPI" e subtítulo; sem rótulo acima do título.

### Estrutura da seção, nesta ordem

1. **Ação** (`form` → `pedidos:lancar`, POST com CSRF)
   - campo `limite` ("Só as primeiras [N] requisições", `type="number"`, `min=1`, `max=10000`,
     vazio = todas);
   - botão `name="modo" value="simular"` "Simular";
   - botão "Lançar no SCPI": liberado, `type="submit" name="modo" value="lancar"`; bloqueado,
     `type="button" aria-disabled="true" aria-describedby="dica-lancamento-real"`, ícone de
     cadeado, dentro de `.dica-flutuante`, com `<span role="tooltip" id="dica-lancamento-real">`
     "Lançamento real bloqueado até a virada: só a simulação roda.";
   - destaque (`botao-primario`) em exatamente um botão: "Simular" bloqueado, "Lançar no SCPI"
     liberado; nenhum com execução em andamento ou fila vazia;
   - em andamento ou fila vazia: os botões que enviariam e o `limite` com `disabled`, e o motivo em
     texto ("Há uma execução em andamento." / "Nada aguardando o robô.");
   - `campo-dica`: o que a simulação faz e, bloqueado, a menção a `LANCAMENTO_REAL` no `.env`.
2. **Fila** — "N requisição/requisições aguardando o robô" (sempre), e com N > 0 uma tabela com
   Nº (link `.mono` para `pedidos:detalhe`), Data, Recebedor, Centro de custo, Materiais; até 20
   linhas, e com mais, "e mais K requisições".
3. **Andamento** (só com alguma execução registrada)
   - frase de `andamento.frase`; selo da situação escrito ("Concluída", "Concluída com
     pendências", "Falhou", "Em andamento", "Interrompida") e selo do modo;
   - linha "Iniciada por … · duração …";
   - contadores diferentes de zero; com `precisa_conferir`, link "Ver as travas" (`#travas`);
   - com falha: `div.aviso.aviso-erro[role=alert]` com a frase, até onde chegou e o próximo
     passo; na simulação, `form` → `pedidos:lancar` com `modo=simular` e o botão "Simular de
     novo" (desabilitado com execução em andamento); `<details>` "Detalhe técnico" fechado com o
     erro original e o registro recente quando `tecnico`;
   - sem falha e com registro: o registro recente continua num `<details>` "Registro da execução"
     (aberto enquanto em andamento).
4. **Travas** — sem travas: só `<p id="travas">Nenhuma trava para conferir.</p>`. Com travas:
   cartão `id="travas"`, um `article` por lote com o Nº do pedido de origem, os dados e a tabela
   das linhas (como hoje); sem execução em andamento:
   - `form` de resolução → `pedidos:resolver` com "Informar requisição" (`acao=lancada`), a caixa
     "Conferi no SCPI" quando `conferir`, e "Liberar para relançar" (`acao=liberar`);
   - `<details class="confirmar-nao-lancar">` com `<summary>` "Não lançar…" e, aberto, o aviso e
     um `form` próprio → `pedidos:resolver` com `acao=nao_lancar`, `confirmado=1` e o botão
     "Confirmar: não lançar".
5. **Histórico** (só com alguma execução) — tabela com Início, Modo, Quem, Situação,
   Requisições ("N de M" ou "—"), Duração ("—" sem fim); até 10 execuções.

## POST `pedidos:lancar`

Entrada: `modo` (`simular` | `lancar`; ausente → `simulacao=1` decide, como hoje), `limite`
opcional (1–10000). Validação e mensagens de recusa iguais às de hoje (`LancamentoForm`), com
`LANCAMENTO_BLOQUEADO` para `modo=lancar` bloqueado. Sucesso: mensagem e redirecionamento para
`pedidos:lancamentos`; o "Limite: N requisição/requisições." ganha plural certo.

## POST `pedidos:resolver <lote>`

Entrada: `acao` (`lancada` | `liberar` | `nao_lancar`), `requisicao`, `conferido`, e **novo**
`confirmado`.

- `acao=nao_lancar` sem `confirmado=1`: mensagem de erro "Confirme antes de marcar para não
  lançar.", nada gravado, `resolver_lote` não é chamado.
- Demais casos: `resolver_lote` como hoje, com as mesmas mensagens.

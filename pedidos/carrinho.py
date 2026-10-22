"""Carrinho dos formulários (traduz `criarSeletor` de `Comum.html`).

O carrinho vive na página, em campos escondidos (`item_codigo`/`item_qtd`). O HTMX o envia a
cada adição ou remoção e o servidor só devolve o trecho, sem guardar estado. O envio final
revalida tudo.

A quantidade aceita e o teto de estoque seguem a regra do formulário (`Fluxo.regra_quantidade`):
quem pede segue a unidade do material (fração só em unidade fracionável); a equipe aceita fração
em qualquer unidade. O teto (`limite`) é o mesmo número que a lista mostra como estoque.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from catalogo.catalogos import ItemCatalogo
from pedidos.regras import (
    ItemEnviado,
    aceita_fracao,
    interpretar_quantidade,
    maximo_pedivel,
    qtd_br,
    texto_acima_do_estoque,
    texto_erro_quantidade,
)


@dataclass(frozen=True)
class LinhaCarrinho:
    codigo: str
    quantidade: Decimal | None
    item: ItemCatalogo | None
    # O que a pessoa digitou, quando a quantidade não converte: a linha fica no pedido para ser
    # corrigida, inclusive nas operações do carrinho depois de um envio recusado.
    bruto: str | None = None

    @property
    def texto(self) -> str:
        """Quantidade no campo escondido: pt-BR exata, sem zeros à direita; a linha ilegível
        mostra o texto digitado."""
        if self.bruto is not None:
            return self.bruto
        return qtd_br(self.quantidade)


@dataclass
class Carrinho:
    linhas: list[LinhaCarrinho] = field(default_factory=list)
    erro: str = ""
    aviso: str = ""


def _fracionavel(fluxo, item: ItemCatalogo | None) -> bool:
    """Se a quantidade deste material pode ter fração neste formulário (`regras.aceita_fracao`,
    a mesma conta da validação do envio)."""
    return aceita_fracao(fluxo.regra_quantidade, item)


def ler(dados, fluxo, catalogo, anteriores=None, manter_ilegiveis=False) -> list[LinhaCarrinho]:
    """O carrinho enviado pela página; pares inválidos são ignorados. `anteriores`
    ({código: texto}) troca a quantidade de uma linha pela última válida: é o que vale enquanto
    a alteração dela é conferida. Com `manter_ilegiveis` (o envio e o carrinho públicos), o par que
    não converte continua no pedido, com o texto digitado, até ser corrigido ou removido."""
    por_codigo = {i.codigo: i for i in catalogo or []}
    anteriores = anteriores or {}
    linhas = []
    for codigo, texto_qtd in zip(
        dados.getlist("item_codigo"), dados.getlist("item_qtd"), strict=False
    ):
        item = por_codigo.get(codigo)
        digitado = anteriores.get(codigo, texto_qtd)
        q, causa = interpretar_quantidade(digitado, _fracionavel(fluxo, item))
        if not causa:
            linhas.append(LinhaCarrinho(codigo, q, item))
        elif manter_ilegiveis:
            linhas.append(LinhaCarrinho(codigo, None, item, bruto=digitado))
    return linhas


def itens_enviados(dados) -> tuple[ItemEnviado, ...]:
    """Itens para o envio final, com os textos como vieram (a validação converte)."""
    return tuple(
        ItemEnviado(c, q)
        for c, q in zip(dados.getlist("item_codigo"), dados.getlist("item_qtd"), strict=False)
    )


def _fq(n, item: ItemCatalogo) -> str:
    numero = qtd_br(n)
    return f"{numero} {item.unidade}" if item.unidade else numero


def limite(fluxo, item: ItemCatalogo) -> Decimal:
    """O mais que se pode pôr no pedido: o máximo pedível, o mesmo número que a lista mostra
    como estoque (saldo truncado a 3 casas; para quem pede, a parte inteira se a unidade é
    contada)."""
    return maximo_pedivel(item.estoque, item.fracionavel, fluxo.regra_quantidade)


def motivo_bloqueio(fluxo, item: ItemCatalogo) -> str:
    """Por que o material não pode ser pedido ("" se pode)."""
    if item.duplicado:
        return "Cadastro duplicado — avise o almoxarifado"
    if limite(fluxo, item) <= 0:
        return "Sem estoque"
    return ""


def acima_do_estoque(fluxo, item: ItemCatalogo, q) -> str:
    """O erro de quantidade acima do limite, "" se cabe."""
    teto = limite(fluxo, item)
    if q <= teto:
        return ""
    return texto_acima_do_estoque(teto, item.unidade)


def quantidade(fluxo, texto_qtd, item: ItemCatalogo | None = None):
    """A quantidade digitada, ou o erro que a recusa (mesmos textos para adicionar e alterar, no
    envio e no material acrescentado pelo almoxarifado no atendimento)."""
    fracionavel = _fracionavel(fluxo, item)
    q, causa = interpretar_quantidade(texto_qtd, fracionavel)
    if causa:
        unidade = item.unidade if item is not None else ""
        return None, texto_erro_quantidade(causa, fracionavel=fracionavel, unidade=unidade)
    return q, ""


def adicionar(linhas, fluxo, item: ItemCatalogo | None, texto_qtd: str) -> Carrinho:
    linhas = list(linhas)
    if item is None:
        return Carrinho(linhas, erro="Material não encontrado no catálogo.")
    motivo = motivo_bloqueio(fluxo, item)
    if motivo:
        return Carrinho(
            linhas, erro=f"{item.nome} ({item.codigo}): {motivo} — não pode ser adicionado."
        )
    q, erro = quantidade(fluxo, texto_qtd, item)
    if erro:
        return Carrinho(linhas, erro=erro)

    existente = next((linha for linha in linhas if linha.codigo == item.codigo), None)
    if existente is not None and existente.quantidade is None:
        _, erro = quantidade(fluxo, existente.texto, item)
        return Carrinho(linhas, erro=f"{item.nome} ({item.codigo}): {erro}")
    ja = existente.quantidade if existente is not None else Decimal(0)
    teto = limite(fluxo, item)
    if ja + q > teto:
        cabe = teto - ja
        if not ja:
            erro = acima_do_estoque(fluxo, item, q)
        elif cabe > 0:
            erro = (
                f"Já há {_fq(ja, item)} no pedido; é possível acrescentar no máximo "
                f"{_fq(cabe, item)}."
            )
        else:
            erro = f"Já há {_fq(ja, item)} no pedido, que é todo o estoque disponível."
        return Carrinho(linhas, erro=erro)
    if not ja and fluxo.max_itens is not None and len(linhas) >= fluxo.max_itens:
        return Carrinho(linhas, erro=f"O pedido pode ter no máximo {fluxo.max_itens} materiais.")

    if ja:
        total = ja + q
        novas = [
            LinhaCarrinho(linha.codigo, total, item) if linha.codigo == item.codigo else linha
            for linha in linhas
        ]
        aviso = (
            f"{item.nome} já estava no pedido: {_fq(ja, item)} + "
            f"{_fq(q, item)} = {_fq(total, item)}."
        )
        return Carrinho(novas, aviso=aviso)
    return Carrinho([*linhas, LinhaCarrinho(item.codigo, q, item)])


def remover(linhas, codigo: str) -> Carrinho:
    return Carrinho([linha for linha in linhas if linha.codigo != codigo])


def alterar(linhas, fluxo, item: ItemCatalogo | None, texto_qtd: str) -> Carrinho:
    """Troca a quantidade de um material que já está no pedido (substitui, não soma). Recusada,
    a linha fica com a quantidade anterior, que é a que vem em `linhas`."""
    linhas = list(linhas)
    if item is None:
        return Carrinho(linhas, erro="Material não encontrado no catálogo.")
    if not any(linha.codigo == item.codigo for linha in linhas):
        return Carrinho(linhas, erro="Material não está no pedido.")
    q, erro = quantidade(fluxo, texto_qtd, item)
    if erro:
        return Carrinho(linhas, erro=erro)
    if erro := acima_do_estoque(fluxo, item, q):
        return Carrinho(linhas, erro=erro)
    return Carrinho(
        [
            LinhaCarrinho(linha.codigo, q, item) if linha.codigo == item.codigo else linha
            for linha in linhas
        ]
    )

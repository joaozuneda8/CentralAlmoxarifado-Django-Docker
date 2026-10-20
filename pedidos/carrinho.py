"""Carrinho dos formulários (traduz `criarSeletor` de `Comum.html`).

O carrinho vive na página, em campos escondidos (`item_codigo`/`item_qtd`). O HTMX o envia a
cada adição ou remoção e o servidor só devolve o trecho, sem guardar estado. O envio final
revalida tudo.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from catalogo.catalogos import ItemCatalogo
from pedidos.regras import ItemEnviado, parse_inteiro, parse_qtd_br, qtd_br


@dataclass(frozen=True)
class LinhaCarrinho:
    codigo: str
    quantidade: Decimal | int
    item: ItemCatalogo | None

    @property
    def texto(self) -> str:
        """Quantidade no campo escondido: inteira no AB, pt-BR nos demais."""
        if isinstance(self.quantidade, int):
            return str(self.quantidade)
        return qtd_br(self.quantidade)


@dataclass
class Carrinho:
    linhas: list[LinhaCarrinho] = field(default_factory=list)
    erro: str = ""
    aviso: str = ""


def _converter(fluxo, texto_qtd):
    return parse_inteiro(texto_qtd) if fluxo.inteiro else parse_qtd_br(texto_qtd)


def ler(dados, fluxo, catalogo, anteriores=None) -> list[LinhaCarrinho]:
    """O carrinho enviado pela página; pares inválidos são ignorados. `anteriores`
    ({código: texto}) troca a quantidade de uma linha pela última válida: é o que vale enquanto
    a alteração dela é conferida."""
    por_codigo = {i.codigo: i for i in catalogo or []}
    anteriores = anteriores or {}
    linhas = []
    for codigo, texto_qtd in zip(
        dados.getlist("item_codigo"), dados.getlist("item_qtd"), strict=False
    ):
        q = _converter(fluxo, anteriores.get(codigo, texto_qtd))
        if q is not None and q > 0:
            linhas.append(LinhaCarrinho(codigo, q, por_codigo.get(codigo)))
    return linhas


def itens_enviados(dados) -> tuple[ItemEnviado, ...]:
    """Itens para o envio final, com os textos como vieram (a validação converte)."""
    return tuple(
        ItemEnviado(c, q)
        for c, q in zip(dados.getlist("item_codigo"), dados.getlist("item_qtd"), strict=False)
    )


def _fq(fluxo, n, item: ItemCatalogo) -> str:
    numero = str(int(n)) if fluxo.inteiro else qtd_br(n)
    return f"{numero} {item.unidade}" if item.unidade else numero


def motivo_bloqueio(fluxo, item: ItemCatalogo) -> str:
    """Por que o material não pode ser pedido ("" se pode)."""
    if item.duplicado:
        return "Cadastro duplicado — avise o almoxarifado"
    teto = limite(fluxo, item)
    if teto is not None and teto <= 0:
        return "Sem estoque"
    return ""


def limite(fluxo, item: ItemCatalogo) -> Decimal | int | None:
    """O mais que se pode pôr no pedido: a parte inteira do estoque no AB, o saldo exato (decimal)
    na limpeza e na saída avulsa."""
    if fluxo.com_estoque:
        return item.disponivel
    if fluxo.limita_estoque:
        return item.estoque
    return None


def acima_do_estoque(fluxo, item: ItemCatalogo, q) -> str:
    """O erro de quantidade acima do limite, "" se cabe (ou se o fluxo não limita)."""
    teto = limite(fluxo, item)
    if teto is None or q <= teto:
        return ""
    return f"Quantidade acima do estoque. Estoque disponível: {_fq(fluxo, teto, item)}."


def quantidade(fluxo, texto_qtd):
    """A quantidade digitada, ou o erro que a recusa (mesmos textos para adicionar e alterar,
    também no material acrescentado pelo almoxarifado no atendimento)."""
    q = _converter(fluxo, texto_qtd)
    if fluxo.inteiro and (q is None or q < 1):
        return None, "Informe um número inteiro maior que zero."
    if not fluxo.inteiro and (q is None or q <= 0):
        if "." in (texto_qtd or ""):
            return None, "Use vírgula para decimais (ex.: 1,5)."
        return None, "Informe uma quantidade maior que zero."
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
    q, erro = quantidade(fluxo, texto_qtd)
    if erro:
        return Carrinho(linhas, erro=erro)

    ja = next((linha.quantidade for linha in linhas if linha.codigo == item.codigo), 0)
    teto = limite(fluxo, item)
    if teto is not None and ja + q > teto:
        cabe = teto - ja
        if not ja:
            erro = acima_do_estoque(fluxo, item, q)
        elif cabe > 0:
            erro = (
                f"Já há {_fq(fluxo, ja, item)} no pedido; é possível acrescentar no máximo "
                f"{_fq(fluxo, cabe, item)}."
            )
        else:
            erro = f"Já há {_fq(fluxo, ja, item)} no pedido, que é todo o estoque disponível."
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
            f"{item.nome} já estava no pedido: {_fq(fluxo, ja, item)} + "
            f"{_fq(fluxo, q, item)} = {_fq(fluxo, total, item)}."
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
    q, erro = quantidade(fluxo, texto_qtd)
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

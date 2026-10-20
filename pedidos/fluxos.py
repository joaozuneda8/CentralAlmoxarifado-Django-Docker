"""Os formulários que montam um carrinho de materiais: limpeza e AB (públicos) e saída avulsa.

Cada fluxo diz de que catálogo lê, se a quantidade é inteira e se o estoque limita o pedido.
"""

from dataclasses import dataclass

from django.conf import settings
from django.http import Http404

from catalogo.catalogos import ItemCatalogo
from pedidos.regras import AB, AVULSA, LIMPEZA, normalizar_busca, qtd_estoque

LIMITE_RESULTADOS = 50


@dataclass(frozen=True)
class Fluxo:
    nome: str  # usado na URL
    origem: str
    titulo: str  # nos formulários públicos, o nome que o funcionário vê (o interno é o da Origem)
    inteiro: bool
    com_estoque: bool
    publico: bool
    # Limita pelo saldo exato do cadastro (decimal), sem mostrar o estoque na lista.
    limita_estoque: bool = False

    @property
    def max_itens(self) -> int | None:
        return settings.PEDIDOS_MAX_ITENS if self.publico else None

    # Textos do carrinho: o funcionário monta um pedido; o almoxarifado, os materiais de uma saída.
    @property
    def rotulo_carrinho(self) -> str:
        return "Seu pedido" if self.publico else "Materiais da saída"

    @property
    def rotulo_revisar(self) -> str:
        return "Revisar e enviar" if self.publico else "Revisar e registrar"

    @property
    def rotulo_enviar(self) -> str:
        return "Enviar pedido" if self.publico else "Registrar saída"

    @property
    def icone_enviar(self) -> str:
        return "enviar" if self.publico else "saida"


FLUXOS: dict[str, Fluxo] = {
    "limpeza": Fluxo(
        "limpeza",
        LIMPEZA,
        "Limpeza, copa e escritório",
        inteiro=False,
        com_estoque=False,
        publico=True,
    ),
    "ab": Fluxo(
        "ab",
        AB,
        "Ferramentas, peças e materiais",
        inteiro=True,
        com_estoque=True,
        publico=True,
    ),
    "avulsa": Fluxo(
        "avulsa",
        AVULSA,
        "Saída avulsa",
        inteiro=False,
        com_estoque=False,
        publico=False,
        limita_estoque=True,
    ),
}


def fluxo_publico(nome: str) -> Fluxo:
    fluxo = FLUXOS.get(nome)
    if fluxo is None or not fluxo.publico:
        raise Http404("Formulário desconhecido.")
    return fluxo


def _ordenados(valores) -> list[str]:
    return sorted({v for v in valores if v}, key=normalizar_busca)


def opcoes_filtro(fluxo: Fluxo, catalogo) -> list:
    """Limpeza e AB: [(grupo, [subgrupos])] dos materiais do catálogo. Avulsa: nenhum filtro."""
    catalogo = catalogo or []
    if fluxo.origem in (LIMPEZA, AB):
        return [
            (grupo, _ordenados(i.subgrupo for i in catalogo if i.grupo == grupo))
            for grupo in _ordenados(i.grupo for i in catalogo)
        ]
    return []


def classe_ab(item: ItemCatalogo) -> str:
    return " › ".join(p for p in (item.grupo, item.subgrupo) if p)


def _passa(fluxo: Fluxo, item: ItemCatalogo, filtro: str) -> bool:
    if not filtro:
        return True
    if fluxo.origem in (LIMPEZA, AB):
        return filtro in (item.grupo, classe_ab(item))
    return True


def _texto_busca(fluxo: Fluxo, item: ItemCatalogo) -> str:
    return item.nome if fluxo.publico else f"{item.nome} {item.codigo}"


def buscar(fluxo: Fluxo, catalogo, q: str, filtro: str) -> tuple[list[ItemCatalogo], int]:
    """Itens cujo nome contém todas as palavras de `q` (sem acento): os que podem ser pedidos
    primeiro e os bloqueados (sem estoque, duplicados) no fim, cada grupo na ordem do catálogo; os
    primeiros `LIMITE_RESULTADOS` e o total. A ordenação vem antes do corte, para nenhum material
    que pode ser pedido ficar de fora. Só a saída avulsa (equipe) busca também pelo código; os
    formulários públicos procuram só pelo nome."""
    from pedidos.carrinho import motivo_bloqueio

    palavras = normalizar_busca(q).split()
    achados = [
        i
        for i in catalogo or []
        if _passa(fluxo, i, filtro)
        and all(p in normalizar_busca(_texto_busca(fluxo, i)) for p in palavras)
    ]
    achados.sort(key=lambda i: bool(motivo_bloqueio(fluxo, i)))  # estável: mantém a ordem
    return achados[:LIMITE_RESULTADOS], len(achados)


@dataclass(frozen=True)
class Resultado:
    """Um material na lista de resultados, já com o que a tela mostra."""

    item: ItemCatalogo
    motivo: str  # por que não pode ser pedido ("" se pode)
    info: str  # unidade, ou o estoque disponível no AB
    classe: str
    estoque: str = ""  # "Estoque N" (saldo exato) onde `info` não o diz: limpeza e saída avulsa

    @property
    def linha_publica(self) -> str:
        """A informação do formulário público (sem código nem grupo): estoque e unidade."""
        unidade = "" if self.info == "—" else self.info
        return " · ".join(p for p in (self.estoque, unidade) if p) or self.info


def resultados(fluxo: Fluxo, itens) -> list[Resultado]:
    from pedidos.carrinho import motivo_bloqueio

    lista = []
    for i in itens:
        estoque = ""
        if fluxo.com_estoque:
            info = (
                f"{i.disponivel} {i.unidade} disponíveis"
                if i.unidade
                else f"{i.disponivel} disponíveis"
            )
        else:
            info = i.unidade or "—"
            estoque = f"Estoque {qtd_estoque(i.estoque)}"
        classe = i.grupo if fluxo.origem == AVULSA else classe_ab(i)
        lista.append(Resultado(i, motivo_bloqueio(fluxo, i), info, classe, estoque))
    return lista

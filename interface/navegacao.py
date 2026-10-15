"""Itens da barra lateral da área do almoxarifado.

Cada subprojeto acrescenta seus destinos a `ITENS_MENU`. A barra só espelha o que cada rota
permite; quem decide o acesso continua sendo a própria rota.
"""

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class ItemMenu:
    rotulo: str
    rota: str
    icone: str = ""
    so_equipe: bool = False


ITENS_MENU: tuple[ItemMenu, ...] = (
    ItemMenu("Painel", "pedidos:painel", "painel"),
    ItemMenu("Saída avulsa", "pedidos:avulsa", "saida"),
    ItemMenu("Automações", "automacoes:pagina", "robo"),
    ItemMenu("Curva ABC", "catalogo:curva", "grafico"),
    ItemMenu("Cadastros", "admin:index", "cadastros", so_equipe=True),
)


def menu(request) -> dict:
    """Context processor: `menu` para usuário autenticado; nada para anônimo."""
    usuario = getattr(request, "user", None)  # ausente se o middleware de auth não rodou
    if usuario is None or not usuario.is_authenticated:
        return {}
    correspondencia = getattr(request, "resolver_match", None)
    atual = correspondencia.view_name if correspondencia else None
    return {
        "menu": [
            {
                "rotulo": item.rotulo,
                "url": reverse(item.rota),
                "icone": item.icone,
                "atual": item.rota == atual,
            }
            for item in ITENS_MENU
            if usuario.is_staff or not item.so_equipe
        ]
    }

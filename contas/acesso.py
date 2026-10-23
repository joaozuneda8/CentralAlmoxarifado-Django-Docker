"""Acesso da Segurança do Trabalho (spec 008).

O sistema não tem papéis: todo usuário logado vê a parte interna inteira. O usuário da Segurança
do Trabalho é o que está no grupo `GRUPO_SEGURANCA_TRABALHO` e só abre as rotas de
`ROTAS_SEGURANCA_TRABALHO` (`contas.middleware`). O acesso é a participação no grupo, nunca
`is_staff` nem permissão: o superusuário passa em qualquer `has_perm`, e quem decide um pedido de
EPI precisa ser da Segurança do Trabalho.
"""

GRUPO_SEGURANCA_TRABALHO = "Segurança do Trabalho"

# As únicas rotas (nome com namespace) abertas ao usuário do grupo: a entrada e a saída, a fila e a
# decisão dos pedidos de EPI e as páginas públicas, que qualquer pessoa abre. Tudo o mais é negado
# por padrão, inclusive rota que alguém crie depois.
ROTAS_SEGURANCA_TRABALHO = frozenset(
    {
        "login",
        "logout",
        "pedidos:autorizacoes",
        "pedidos:autorizacao",
        "pedidos:decidir",
        "pedidos:inicio",
        "pedidos:formulario",
        "pedidos:materiais",
        "pedidos:carrinho",
        "pedidos:consulta_epi",
    }
)


def da_seguranca_trabalho(usuario) -> bool:
    """Se o usuário está autenticado e é do grupo da Segurança do Trabalho."""
    return bool(
        usuario is not None
        and usuario.is_authenticated
        and usuario.groups.filter(name=GRUPO_SEGURANCA_TRABALHO).exists()
    )

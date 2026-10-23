"""Disponibilidade dos materiais e dos centros de custo nos formulários (spec 009).

A disponibilidade efetiva de um material num formulário é a regra de origem de hoje mais as exceções
do administrador, sempre respeitando o cadastro (material oculto nunca é oferecido):

    efetiva = (regra_de_origem − retirados) ∪ acrescentados

`estado` é a regra pura (sem ORM, Princípio I); os serviços que gravam ficam no fim do módulo.
"""

from dataclasses import dataclass

# De onde vem a disponibilidade (ou a falta dela) de um material num formulário.
REGRA = "regra"  # a regra de origem o traz e nenhuma exceção o retira
ACRESCENTADO = "acrescentado"  # a regra não o traz; uma exceção o acrescenta
RETIRADO = "retirado"  # a regra o traz; uma exceção o retira
FORA = "fora"  # a regra não o traz e nada o acrescenta


@dataclass(frozen=True)
class Estado:
    disponivel: bool
    origem: str
    # A exceção não muda nada: retirar o que a regra não traz, ou acrescentar o que ela já traz.
    sem_efeito: bool
    # Oculto no cadastro: vale em todos os formulários e vence qualquer exceção.
    oculto: bool = False


def estado(oculto: bool, na_regra: bool, excecao: bool | None) -> Estado:
    """O estado efetivo do material no formulário. `excecao` é `True` (acrescenta), `False`
    (retira) ou `None` (sem exceção). Material oculto nunca está disponível, mas a origem e o "sem
    efeito" são os que valeriam sem o oculto, para a tela explicar."""
    if na_regra:
        if excecao is False:
            disponivel, origem, sem_efeito = False, RETIRADO, False
        else:
            disponivel, origem, sem_efeito = True, REGRA, excecao is True
    elif excecao is True:
        disponivel, origem, sem_efeito = True, ACRESCENTADO, False
    else:
        disponivel, origem, sem_efeito = False, FORA, excecao is False
    return Estado(disponivel and not oculto, origem, sem_efeito, oculto)

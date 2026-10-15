"""De/para de códigos: valida os pares, resolve o código canônico e consolida as saídas.

Traduz a consolidação da planilha MAPEAMENTO DE/PARA CONSOLIDADO (abas `DEPARA_MAP`, `DEPARA` e
`MOV_NORM`): o canônico de um código é o destino final da cadeia de pares, ou o próprio código se
não houver par. Diferente da planilha, a cadeia é seguida até o fim (ela segue dois saltos), e o
fator é o produto dos fatores da cadeia. Funções puras, sem ORM.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from pedidos.regras import norm_u

FORMATO_CODIGO = re.compile(r"^\d{3}\.\d{3}\.\d{3}$")
UM = Decimal("1")


class CicloDePara(ValueError):
    """Os pares formam um ciclo; `caminho` traz os códigos na ordem, fechando no primeiro."""

    def __init__(self, caminho: list[str]):
        self.caminho = caminho
        super().__init__(f"Os pares formam um ciclo: {' → '.join(caminho)}.")


@dataclass(frozen=True)
class Par:
    antigo: str
    novo: str
    fator: Decimal = UM


@dataclass(frozen=True)
class LinhaSaidas:
    """Saídas de um código no período, já somadas."""

    codigo: str
    ocorrencias: int
    qtd: Decimal
    valor: Decimal


@dataclass(frozen=True)
class LinhaConsolidada:
    """Saídas de um código canônico: ocorrências e valor como vieram, quantidade convertida."""

    canonico: str
    ocorrencias: int
    qtd: Decimal
    valor: Decimal


def validar_par(antigo: str, novo: str, fator: Decimal | None) -> list[str]:
    """Erros do par em si (sem olhar os outros pares), na ordem em que aparecem no formulário."""
    erros = []
    for rotulo, codigo in (("antigo", antigo), ("novo", novo)):
        if not FORMATO_CODIGO.match(codigo or ""):
            erros.append(f'O código {rotulo} "{codigo or ""}" não está no formato 000.000.000.')
    if norm_u(antigo) == norm_u(novo):
        erros.append("O código antigo e o código novo são iguais.")
    if fator is None or fator <= 0:
        erros.append("O fator precisa ser maior que zero.")
    return erros


def resolver_canonicos(pares: Iterable[Par]) -> dict[str, tuple[str, Decimal]]:
    """Código antigo normalizado (`norm_u`) → (código canônico, fator acumulado).

    Só os códigos que são antigos de algum par entram no mapa; para os demais, `canonico_de`
    devolve o próprio código. Um ciclo levanta `CicloDePara`.
    """
    destino = {norm_u(p.antigo): p for p in pares}
    resolvidos: dict[str, tuple[str, Decimal]] = {}
    for inicio in destino:
        caminho = [inicio]
        fator = UM
        atual = destino[inicio]
        while True:
            fator *= atual.fator
            seguinte = norm_u(atual.novo)
            if seguinte in caminho:
                nomes = [destino[c].antigo for c in caminho]
                raise CicloDePara([*nomes, destino[seguinte].antigo])
            if seguinte in resolvidos:
                canonico, resto = resolvidos[seguinte]
                resolvidos[inicio] = (canonico, fator * resto)
                break
            if seguinte not in destino:
                resolvidos[inicio] = (atual.novo, fator)
                break
            caminho.append(seguinte)
            atual = destino[seguinte]
    return resolvidos


def canonico_de(codigo: str, canonicos: dict[str, tuple[str, Decimal]]) -> tuple[str, Decimal]:
    """(canônico, fator) de `codigo`; sem par, o próprio código com fator 1."""
    return canonicos.get(norm_u(codigo), (codigo, UM))


def consolidar(
    linhas: Iterable[LinhaSaidas], canonicos: dict[str, tuple[str, Decimal]]
) -> list[LinhaConsolidada]:
    """Soma as saídas pelo canônico; a quantidade é multiplicada pelo fator do par."""
    somas: dict[str, list] = {}
    for linha in linhas:
        canonico, fator = canonico_de(linha.codigo, canonicos)
        soma = somas.setdefault(norm_u(canonico), [canonico, 0, Decimal(0), Decimal(0)])
        soma[1] += linha.ocorrencias
        soma[2] += linha.qtd * fator
        soma[3] += linha.valor
    return [LinhaConsolidada(*soma) for soma in somas.values()]

from decimal import Decimal

import pytest

from pedidos.regras import estoque_inteiro, norm_placa, norm_u


@pytest.mark.parametrize(
    ("entrada", "saida"),
    [("cza-1614", "CZA1614"), (" abc 1d23 ", "ABC1D23"), (None, ""), ("", "")],
)
def test_norm_placa(entrada, saida):
    assert norm_placa(entrada) == saida


@pytest.mark.parametrize(
    ("entrada", "saida"),
    [("  Oficina   mecânica ", "OFICINA MECANICA"), ("Conceição", "CONCEICAO"), (None, "")],
)
def test_norm_u(entrada, saida):
    assert norm_u(entrada) == saida


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("2,5", 2),
        (-3, 0),
        ("x", 0),
        (Decimal("12.0000"), 12),
        (Decimal("0.9"), 0),
        (None, 0),
        ("", 0),
        (10, 10),
        (Decimal("NaN"), 0),
    ],
)
def test_estoque_inteiro(valor, esperado):
    assert estoque_inteiro(valor) == esperado

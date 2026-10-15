from datetime import date, datetime
from decimal import Decimal

import openpyxl
import pytest
from django.utils import timezone

from implantacao.planilha import (
    ABAS,
    ErroPlanilha,
    data_celula,
    ler_xlsx,
    momento_celula,
    qtd_celula,
    texto_celula,
)
from tests.planilha_exemplo import abas_exemplo, salvar_xlsx


def test_le_todas_as_abas_com_numero_da_linha(tmp_path):
    abas = ler_xlsx(salvar_xlsx(abas_exemplo(), tmp_path / "p.xlsx"))
    assert set(abas) == set(ABAS)
    assert [linha["Nº"] for linha in abas["Pedidos"]] == ["P-000120", "P-000121", "AV-000122"]
    assert abas["Pedidos"][0]["_linha"] == 2
    assert isinstance(abas["Pedidos"][0]["Criado em"], datetime)


def test_linha_vazia_e_pulada_sem_mudar_a_numeracao(tmp_path):
    caminho = salvar_xlsx(abas_exemplo(), tmp_path / "p.xlsx")
    livro = openpyxl.load_workbook(caminho)
    livro["Pedidos"].insert_rows(3)  # linha 3 em branco
    livro.save(caminho)
    assert [linha["_linha"] for linha in ler_xlsx(caminho)["Pedidos"]] == [2, 4, 5]


def test_cabecalho_com_espacos_e_colunas_opcionais(tmp_path):
    exemplo = abas_exemplo()
    exemplo["Pedidos"] = [
        {(" Nº " if k == "Nº" else k): v for k, v in linha.items() if k != "Recibo impresso em"}
        for linha in exemplo["Pedidos"]
    ]
    abas = ler_xlsx(salvar_xlsx(exemplo, tmp_path / "p.xlsx"))
    assert abas["Pedidos"][0]["Nº"] == "P-000120"


def test_aba_e_coluna_faltando_aparecem_juntas(tmp_path):
    exemplo = abas_exemplo()
    del exemplo["Listas"]
    exemplo["Saídas"] = [
        {k: v for k, v in linha.items() if k != "Qtd"} for linha in exemplo["Saídas"]
    ]
    with pytest.raises(ErroPlanilha) as erro:
        ler_xlsx(salvar_xlsx(exemplo, tmp_path / "p.xlsx"))
    assert 'aba "Listas"' in str(erro.value)
    assert 'Saídas: coluna "Qtd"' in str(erro.value)


def test_cabecalho_repetido_vale_a_primeira_coluna(tmp_path):
    caminho = salvar_xlsx(abas_exemplo(), tmp_path / "p.xlsx")
    livro = openpyxl.load_workbook(caminho)
    folha = livro["Centros de Custo"]
    folha["D1"] = "DESCR"
    folha["D2"] = "outro"
    livro.save(caminho)
    assert ler_xlsx(caminho)["Centros de Custo"][0]["DESCR"] == "ETA II"


def test_exemplo_traz_colunas_opcionais_e_listas_completas(tmp_path):
    abas = ler_xlsx(salvar_xlsx(abas_exemplo(), tmp_path / "p.xlsx"))
    assert abas["Pedidos"][0]["Recibo impresso em"] == datetime(2026, 9, 2, 9, 5)
    assert abas["Pedidos"][1]["Recibo impresso em"] is None
    assert abas["Listas"][1]["Destinos"] is None
    assert abas["Listas"][0]["Funcionários"] == "Ana Exemplo"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, ""),
        ("  x ", "x"),
        ("'=SOMA(A1)", "=SOMA(A1)"),
        (12.0, "12"),
        (12, "12"),
        (1.5, "1.5"),
    ],
)
def test_texto_celula(valor, esperado):
    assert texto_celula(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (datetime(2026, 9, 2, 0, 0), date(2026, 9, 2)),
        (date(2026, 9, 2), date(2026, 9, 2)),
        ("02/09/2026", date(2026, 9, 2)),
        ("2026-09-02", date(2026, 9, 2)),
        ("", None),
        (None, None),
    ],
)
def test_data_celula(valor, esperado):
    assert data_celula(valor) == esperado


@pytest.mark.parametrize("valor", ["31/02/2026", "2/9/26", "ontem", 45000])
def test_data_celula_invalida(valor):
    with pytest.raises(ValueError):
        data_celula(valor)


@pytest.mark.parametrize(
    ("valor", "local"),
    [
        (datetime(2026, 9, 2, 17, 10), datetime(2026, 9, 2, 17, 10)),
        ("02/09/2026 17:10", datetime(2026, 9, 2, 17, 10)),
        ("02/09/2026 17:10:05", datetime(2026, 9, 2, 17, 10, 5)),
        ("02/09/2026", datetime(2026, 9, 2, 0, 0)),
    ],
)
def test_momento_celula_no_fuso_do_sistema(valor, local):
    momento = momento_celula(valor)
    assert timezone.is_aware(momento)
    assert timezone.localtime(momento).replace(tzinfo=None) == local


@pytest.mark.parametrize("valor", ["", None])
def test_momento_celula_vazio(valor):
    assert momento_celula(valor) is None


@pytest.mark.parametrize("valor", ["ontem", "31/02/2026 10:00", 45000])
def test_momento_celula_invalido(valor):
    with pytest.raises(ValueError):
        momento_celula(valor)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (1.5, Decimal("1.5")),
        (2, Decimal("2")),
        ("1,5", Decimal("1.5")),
        ("", None),
        (None, None),
        (0.30000000000000004, Decimal("0.300")),
    ],
)
def test_qtd_celula(valor, esperado):
    assert qtd_celula(valor) == esperado


@pytest.mark.parametrize("valor", ["1.5", "abc", -1, "-1", True])
def test_qtd_celula_invalida(valor):
    with pytest.raises(ValueError):
        qtd_celula(valor)

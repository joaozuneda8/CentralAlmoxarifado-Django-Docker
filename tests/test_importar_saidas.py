from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from catalogo.models import Importacao, SaidaSCPI
from scpi import relatorios
from scpi.gravacao import periodo_saidas
from scpi.leitura import ErroImportacao

pytestmark = pytest.mark.django_db
FIX = Path(__file__).parent / "fixtures" / "scpi"


def importar_janeiro():
    call_command(
        "importar_saidas_scpi",
        arquivo=FIX / "saidas.csv",
        desde="01/01/2026",
        ate="31/01/2026",
    )


def test_importa_saidas_sem_duplicar(capsys):
    importar_janeiro()
    assert SaidaSCPI.objects.count() == 5
    luva = SaidaSCPI.objects.get(id_requi="2", cadpro="013.005.007")
    assert (luva.data, luva.qtd, luva.valor, luva.item) == (
        date(2026, 1, 12),
        2,
        Decimal("6.2"),
        1,
    )
    imp = Importacao.objects.get()
    assert (imp.tipo, imp.situacao, imp.linhas) == ("SAIDAS", "SUCESSO", 5)
    assert (imp.periodo_de, imp.periodo_ate) == (date(2026, 1, 1), date(2026, 1, 31))
    assert imp.avisos == []
    assert "Saídas do SCPI (01/01/2026 a 31/01/2026): 5 linhas novas." in capsys.readouterr().out

    # Reimportar o mesmo período (a sobreposição de 7 dias) não duplica nada.
    importar_janeiro()
    assert SaidaSCPI.objects.count() == 5
    assert Importacao.objects.first().linhas == 0


def test_mesmo_material_duas_vezes_na_requisicao_guarda_as_duas_linhas():
    """A requisição 3 da fixture tem a luva em duas linhas (outra placa, outro destino): as duas
    são saídas de verdade e ficam, numeradas pela ordem no relatório."""
    importar_janeiro()
    luvas = SaidaSCPI.objects.filter(id_requi="3", cadpro="013.005.007").order_by("item")
    assert [s.item for s in luvas] == [1, 2]


def test_periodo_vazio_nao_e_erro(tmp_path):
    vazio = tmp_path / "s.csv"
    vazio.write_bytes((FIX / "saidas.csv").read_bytes().splitlines(keepends=True)[0])
    call_command("importar_saidas_scpi", arquivo=vazio, desde="01/01/2026", ate="02/01/2026")
    imp = Importacao.objects.get()
    assert (imp.situacao, imp.linhas) == ("SUCESSO", 0)


def test_primeiro_periodo_comeca_em_janeiro():
    assert periodo_saidas(date(2026, 10, 10)) == (date(2026, 1, 1), date(2026, 10, 10))


def test_periodo_seguinte_sobrepoe_sete_dias_ao_ultimo_sucesso():
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2026, 10, 9))
    Importacao.objects.create(tipo="SAIDAS", situacao="FALHA", periodo_ate=date(2026, 10, 10))
    Importacao.objects.create(tipo="ESTOQUE", situacao="SUCESSO", periodo_ate=date(2026, 10, 10))
    assert periodo_saidas(date(2026, 10, 10)) == (date(2026, 10, 2), date(2026, 10, 10))


def test_desde_e_ate_sobrescrevem():
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2026, 10, 9))
    assert periodo_saidas(date(2026, 10, 10), date(2026, 3, 1), date(2026, 3, 31)) == (
        date(2026, 3, 1),
        date(2026, 3, 31),
    )


def test_inicio_depois_do_fim_recusado_na_regra():
    with pytest.raises(ErroImportacao, match=r"\(10/10/2026\) é depois do fim \(01/10/2026\)"):
        periodo_saidas(date(2026, 10, 10), date(2026, 10, 10), date(2026, 10, 1))


def test_saida_retroativa_entra_na_importacao_seguinte(monkeypatch):
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2026, 1, 13))
    pedidos = []

    def baixar(de, ate):
        pedidos.append((de, ate))
        return (FIX / "saidas.csv").read_bytes()

    monkeypatch.setattr(relatorios, "baixar_saidas", baixar)
    monkeypatch.setattr(timezone, "localdate", lambda: date(2026, 1, 14))
    call_command("importar_saidas_scpi")
    assert pedidos == [(date(2026, 1, 6), date(2026, 1, 14))]  # cobre o dia 12
    assert SaidaSCPI.objects.filter(data=date(2026, 1, 12)).count() == 2
    assert Importacao.objects.first().periodo_ate == date(2026, 1, 14)


def test_inicio_depois_do_fim_e_recusado():
    with pytest.raises(CommandError, match="é depois do fim"):
        call_command(
            "importar_saidas_scpi",
            desde="10/10/2026",
            ate="01/10/2026",
            arquivo=FIX / "saidas.csv",
        )
    assert not Importacao.objects.exists()


def test_data_mal_escrita_na_opcao_e_recusada():
    with pytest.raises(CommandError, match="dd/mm/aaaa"):
        call_command("importar_saidas_scpi", desde="2026-01-01", arquivo=FIX / "saidas.csv")


def test_carga_historica_antiga_nao_faz_o_periodo_recuar():
    Importacao.objects.create(
        tipo="SAIDAS",
        situacao="SUCESSO",
        periodo_ate=date(2026, 10, 9),
        inicio=timezone.now() - timedelta(days=1),
    )
    # Carga histórica feita depois, em blocos: termina em 2024.
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", periodo_ate=date(2024, 12, 31))
    assert periodo_saidas(date(2026, 10, 10)) == (date(2026, 10, 2), date(2026, 10, 10))

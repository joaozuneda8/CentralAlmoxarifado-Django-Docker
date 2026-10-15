from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from catalogo.models import Importacao, Material
from scpi import relatorios
from scpi.gravacao import lista_curta

pytestmark = pytest.mark.django_db
FIX = Path(__file__).parent / "fixtures" / "scpi"


def cadastrar(*codigos, estoque=99):
    for codigo in codigos:
        Material.objects.create(codigo=codigo, nome=codigo, estoque=estoque)


def test_importa_saldos_e_zera_ausentes(capsys):
    cadastrar("001.001.001", "001.001.002", "013.005.007", "017.004")
    call_command("importar_estoque", arquivo=FIX / "estoque.csv")
    saldos = dict(Material.objects.values_list("codigo", "estoque"))
    assert saldos == {
        "001.001.001": Decimal("12"),
        "001.001.002": 0,
        "013.005.007": Decimal("1234.5"),
        "017.004": 0,
    }
    assert not Material.objects.filter(estoque_em__isnull=True).exists()
    assert Material.objects.values("estoque_em").distinct().count() == 1
    imp = Importacao.objects.get()
    assert (imp.tipo, imp.situacao, imp.linhas) == ("ESTOQUE", "SUCESSO", 2)
    assert imp.avisos == [
        "Quantidade inválida ignorada: 001.001.002 ('abc').",
        "Códigos com saldo sem cadastro (ignorados): 999.999.999.",
    ]
    assert "Estoque: 2 materiais com saldo." in capsys.readouterr().out


def test_codigo_repetido_vale_a_ultima_linha(tmp_path):
    cadastrar("001.001.001")
    arquivo = tmp_path / "e.csv"
    arquivo.write_bytes(b"CADPRO;QUAN3\r\n001.001.001;3\r\n001.001.001;7,5\r\n")
    call_command("importar_estoque", arquivo=arquivo)
    assert Material.objects.get().estoque == Decimal("7.5")
    assert Importacao.objects.get().avisos == [
        "Códigos repetidos no estoque (vale a última linha): 001.001.001."
    ]


def test_estoque_vazio_aborta_sem_alterar_saldos(tmp_path):
    Material.objects.create(codigo="001.001.001", nome="X", estoque=5)
    vazio = tmp_path / "v.csv"
    vazio.write_bytes(b"\xef\xbb\xbfCADPRO;QUAN3\r\n")
    with pytest.raises(CommandError, match="não tem nenhum material"):
        call_command("importar_estoque", arquivo=vazio)
    m = Material.objects.get()
    assert m.estoque == 5 and m.estoque_em is None
    assert Importacao.objects.get().situacao == "FALHA"


def test_sem_arquivo_baixa_do_scpi(monkeypatch):
    cadastrar("001.001.001")
    monkeypatch.setattr(relatorios, "baixar_estoque", lambda: b"CADPRO;QUAN3\r\n001.001.001;4\r\n")
    call_command("importar_estoque")
    assert Material.objects.get().estoque == 4


def test_lista_curta():
    assert lista_curta([str(n) for n in range(10)]) == "0, 1, 2, 3, 4, 5, 6, 7 e mais 2"
    assert lista_curta(["a", "b"]) == "a, b"


def test_codigo_igual_para_o_banco_recebe_o_saldo(tmp_path):
    cadastrar("000.009.0-a")
    arquivo = tmp_path / "e.csv"
    arquivo.write_bytes(b"CADPRO;QUAN3\r\n000.009.0-A;6\r\n")
    call_command("importar_estoque", arquivo=arquivo)
    assert Material.objects.get().estoque == 6
    assert Importacao.objects.get().avisos == []

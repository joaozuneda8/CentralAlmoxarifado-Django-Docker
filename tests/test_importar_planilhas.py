import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import DatabaseError

from catalogo.models import CentroCusto, ItemLimpeza, Opcao
from pedidos.consultas import lotes_pendentes, lotes_travados
from pedidos.models import Atendimento, LinhaSaida, Pedido, Sequencia
from tests.cenario import criar_pedido, montar_cenario
from tests.planilha_exemplo import abas_exemplo, salvar_xlsx

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _antes_da_virada(settings):
    settings.LANCAMENTO_REAL = False


@pytest.fixture
def xlsx(tmp_path):
    return lambda abas=None: str(salvar_xlsx(abas or abas_exemplo(), tmp_path / "planilha.xlsx"))


def importar(caminho, *args):
    saida = io.StringIO()
    call_command("importar_planilhas", "--arquivo", caminho, *args, stdout=saida)
    return saida.getvalue()


def test_importa_a_planilha_de_ponta_a_ponta(xlsx):
    montar_cenario()
    saida = importar(xlsx())
    assert "Pedidos: 3 · itens: 4 · atendimentos: 3 · linhas de saída: 4 (pendentes: 1)" in saida
    assert "último número: 122" in saida
    p = Pedido.objects.get(numero="P-000120")
    assert (
        p.situacao_scpi.rotulo == "Lançado 003354/26" and p.atendimento.recebedor == "Ana Exemplo"
    )
    planilha = get_user_model().objects.get(username="planilha")
    assert not planilha.is_active and not planilha.has_usable_password()
    assert p.atendimento.atendido_por == planilha
    assert Pedido.objects.get(numero="AV-000122").registrado_por == planilha
    assert Pedido.objects.get(numero="P-000120").registrado_por is None
    assert lotes_pendentes() == 1 and [t.lote for t in lotes_travados()] == ["AV-000122"]
    assert Sequencia.objects.get(nome="PEDIDOS").ultimo == 122
    assert list(CentroCusto.objects.order_by("codigo").values_list("codigo", flat=True)) == [
        "101",
        "102",
        "205",
    ]
    assert Opcao.valores(Opcao.Lista.FUNCIONARIO) == ["Ana Exemplo"]
    assert ItemLimpeza.objects.get(material__codigo="023.001.002").nome_exibido == "Detergente"


def test_reimportar_substitui_sem_duplicar(xlsx):
    montar_cenario()
    importar(xlsx())
    abas = abas_exemplo()
    abas["Saídas"][2].update({"Requisição": "003400/26", "Status SCPI": "LANÇADA"})
    importar(xlsx(abas))
    assert Pedido.objects.count() == 3 and LinhaSaida.objects.count() == 4
    assert LinhaSaida.objects.get(lote="P-000121").status == "LANCADA" and lotes_pendentes() == 0


def test_dry_run_nao_grava(xlsx):
    montar_cenario()
    centros, itens = CentroCusto.objects.count(), ItemLimpeza.objects.count()
    saida = importar(xlsx(), "--dry-run")
    assert "Pedidos: 3" in saida and "Simulação: nada foi gravado." in saida
    assert Pedido.objects.count() == 0 and Sequencia.objects.count() == 0
    assert CentroCusto.objects.count() == centros and ItemLimpeza.objects.count() == itens
    assert not get_user_model().objects.filter(username="planilha").exists()


def test_dry_run_nao_apaga_o_que_ja_estava_no_banco(xlsx):
    montar_cenario()
    importar(xlsx())
    abas = abas_exemplo()
    abas["Centros de Custo"] = abas["Centros de Custo"][:1]
    importar(xlsx(abas), "--dry-run")
    assert CentroCusto.objects.count() == 3 and Pedido.objects.count() == 3


def test_dry_run_recusa_igual_a_gravacao(xlsx, settings):
    montar_cenario()
    settings.LANCAMENTO_REAL = True
    with pytest.raises(CommandError, match="LANCAMENTO_REAL=1"):
        importar(xlsx(), "--dry-run")


def test_dry_run_aplica_as_travas_do_banco(xlsx):
    montar_cenario()
    feito_no_django = criar_pedido()
    with pytest.raises(CommandError, match=f"não estão na planilha: {feito_no_django.numero}"):
        importar(xlsx(), "--dry-run")
    assert list(Pedido.objects.all()) == [feito_no_django]


@pytest.mark.parametrize("modo", [[], ["--dry-run"]])
def test_erro_de_banco_vira_erro_do_comando(xlsx, monkeypatch, modo):
    def estoura(carga):
        raise DatabaseError("Data too long for column 'x'")

    monkeypatch.setattr("implantacao.management.commands.importar_planilhas.gravar", estoura)
    with pytest.raises(CommandError, match="Data too long"):
        importar(xlsx(), *modo)


def test_planilha_com_erro_nao_grava_nada(xlsx):
    montar_cenario()
    centros_antes = CentroCusto.objects.count()
    abas = abas_exemplo()
    abas["Itens"][0]["Qtd pedida"] = "1.5"
    with pytest.raises(CommandError, match=r"nada foi gravado:(.|\n)*Itens, linha 2"):
        importar(xlsx(abas))
    assert Pedido.objects.count() == 0 and CentroCusto.objects.count() == centros_antes


def test_recusa_depois_da_virada(xlsx, settings):
    montar_cenario()
    importar(xlsx())
    settings.LANCAMENTO_REAL = True
    abas = abas_exemplo()
    abas["Saídas"][2].update({"Requisição": "003400/26", "Status SCPI": "LANÇADA"})
    with pytest.raises(CommandError, match="LANCAMENTO_REAL=1"):
        importar(xlsx(abas))
    assert Pedido.objects.count() == 3
    assert LinhaSaida.objects.get(lote="P-000121").status == "PENDENTE"
    assert lotes_pendentes() == 1


def test_recusa_atendimento_feito_no_django(xlsx):
    montar_cenario()
    importar(xlsx())
    atendimento = Atendimento.objects.get(pedido__numero="P-000121")
    atendimento.atendido_por = get_user_model().objects.create_user("12345", password="x")
    atendimento.save()
    with pytest.raises(CommandError, match=r"atendimentos feitos no Django: P-000121\.") as exc:
        importar(xlsx())
    assert "VIRADA.md" in str(exc.value)
    assert Pedido.objects.count() == 3
    assert Atendimento.objects.get(pedido__numero="P-000121").atendido_por.username == "12345"


def test_recusa_lista_os_atendimentos_em_ordem(xlsx):
    montar_cenario()
    importar(xlsx())
    usuario = get_user_model().objects.create_user("12345", password="x")
    Atendimento.objects.update(atendido_por=usuario)
    with pytest.raises(CommandError, match=r"Django: AV-000122, P-000120, P-000121\."):
        importar(xlsx())


def test_recusa_pedido_do_banco_fora_da_planilha(xlsx):
    montar_cenario()
    feito_no_django = criar_pedido()
    with pytest.raises(
        CommandError, match=f"não estão na planilha: {feito_no_django.numero}"
    ) as exc:
        importar(xlsx())
    assert "pelo shell" in str(exc.value) and "VIRADA.md" in str(exc.value)
    assert list(Pedido.objects.all()) == [feito_no_django]


def test_recusa_sem_cadastro_do_scpi(xlsx):
    with pytest.raises(CommandError, match="importar_cadastro"):
        importar(xlsx())


def test_item_de_limpeza_sem_material_vira_aviso(xlsx):
    montar_cenario()
    abas = abas_exemplo()
    abas["Lista_Limpeza"].append(
        {
            "Código": "999.999.999",
            "Categoria": "Limpeza",
            "Nome exibido": "",
            "Unidade exibida": "",
            "_linha": 4,
        }
    )
    saida = importar(xlsx(abas))
    assert "Aviso: Lista_Limpeza: código 999.999.999 não está no cadastro" in saida
    assert ItemLimpeza.objects.count() == 2


def test_arquivo_sem_aba_obrigatoria(xlsx):
    abas = abas_exemplo()
    del abas["Itens"]
    with pytest.raises(CommandError, match='aba "Itens"'):
        importar(xlsx(abas))

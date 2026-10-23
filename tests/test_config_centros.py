"""Os destinos de cada formulário a partir da configuração (spec 009, FR-005 a FR-013)."""

import pytest

from catalogo.catalogos import MODO_DESTINO, centros_do_formulario
from catalogo.models import CentroCusto, CentroFormulario, Formulario
from pedidos.regras import (
    AB,
    EPIS,
    LIMPEZA,
    OFICINA,
    VIATURAS,
    Centro,
    opcoes_destino,
    resolver_destino,
)
from tests.config_cenario import criar_centro, habilitar

pytestmark = pytest.mark.django_db


def destinos(origem) -> list[str]:
    return opcoes_destino(centros_do_formulario(origem))


def test_cada_formulario_publico_tem_um_modo_de_destino():
    assert set(MODO_DESTINO) == {LIMPEZA, AB, EPIS, VIATURAS, OFICINA}


def test_modo_padrao_oferece_a_descricao_e_descricao_placa_para_a_linha_com_placa():
    criar_centro("ETA I", "12", formularios=[LIMPEZA, AB, EPIS])
    criar_centro("ETA I", "13", "AAA1A11", formularios=[LIMPEZA, AB, EPIS])
    criar_centro("PICKUP 01", "31", "ABC1D23", formularios=[LIMPEZA])
    assert destinos(LIMPEZA) == ["ETA I", "PICKUP 01", "ETA I — AAA1A11", "PICKUP 01 — ABC1D23"]
    assert destinos(AB) == ["ETA I", "ETA I — AAA1A11"]
    assert destinos(EPIS) == ["ETA I", "ETA I — AAA1A11"]


def test_o_padrao_devolve_a_linha_com_a_placa_do_cadastro():
    criar_centro("ETA I", "13", "AAA1A11", formularios=[LIMPEZA])
    assert centros_do_formulario(LIMPEZA) == [Centro("ETA I", "13", "AAA1A11")]


def test_sem_placa_oferece_uma_por_descricao_com_o_primeiro_codigo_e_sem_placa():
    criar_centro("EQUIPE NORTE", "52", "AAA1A11", formularios=[VIATURAS])
    criar_centro("EQUIPE NORTE", "51", formularios=[VIATURAS])
    criar_centro("EQUIPE SUL", "60", formularios=[VIATURAS])
    assert centros_do_formulario(VIATURAS) == [
        Centro("EQUIPE NORTE", "51"),
        Centro("EQUIPE SUL", "60"),
    ]
    assert destinos(VIATURAS) == ["EQUIPE NORTE", "EQUIPE SUL"]


def test_oficina_linha_com_placa_so_como_descricao_placa_e_sem_placa_como_a_descricao():
    criar_centro("OFICINA MECÂNICA", "20", formularios=[OFICINA])
    criar_centro("PICKUP 01", "31", "ABC1D23", formularios=[OFICINA])
    criar_centro("RETRO A", "41", "XYZ9K99", formularios=[OFICINA])
    assert centros_do_formulario(OFICINA) == [
        Centro("OFICINA MECÂNICA", "20"),
        Centro("PICKUP 01", "31", "ABC1D23", so_com_placa=True),
        Centro("RETRO A", "41", "XYZ9K99", so_com_placa=True),
    ]
    assert destinos(OFICINA) == [
        "OFICINA MECÂNICA",
        "PICKUP 01 — ABC1D23",
        "RETRO A — XYZ9K99",
    ]


def test_oficina_aceita_a_placa_sozinha_como_destino():
    criar_centro("PICKUP 01", "31", "ABC1D23", formularios=[OFICINA])
    assert resolver_destino("abc-1d23", centros_do_formulario(OFICINA)) == "PICKUP 01 — ABC1D23"


def test_centro_inativo_nao_sai_em_nenhum_modo():
    for formulario in (LIMPEZA, VIATURAS, OFICINA):
        criar_centro(f"CENTRO {formulario}", f"9{len(formulario)}", formularios=[formulario])
    criar_centro("PLACA INATIVA", "70", "QQQ1Q11", formularios=[OFICINA], ativo=False)
    CentroCusto.objects.update(ativo=False)
    assert all(not centros_do_formulario(f) for f in (LIMPEZA, VIATURAS, OFICINA))


def test_reativar_o_centro_devolve_a_associacao_que_ficou_guardada():
    centro = criar_centro("ETA I", "12", formularios=[LIMPEZA, AB])
    CentroCusto.objects.filter(pk=centro.pk).update(ativo=False)
    assert centros_do_formulario(LIMPEZA) == []
    assert CentroFormulario.objects.filter(centro=centro).count() == 2
    CentroCusto.objects.filter(pk=centro.pk).update(ativo=True)
    assert destinos(LIMPEZA) == ["ETA I"] and destinos(AB) == ["ETA I"]


def test_habilitar_num_formulario_nao_o_habilita_nos_outros():
    criar_centro("ETA I", "12", formularios=[LIMPEZA])
    assert destinos(LIMPEZA) == ["ETA I"]
    for outro in (AB, VIATURAS, OFICINA, EPIS):
        assert destinos(outro) == []


def test_centro_novo_nao_esta_em_formulario_nenhum():
    CentroCusto.objects.create(descricao="SETOR NOVO", codigo="90")
    assert all(not centros_do_formulario(f) for f in Formulario.values)


def test_lista_vazia_quando_nada_esta_habilitado():
    assert all(centros_do_formulario(f) == [] for f in Formulario.values)


def test_habilitar_depois_aparece_sem_reiniciar():
    centro = criar_centro("ETA I", "12")
    assert destinos(AB) == []
    habilitar(centro, AB)
    assert destinos(AB) == ["ETA I"]

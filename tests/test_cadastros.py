import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

from catalogo.models import CentroCusto, ItemLimpeza, Material, Opcao

pytestmark = pytest.mark.django_db


def material(codigo="1001", nome="Detergente"):
    return Material.objects.create(codigo=codigo, nome=nome, unidade="UN")


def test_codigo_do_material_e_unico():
    material()
    with pytest.raises(IntegrityError):
        material()


def test_valores_da_opcao_so_ativos_e_em_ordem():
    Opcao.objects.create(lista="DESTINO", valor="ETA II", ordem=2)
    Opcao.objects.create(lista="DESTINO", valor="ETA I", ordem=1)
    Opcao.objects.create(lista="DESTINO", valor="Antigo", ordem=0, ativo=False)
    Opcao.objects.create(lista="TIPO_SAIDA", valor="BALCÃO")
    assert Opcao.valores("DESTINO") == ["ETA I", "ETA II"]


def test_opcao_repetida_na_mesma_lista_e_recusada():
    Opcao.objects.create(lista="DESTINO", valor="ETA I")
    with pytest.raises(IntegrityError):
        Opcao.objects.create(lista="DESTINO", valor="ETA I")


def test_placa_e_normalizada_ao_gravar():
    cc = CentroCusto.objects.create(descricao="FROTA", codigo="10", placa="cza-1614")
    assert cc.placa == "CZA1614"


def test_mesma_placa_em_outro_formato_e_recusada():
    CentroCusto.objects.create(descricao="FROTA", codigo="10", placa="CZA1614")
    outro = CentroCusto(descricao="OFICINA", codigo="20", placa="cza 1614")
    with pytest.raises(ValidationError, match="CZA1614"):
        outro.full_clean()


def test_varias_linhas_sem_placa_sao_aceitas():
    CentroCusto.objects.create(descricao="FROTA", codigo="10")
    CentroCusto(descricao="OFICINA", codigo="20").full_clean()


def test_categoria_do_item_de_limpeza_vem_das_opcoes():
    Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Limpeza")
    m = material()
    ItemLimpeza(material=m, categoria="Limpeza").full_clean()
    with pytest.raises(ValidationError, match="Copa"):
        ItemLimpeza(material=m, categoria="Copa").full_clean()


def test_material_aparece_uma_vez_na_lista_de_limpeza():
    m = material()
    ItemLimpeza.objects.create(material=m, categoria="Limpeza")
    with pytest.raises(IntegrityError):
        ItemLimpeza.objects.create(material=m, categoria="Limpeza")


@pytest.mark.parametrize("modelo", ["material", "itemlimpeza", "centrocusto", "opcao"])
def test_listas_do_admin_abrem(admin_client, modelo):
    assert admin_client.get(reverse(f"admin:catalogo_{modelo}_changelist")).status_code == 200


def test_material_e_somente_leitura_no_admin(admin_client):
    m = material()
    assert admin_client.get(reverse("admin:catalogo_material_add")).status_code == 403
    r = admin_client.post(
        reverse("admin:catalogo_material_change", args=[m.pk]),
        {"codigo": "1001", "nome": "Outro nome"},
    )
    m.refresh_from_db()
    assert r.status_code == 403 and m.nome == "Detergente"


def test_admin_recusa_placa_repetida(admin_client):
    CentroCusto.objects.create(descricao="FROTA", codigo="10", placa="CZA1614")
    r = admin_client.post(
        reverse("admin:catalogo_centrocusto_add"),
        {"descricao": "OFICINA", "codigo": "20", "placa": "cza-1614"},
    )
    assert r.status_code == 200 and "CZA1614" in r.text
    assert CentroCusto.objects.count() == 1


def test_admin_do_item_de_limpeza_oferece_categorias_e_busca_material(admin_client):
    Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Copa/cozinha")
    r = admin_client.get(reverse("admin:catalogo_itemlimpeza_add"))
    assert "Copa/cozinha" in r.text
    assert "admin-autocomplete" in r.text


def _item_com_categoria_desativada():
    copa = Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Copa")
    item = ItemLimpeza.objects.create(material=material(), categoria="Copa", ordem=1)
    copa.ativo = False
    copa.save()
    return item


def test_item_antigo_pode_ser_editado_sem_trocar_a_categoria_desativada():
    item = _item_com_categoria_desativada()
    item.nome_exibido = "Detergente neutro"
    item.full_clean()


def test_ordem_na_lista_salva_mesmo_com_categoria_desativada(admin_client):
    item = _item_com_categoria_desativada()
    r = admin_client.post(
        reverse("admin:catalogo_itemlimpeza_changelist"),
        {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-0-id": str(item.pk),
            "form-0-ordem": "5",
            "_save": "Salvar",
        },
    )
    assert r.status_code == 302
    item.refresh_from_db()
    assert item.ordem == 5


def test_trocar_para_categoria_desativada_continua_recusado():
    item = _item_com_categoria_desativada()
    Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Limpeza")
    item.categoria = "Limpeza"
    item.save()
    item.categoria = "Copa"
    with pytest.raises(ValidationError, match="Copa"):
        item.full_clean()


def test_banco_recusa_placa_repetida_mesmo_sem_full_clean():
    CentroCusto.objects.create(descricao="FROTA", codigo="10", placa="CZA1614")
    with pytest.raises(IntegrityError):
        CentroCusto.objects.create(descricao="OFICINA", codigo="20", placa="cza-1614")


def test_banco_aceita_varias_linhas_sem_placa():
    CentroCusto.objects.create(descricao="FROTA", codigo="10", placa="")
    CentroCusto.objects.create(descricao="OFICINA", codigo="20", placa="---")
    CentroCusto.objects.create(descricao="PATIO", codigo="30")
    assert CentroCusto.objects.filter(placa__isnull=True).count() == 3

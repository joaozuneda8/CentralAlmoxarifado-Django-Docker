"""Manutenção da escolha da oficina no admin (spec 007, US3, FR-012, FR-012a, SC-004): vale no
próximo acesso ao formulário, sem nova publicação."""

import pytest
from django.urls import reverse

from catalogo.models import Material, MaterialOficina, Opcao
from tests.oficina_cenario import FILTRO, FITA, OLEO, montar_oficina

pytestmark = pytest.mark.django_db

BUSCA = reverse("pedidos:materiais", args=["oficina"])


@pytest.fixture(autouse=True)
def cenario():
    montar_oficina()


def acha(client, q, codigo):
    return f'data-codigo="{codigo}"' in client.get(BUSCA, {"q": q}).text


def test_os_materiais_da_oficina_no_admin(admin_client):
    url = reverse("admin:catalogo_materialoficina_changelist")
    assert "ÓLEO LUBRIFICANTE 15W40" in admin_client.get(url).text
    assert admin_client.get(url, {"q": OLEO}).status_code == 200
    fita = Material.objects.get(codigo=FITA)
    r = admin_client.post(reverse("admin:catalogo_materialoficina_add"), {"material": fita.pk})
    assert r.status_code == 302 and MaterialOficina.objects.filter(material=fita).exists()
    # De novo: recusado.
    r = admin_client.post(reverse("admin:catalogo_materialoficina_add"), {"material": fita.pk})
    assert r.status_code == 200 and MaterialOficina.objects.filter(material=fita).count() == 1


def test_autocomplete_do_material():
    from django.contrib import admin

    assert admin.site._registry[MaterialOficina].autocomplete_fields == ["material"]


def test_incluir_um_avulso_vale_no_proximo_acesso(client, admin_client):
    assert not acha(client, "fita", FITA)
    fita = Material.objects.get(codigo=FITA)
    admin_client.post(reverse("admin:catalogo_materialoficina_add"), {"material": fita.pk})
    assert acha(client, "fita", FITA)


def test_a_lista_de_grupos_no_admin(client, admin_client):
    grupo = Opcao.objects.get(lista=Opcao.Lista.GRUPO_OFICINA)
    admin_client.post(reverse("admin:catalogo_opcao_delete", args=[grupo.pk]), {"post": "yes"})
    assert not acha(client, "filtro", FILTRO)
    r = admin_client.post(
        reverse("admin:catalogo_opcao_add"),
        {"lista": "GRUPO_OFICINA", "valor": "AUTO PECAS", "ordem": "0", "ativo": "on"},
    )
    assert r.status_code == 302
    assert acha(client, "filtro", FILTRO)

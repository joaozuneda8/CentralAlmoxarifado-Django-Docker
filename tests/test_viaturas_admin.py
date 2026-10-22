"""Manutenção da lista de peças e da marca dos centros no admin (spec 006, US3, FR-007, FR-011,
SC-003): vale no próximo acesso ao formulário, sem nova publicação."""

import re

import pytest
from django.urls import reverse

from catalogo.models import CentroCusto, Material, PecaViatura
from tests.viaturas_cenario import FITA, ISOLANTE, TUBO, montar_viaturas

pytestmark = pytest.mark.django_db

CARRINHO = reverse("pedidos:carrinho", args=["viaturas"])


@pytest.fixture(autouse=True)
def cenario():
    montar_viaturas()


def nomes_da_folha(client):
    return re.findall(r"<strong>([^<]+)</strong>", client.post(CARRINHO, {"folha_abrir": "1"}).text)


def test_a_lista_no_admin(admin_client):
    url = reverse("admin:catalogo_pecaviatura_changelist")
    html = admin_client.get(url).text
    assert "Tubo PVC 3/4 Soldável Marrom (metro)" in html and 'name="form-0-ordem"' in html
    nova = admin_client.post(
        reverse("admin:catalogo_pecaviatura_add"),
        {"material": Material.objects.get(codigo=ISOLANTE).pk, "nome_exibido": "", "ordem": 9},
    )
    assert (
        nova.status_code == 302 and PecaViatura.objects.filter(material__codigo=ISOLANTE).exists()
    )
    repetida = admin_client.post(
        reverse("admin:catalogo_pecaviatura_add"),
        {"material": Material.objects.get(codigo=FITA).pk, "nome_exibido": "", "ordem": 1},
    )
    assert repetida.status_code == 200 and "já existe" in repetida.text


def test_incluir_retirar_e_reordenar_valem_no_proximo_acesso(client):
    assert nomes_da_folha(client)[0] == "Tubo PVC 3/4 Soldável Marrom (metro)"
    PecaViatura.objects.create(material=Material.objects.get(codigo=ISOLANTE), ordem=0)
    PecaViatura.objects.filter(material__codigo=TUBO).delete()
    PecaViatura.objects.filter(material__codigo=FITA).update(ordem=99)
    nomes = nomes_da_folha(client)
    assert nomes[0] == "FITA ISOLANTE" and nomes[-1] == "FITA VEDA ROSCA"
    assert "Tubo PVC 3/4 Soldável Marrom (metro)" not in nomes


def test_a_marca_dos_centros_no_admin(admin_client):
    html = admin_client.get(reverse("admin:catalogo_centrocusto_changelist")).text
    assert "Equipe de manutenção" in html
    assert "equipe_manutencao__exact" in html  # o filtro
    marcados = admin_client.get(
        reverse("admin:catalogo_centrocusto_changelist"), {"equipe_manutencao__exact": "1"}
    ).text
    assert "BBB2B22" in marcados and "ETA II" not in marcados
    assert CentroCusto.objects.filter(equipe_manutencao=True).count() == 1

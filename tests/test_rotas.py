import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    ("rota", "args", "caminho"),
    [
        ("pedidos:inicio", [], "/"),
        ("pedidos:formulario", ["limpeza"], "/pedido/limpeza/"),
        ("pedidos:painel", [], "/painel/"),
        ("login", [], "/painel/entrar/"),
        ("logout", [], "/painel/sair/"),
        ("pedidos:detalhe", ["P-000001"], "/painel/pedidos/P-000001/"),
        ("pedidos:avulsa", [], "/painel/saida-avulsa/"),
        ("automacoes:pagina", [], "/painel/automacoes/"),
        ("automacoes:atualizar", [], "/painel/automacoes/atualizar/"),
        ("automacoes:lancar", [], "/painel/automacoes/lancar/"),
        ("catalogo:curva", [], "/painel/catalogo/curva/"),
        ("admin:index", [], "/admin/"),
    ],
)
def test_area_interna_fica_em_painel(rota, args, caminho):
    assert reverse(rota, args=args) == caminho


@pytest.mark.django_db
def test_caminho_antigo_nao_existe_mais(client):
    assert client.get("/almoxarifado/").status_code == 404

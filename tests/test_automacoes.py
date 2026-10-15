import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

pytestmark = pytest.mark.django_db

URL = reverse("automacoes:pagina")
ABAS = ["visao-geral", "lancamento", "cadastro", "estoque", "saidas"]


@pytest.fixture
def usuario_logado(client):
    usuario = get_user_model().objects.create_user(username="12345", password="x")
    client.force_login(usuario)
    return usuario


def aba_ativa(html):
    return re.search(r'<button[^>]*id="aba-([a-z-]+)"[^>]*aria-selected="true"', html).group(1)


def test_pagina_exige_login(client):
    r = client.get(URL)
    assert r.status_code == 302 and r.url.startswith(reverse("login"))


def test_pagina_tem_as_cinco_abas_em_ordem(client, usuario_logado):
    r = client.get(URL)
    assert r.status_code == 200
    assert "<h1" in r.text and ">Automações<" in r.text
    assert "data-abas" in r.text
    ids = re.findall(r'id="aba-([a-z-]+)"', r.text)
    assert ids == ABAS
    for chave in ABAS:
        assert f'id="painel-{chave}"' in r.text


@pytest.mark.parametrize(
    "consulta, esperada",
    [
        ("", "visao-geral"),
        ("?aba=situacao", "visao-geral"),
        ("?aba=inexistente", "visao-geral"),
        ("?aba=lancamento", "lancamento"),
        ("?aba=estoque", "estoque"),
    ],
)
def test_aba_pedida(client, usuario_logado, consulta, esperada):
    assert aba_ativa(client.get(URL + consulta).text) == esperada


@pytest.mark.parametrize(
    "alvo, id_esperado",
    [("section#situacao-catalogo", "situacao-catalogo"), ("section#lancamentos", "lancamentos")],
)
def test_htmx_devolve_so_a_regiao_do_alvo(client, usuario_logado, alvo, id_esperado):
    r = client.get(URL, HTTP_HX_REQUEST="true", HTTP_HX_TARGET=alvo)
    assert "<html" not in r.text
    assert r.text.lstrip().startswith(f'<section id="{id_esperado}"')


def test_htmx_com_alvo_desconhecido_ou_restauracao_devolve_a_pagina(client, usuario_logado):
    r = client.get(URL, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="div#outro")
    assert "<html" in r.text
    r = client.get(
        URL,
        HTTP_HX_REQUEST="true",
        HTTP_HX_TARGET="section#lancamentos",
        HTTP_HX_HISTORY_RESTORE_REQUEST="true",
    )
    assert "<html" in r.text


def test_vary_nos_cabecalhos_do_htmx(client, usuario_logado):
    vary = client.get(URL)["Vary"]
    for cabecalho in ("HX-Request", "HX-Target", "HX-History-Restore-Request"):
        assert cabecalho in vary


# Rotas apagadas: as páginas Catálogo e Lançamentos SCPI e suas ações.


@pytest.mark.parametrize(
    "metodo, caminho",
    [
        ("get", "/painel/lancamentos/"),
        ("post", "/painel/lancamentos/iniciar/"),
        ("post", "/painel/lancamentos/P-1/resolver/"),
        ("get", "/painel/catalogo/"),
        ("post", "/painel/catalogo/atualizar/"),
        ("post", "/painel/catalogo/importar/estoque/"),
    ],
)
def test_rotas_antigas_nao_existem(client, usuario_logado, metodo, caminho):
    assert getattr(client, metodo)(caminho).status_code == 404


@pytest.mark.parametrize(
    "nome, args",
    [
        ("pedidos:lancamentos", []),
        ("pedidos:lancar", []),
        ("pedidos:resolver", ["P-1"]),
        ("catalogo:situacao", []),
        ("catalogo:atualizar", []),
        ("catalogo:importar", ["estoque"]),
    ],
)
def test_nomes_antigos_nao_existem(nome, args):
    with pytest.raises(NoReverseMatch):
        reverse(nome, args=args)


def test_curva_continua(client, usuario_logado):
    assert client.get(reverse("catalogo:curva")).status_code == 200


def item_atual(html, url, rotulo):
    return re.search(
        rf'<a class="app-menu-item" href="{re.escape(url)}" aria-current="page">'
        rf'<svg class="icone".*?</svg><span>{rotulo}</span></a>',
        html,
        re.S,
    )


def test_menu_tem_automacoes_entre_saida_avulsa_e_curva(admin_client):
    texto = admin_client.get(reverse("pedidos:painel")).text
    rotulos = ["Painel", "Saída avulsa", "Automações", "Curva ABC", "Cadastros"]
    posicoes = [texto.index(f"<span>{r}</span>") for r in rotulos]
    assert posicoes == sorted(posicoes)
    assert "<span>Catálogo</span>" not in texto and "<span>Lançamentos SCPI</span>" not in texto


@pytest.mark.parametrize("aba", ["visao-geral", "lancamento", "estoque"])
def test_automacoes_fica_marcado_em_todas_as_abas(admin_client, aba):
    texto = admin_client.get(URL, {"aba": aba}).text
    assert item_atual(texto, URL, "Automações")

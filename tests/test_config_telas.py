"""A página Formulários (spec 009, US1 e US2): abas, listas, gravações e volta ao mesmo estado."""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse

from catalogo.models import (
    CentroCusto,
    CentroFormulario,
    ExcecaoMaterial,
    Formulario,
    Material,
    ParDePara,
)
from tests.cenario import montar_cenario
from tests.config_cenario import criar_centro, material, usuarios

pytestmark = pytest.mark.django_db

PAGINA = reverse("catalogo:formularios")
CENTROS = reverse("catalogo:formularios_centros")
EXCECAO = reverse("catalogo:formularios_excecao")
FITA = "016.005.010"
BOTINA = "013.006.001"
CAPACETE_OCULTO = "030.004.001"


@pytest.fixture(autouse=True)
def cenario():
    montar_cenario()


@pytest.fixture
def admin(client):
    client.force_login(usuarios()["admin"])
    return client


def texto(resposta):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", resposta.text))


def volta(resposta) -> dict:
    assert resposta.status_code == 302
    url = urlparse(resposta["Location"])
    assert url.path == PAGINA
    return {k: v[0] for k, v in parse_qs(url.query).items()}


# --- A página e o seletor de formulário --------------------------------------------------------


def test_a_pagina_abre_no_primeiro_formulario_e_mostra_as_duas_abas(admin):
    r = admin.get(PAGINA)
    assert r.status_code == 200
    assert "Limpeza, copa e escritório" in r.text
    assert 'id="aba-centros"' in r.text and 'id="aba-materiais"' in r.text
    assert 'id="painel-centros"' in r.text and 'id="painel-materiais"' in r.text


def test_formulario_invalido_volta_ao_primeiro_sem_erro(admin):
    r = admin.get(PAGINA, {"formulario": "AVULSA"})
    assert r.status_code == 200 and "Destinos de Limpeza, copa e escritório" in r.text


@pytest.mark.parametrize("formulario", Formulario.values)
def test_cada_um_dos_cinco_formularios_abre(admin, formulario):
    r = admin.get(PAGINA, {"formulario": formulario})
    assert r.status_code == 200
    assert f"Destinos de {Formulario(formulario).label}" in r.text
    assert f"formulario={formulario}" in r.text  # a URL das abas leva o formulário


def test_a_aba_vem_da_url_e_o_padrao_e_materiais(admin):
    ativa = 'class="aba aba-ativa" id="aba-'
    assert f'{ativa}materiais"' in admin.get(PAGINA).text
    assert f'{ativa}centros"' in admin.get(PAGINA, {"aba": "centros"}).text
    assert f'{ativa}materiais"' in admin.get(PAGINA, {"aba": "nada"}).text


def test_a_pagina_exige_login(client):
    r = client.get(PAGINA)
    assert r.status_code == 302 and "/entrar/" in r["Location"]


def test_o_menu_tem_o_item_formularios(admin):
    r = admin.get(reverse("catalogo:curva"))
    assert f'href="{PAGINA}"' in r.text and "Formulários" in r.text


# --- Aba Centros de custo ----------------------------------------------------------------------


def test_a_aba_de_centros_lista_as_linhas_com_o_estado_em_texto(admin):
    criar_centro("SETOR PARADO", "88", formularios=[Formulario.LIMPEZA], ativo=False)
    criar_centro("SETOR FORA", "89")
    r = admin.get(PAGINA, {"formulario": "LIMPEZA", "aba": "centros"})
    painel = r.text.split('id="painel-centros"')[1].split('id="painel-materiais"')[0]
    assert "ETA I" in painel and "Destino" in painel
    assert "PICKUP 01" in painel and "ABC1D23" in painel
    parado = painel.split("SETOR PARADO")[1].split("</tr>")[0]
    assert "Inativo" in parado and "sem efeito: inativo" in parado
    fora = painel.split("SETOR FORA")[1].split("</tr>")[0]
    assert "Não é destino" in fora and "Habilitar" in fora


def test_o_resumo_conta_as_linhas_do_formulario(admin):
    total = CentroCusto.objects.count()
    r = admin.get(PAGINA, {"formulario": "VIATURAS", "aba": "centros"})
    assert f"0 de {total} linhas são destino deste formulário" in texto(r)
    r = admin.get(PAGINA, {"formulario": "LIMPEZA", "aba": "centros"})
    assert f"{total} de {total} linhas são destino deste formulário" in texto(r)


def test_a_busca_de_centros_filtra_por_descricao_codigo_ou_placa(admin):
    for termo, esperado, ausente in [
        ("eta ii", "ETA II", "ETA I<"),
        ("ABC1D23", "PICKUP 01", "RETRO A"),
        ("41", "RETRO A", "PICKUP 01"),
    ]:
        painel = admin.get(PAGINA, {"formulario": "AB", "aba": "centros", "qc": termo}).text
        painel = painel.split('id="painel-centros"')[1].split('id="painel-materiais"')[0]
        assert esperado in painel and ausente not in painel.split("<tbody>")[1]


def test_nas_viaturas_a_escolha_e_pela_descricao_com_todas_as_linhas_juntas(admin):
    from tests.viaturas_cenario import EQUIPE, montar_viaturas

    montar_viaturas()
    r = admin.get(PAGINA, {"formulario": "VIATURAS", "aba": "centros"})
    painel = r.text.split('id="painel-centros"')[1].split('id="painel-materiais"')[0]
    linha = painel.split(EQUIPE)[1].split("</tr>")[0]
    assert "Destino (1 de 2)" in linha and "Habilitar todas" in linha
    assert painel.count('name="centro"') >= 2  # a descrição envia todas as linhas
    # No modo padrão cada linha tem a sua placa e o seu botão.
    r = admin.get(PAGINA, {"formulario": "AB", "aba": "centros"})
    assert "AAA1A11" in r.text and "BBB2B22" in r.text


def test_habilitar_cria_a_associacao_e_volta_ao_mesmo_estado(admin):
    centro = criar_centro("SETOR NOVO", "90")
    r = admin.post(
        CENTROS,
        {"formulario": "AB", "centro": [centro.pk], "habilitado": "1", "qc": "novo"},
    )
    assert volta(r) == {"formulario": "AB", "aba": "centros", "qc": "novo"}
    assert CentroFormulario.objects.filter(centro=centro, formulario="AB").exists()
    assert not CentroFormulario.objects.filter(centro=centro, formulario="LIMPEZA").exists()
    assert ultima_mensagem(r) == "1 linha habilitada em Ferramentas, peças e materiais."


def test_desabilitar_e_idempotente(admin):
    centro = criar_centro("SETOR NOVO", "90", formularios=[Formulario.AB])
    corpo = {"formulario": "AB", "centro": [centro.pk], "habilitado": "0"}
    admin.post(CENTROS, corpo)
    assert not CentroFormulario.objects.filter(centro=centro).exists()
    r = admin.post(CENTROS, corpo)
    assert ultima_mensagem(r) == "Nada mudou: os centros já estavam assim."


def test_id_inexistente_e_ignorado_e_sem_id_avisa(admin):
    r = admin.post(CENTROS, {"formulario": "AB", "centro": ["999999", "x"], "habilitado": "1"})
    assert ultima_mensagem(r) == "Nada mudou: os centros já estavam assim."
    r = admin.post(CENTROS, {"formulario": "AB", "habilitado": "1"})
    assert ultima_mensagem(r) == "Nenhum centro de custo foi escolhido."


def test_formulario_invalido_na_gravacao_e_400(admin):
    assert (
        admin.post(CENTROS, {"formulario": "AVULSA", "centro": [1], "habilitado": "1"}).status_code
        == 400
    )
    assert admin.post(CENTROS, {"centro": [1], "habilitado": "1"}).status_code == 400


def test_as_gravacoes_so_aceitam_post(admin):
    assert admin.get(CENTROS).status_code == 405
    assert admin.get(EXCECAO).status_code == 405


# --- Aba Materiais -----------------------------------------------------------------------------


def linha_de(corpo: str, codigo: str) -> str:
    """A linha (`<tr>`) da tabela que mostra o material de `codigo`."""
    return next(t for t in corpo.split("<tr>") if f'<span class="mono">{codigo}</span>' in t)


def ultima_mensagem(resposta) -> str:
    return [m.message for m in resposta.wsgi_request._messages][-1]


def linhas_da_aba(resposta) -> str:
    painel = resposta.text.split('id="painel-materiais"')[1]
    return painel.split("<tbody>")[1].split("</tbody>")[0]


def test_a_lista_so_tem_material_visivel_e_mostra_estado_e_origem(admin):
    r = admin.get(PAGINA, {"formulario": "AB", "aba": "materiais"})
    corpo = linhas_da_aba(r)
    assert CAPACETE_OCULTO not in corpo  # oculto no cadastro: só na consulta por material
    linha = linha_de(corpo, FITA)
    assert "Disponível" in linha and "pela regra do formulário" in linha and "Retirar" in linha
    detergente = linha_de(corpo, "023.001.002")
    assert "Não disponível" in detergente and "Acrescentar" in detergente  # da limpeza, fora do AB
    assert "fora da regra do formulário" in detergente


def test_a_linha_mostra_unidade_grupo_e_saldo_so_como_informacao(admin):
    corpo = linhas_da_aba(admin.get(PAGINA, {"formulario": "AB", "aba": "materiais"}))
    linha = linha_de(corpo, "013.005.007")  # LUVA NITRÍLICA, sem saldo
    assert "saldo 0" in texto_do(linha) and "Disponível" in linha  # sem estoque, mas oferecido


def texto_do(trecho: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", trecho))


def test_busca_por_codigo_e_por_nome_sem_acento_e_filtros(admin):
    def achados(**filtros):
        r = admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", **filtros})
        return re.findall(
            r'<span class="mono">(\d{3}\.\d{3}\.\d{3})</span>\s*(?:·|<)', linhas_da_aba(r)
        )

    assert FITA in achados(q="veda rosca") and BOTINA not in achados(q="veda rosca")
    assert achados(q="016.005.010") == [FITA]
    assert "023.004.001" in achados(q="papel higienico")  # sem acento
    assert set(achados(grupo="EPI")) == {BOTINA, "013.005.007"}
    assert achados(grupo="EPI", q="botina") == [BOTINA]
    assert achados(estado="disponivel") and FITA in achados(estado="disponivel")
    assert FITA not in achados(estado="indisponivel") and "023.001.002" in achados(
        estado="indisponivel"
    )
    assert achados(estado="excecao") == []


def test_filtro_com_valor_desconhecido_some_e_a_lista_nao_quebra(admin):
    r = admin.get(
        PAGINA, {"formulario": "AB", "aba": "materiais", "grupo": "NAO EXISTE", "estado": "x"}
    )
    assert r.status_code == 200 and FITA in linhas_da_aba(r)


def test_paginacao_de_50_no_servidor(admin):
    for i in range(120):
        material(f"700.000.{i:03d}", f"ITEM {i:03d}", "MUITOS")
    r = admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", "grupo": "MUITOS"})
    assert linhas_da_aba(r).count("<tr>") == 50
    assert "Página 1 de 3" in texto(r) and "120 materiais no total" in texto(r)
    r = admin.get(
        PAGINA, {"formulario": "AB", "aba": "materiais", "grupo": "MUITOS", "pagina": "3"}
    )
    assert linhas_da_aba(r).count("<tr>") == 20
    fora = admin.get(
        PAGINA, {"formulario": "AB", "aba": "materiais", "grupo": "MUITOS", "pagina": "99"}
    )
    assert "Página 3 de 3" in texto(fora)


def test_a_lista_nao_carrega_o_catalogo_inteiro(admin, django_assert_max_num_queries):
    for i in range(200):
        material(f"700.000.{i:03d}", f"ITEM {i:03d}", "MUITOS")
    with django_assert_max_num_queries(40):
        admin.get(PAGINA, {"formulario": "AB", "aba": "materiais"})


def test_excecao_acrescentar_retirar_e_restaurar(admin):
    corpo = {"formulario": "AB", "q": "veda", "grupo": "", "estado": "", "pagina": "1"}
    r = admin.post(EXCECAO, {**corpo, "codigo": FITA, "acao": "retirar"})
    assert volta(r) == {"formulario": "AB", "aba": "materiais", "q": "veda", "pagina": "1"}
    assert ExcecaoMaterial.objects.get().habilitado is False
    assert ultima_mensagem(r) == (
        f"{FITA} — FITA VEDA ROSCA deixou de ser oferecido em Ferramentas, peças e materiais."
    )
    linha = linhas_da_aba(admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", "q": "veda"}))
    assert "retirado pelo administrador" in linha and "Voltar à regra" in linha
    r = admin.post(EXCECAO, {**corpo, "codigo": FITA, "acao": "restaurar"})
    assert not ExcecaoMaterial.objects.exists()
    assert "voltou à regra" in ultima_mensagem(r)
    novo = material("900.000.001", "TESOURA", "ALMOX")
    admin.post(EXCECAO, {"formulario": "AB", "codigo": novo.codigo, "acao": "acrescentar"})
    assert ExcecaoMaterial.objects.get().habilitado is True
    r = admin.post(EXCECAO, {"formulario": "AB", "codigo": novo.codigo, "acao": "acrescentar"})
    assert "Nada mudou" in ultima_mensagem(r)


def test_acao_invalida_e_400_e_material_inexistente_e_404(admin):
    assert (
        admin.post(EXCECAO, {"formulario": "AB", "codigo": FITA, "acao": "apagar"}).status_code
        == 400
    )
    assert (
        admin.post(EXCECAO, {"formulario": "XX", "codigo": FITA, "acao": "retirar"}).status_code
        == 400
    )
    assert (
        admin.post(
            EXCECAO, {"formulario": "AB", "codigo": "000.000.000", "acao": "retirar"}
        ).status_code
        == 404
    )


def test_a_excecao_vale_so_no_formulario_pedido(admin):
    admin.post(EXCECAO, {"formulario": "AB", "codigo": FITA, "acao": "retirar"})
    assert ExcecaoMaterial.objects.get().formulario == "AB"
    linha = linhas_da_aba(
        admin.get(PAGINA, {"formulario": "VIATURAS", "aba": "materiais", "q": "veda"})
    )
    assert "pela regra do formulário" in linha  # nas viaturas continua


def test_exceção_sem_efeito_e_marcada(admin):
    ExcecaoMaterial.objects.create(
        material=Material.objects.get(codigo=FITA), formulario="AB", habilitado=True
    )
    linha = linhas_da_aba(admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", "q": "veda"}))
    assert "Exceção sem efeito" in linha and "Voltar à regra" in linha


def test_codigo_antigo_de_um_par_de_para_avisa_o_canonico(admin):
    ParDePara.objects.create(antigo="023.004.001", novo=FITA, fator=1)
    linha = linhas_da_aba(admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", "q": "papel"}))
    assert "Código antigo" in linha and FITA in linha


def test_material_duplicado_e_marcado(admin):
    Material.objects.filter(codigo=FITA).update(duplicado=True)
    linha = linhas_da_aba(admin.get(PAGINA, {"formulario": "AB", "aba": "materiais", "q": "veda"}))
    assert "Cadastro duplicado" in linha

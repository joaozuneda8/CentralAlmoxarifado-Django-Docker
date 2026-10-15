from datetime import date
from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from catalogo.consultas_curva import consolidado
from catalogo.curva import periodo
from catalogo.models import (
    ConfiguracaoCurva,
    Material,
    ParametroReposicao,
    ParDePara,
    SaidaSCPI,
)

pytestmark = pytest.mark.django_db


def test_configuracao_atual_cria_a_linha_com_os_padroes_uma_vez_so():
    c = ConfiguracaoCurva.atual()
    assert (c.janela_meses, c.prazo_entrega_dias, c.cobertura_alvo_dias) == (12, 30, 90)
    assert ConfiguracaoCurva.atual().pk == c.pk
    assert ConfiguracaoCurva.objects.count() == 1


def test_configuracao_so_se_inclui_com_a_permissao_e_sem_a_linha(rf):
    modelo_admin = admin.site._registry[ConfiguracaoCurva]
    pedido = rf.get("/")
    pedido.user = get_user_model().objects.create_user(username="1", password="x", is_staff=True)
    assert not modelo_admin.has_add_permission(pedido)
    pedido.user = get_user_model().objects.create_superuser(username="2", password="x")
    assert modelo_admin.has_add_permission(pedido)
    ConfiguracaoCurva.atual()
    assert not modelo_admin.has_add_permission(pedido)


def test_par_com_antigo_repetido_e_recusado_pelo_banco():
    ParDePara.objects.create(antigo="000.000.001", novo="001.001.001")
    with pytest.raises(IntegrityError):
        ParDePara.objects.create(antigo="000.000.001", novo="002.002.002")


def test_parametro_de_reposicao_precisa_de_prazo_ou_cobertura():
    m = Material.objects.create(codigo="001.001.001", nome="X")
    with pytest.raises(ValidationError) as erro:
        ParametroReposicao(material=m).full_clean()
    assert "Preencha o prazo de entrega, a cobertura alvo ou os dois." in str(erro.value)
    ParametroReposicao(material=m, prazo_entrega_dias=45).full_clean()


def saida(id_requi, cadpro, dia, qtd="1", valor="1"):
    SaidaSCPI.objects.create(
        id_requi=id_requi, cadpro=cadpro, data=dia, qtd=Decimal(qtd), valor=Decimal(valor)
    )


def test_consolidado_conserva_os_totais_e_junta_pelo_canonico():
    ParDePara.objects.create(antigo="000.000.001", novo="001.001.001", fator=Decimal("5"))
    saida("1", "000.000.001", date(2026, 2, 1), qtd="2", valor="10")
    saida("2", "001.001.001", date(2026, 3, 1), qtd="3", valor="4")
    saida("3", "003.003.003", date(2026, 3, 1), qtd="1", valor="1.5")
    saida("4", "001.001.001", date(2025, 12, 31), qtd="9", valor="9")  # antes do período
    linhas, rec = consolidado(periodo(date(2026, 10, 12), 12))
    por_codigo = {linha.canonico: linha for linha in linhas}
    assert set(por_codigo) == {"001.001.001", "003.003.003"}
    novo = por_codigo["001.001.001"]
    assert (novo.ocorrencias, novo.qtd, novo.valor) == (2, Decimal("13"), Decimal("14"))
    assert (rec.ocorrencias_antes, rec.ocorrencias_depois) == (3, 3)
    assert rec.valor_antes == rec.valor_depois == Decimal("15.5")
    assert (rec.codigos_antes, rec.canonicos_depois) == (3, 2)

"""Cenário do formulário de EPIs (spec 008), sobre `montar_cenario`.

Grupo de EPIs: "Material de Segurança e EPI" (o cadastro diz `MATERIAL DE SEGURANÇA E EPI`), com
LUVA (UN, saldo 20), CAPACETE (UN, saldo 5) e PROTETOR (UN, sem estoque). Avulso: ÓCULOS (UN,
saldo 8), de outro grupo. Fora da escolha: FITA (do AB) e o resto do cenário. Usuários: um da
Segurança do Trabalho (no grupo), um do almoxarifado (sem grupo) e um administrador (`is_staff`,
sem grupo).
"""

import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from catalogo.models import CentroCusto, Material, MaterialEpi, Opcao
from contas.acesso import GRUPO_SEGURANCA_TRABALHO
from pedidos.protecao import emitir
from tests.cenario import montar_cenario

LUVA = "013.005.100"
CAPACETE = "013.001.001"
PROTETOR = "013.004.001"
OCULOS = "013.003.001"
FITA = "016.005.010"  # do AB, fora da escolha dos EPIs
GRUPO = "MATERIAL DE SEGURANÇA E EPI"
DESTINO = "ETA I"
SENHA = "senha-de-teste-bem-comprida-123"


def montar_epis() -> None:
    montar_cenario()
    referencia = Material.objects.get(codigo=FITA)
    for codigo, nome, grupo, estoque in [
        (LUVA, "LUVA DE VAQUETA", GRUPO, "20"),
        (CAPACETE, "CAPACETE DE SEGURANÇA", GRUPO, "5"),
        (PROTETOR, "PROTETOR AURICULAR", GRUPO, "0"),
        (OCULOS, "ÓCULOS DE PROTEÇÃO", "ALMOXARIFADO", "8"),
    ]:
        Material.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nome": nome,
                "unidade": "UN",
                "grupo": grupo,
                "estoque": Decimal(estoque),
                "estoque_em": referencia.estoque_em,
            },
        )
    Opcao.objects.get_or_create(lista=Opcao.Lista.GRUPO_EPI, valor="Material de Segurança e EPI")
    MaterialEpi.objects.get_or_create(material=Material.objects.get(codigo=OCULOS))
    CentroCusto.objects.get_or_create(descricao="ETA I", codigo="12", defaults={"placa": None})


def usuarios() -> dict:
    """Os três usuários do cenário (idempotente), pelo nome do papel."""
    modelo = get_user_model()
    grupo, _ = Group.objects.get_or_create(name=GRUPO_SEGURANCA_TRABALHO)
    seguranca, _ = modelo.objects.get_or_create(
        username="70001", defaults={"first_name": "Sônia", "last_name": "Segura"}
    )
    seguranca.set_password(SENHA)
    seguranca.save()
    seguranca.groups.add(grupo)
    almox, _ = modelo.objects.get_or_create(username="70002", defaults={"first_name": "Ana"})
    almox.set_password(SENHA)
    almox.save()
    admin, _ = modelo.objects.get_or_create(
        username="70003", defaults={"first_name": "Adão", "is_staff": True, "is_superuser": True}
    )
    admin.set_password(SENHA)
    admin.save()
    return {"seguranca": seguranca, "almox": almox, "admin": admin}


def enviar(client, itens, *, destino=DESTINO, solicitante="Marcos Pereira", token=None):
    """Envia o formulário de EPIs como o navegador (HTMX), com o carrinho dado."""
    return client.post(
        reverse("pedidos:formulario", args=["epis"]),
        {
            "token": (token or emitir(aberto_em=time.time() - 60)).token,
            "solicitante": solicitante,
            "destino": destino,
            "obs": "",
            "confirmacao_extra": "",
            "item_codigo": [c for c, _ in itens],
            "item_qtd": [q for _, q in itens],
        },
        HTTP_HX_REQUEST="true",
    )

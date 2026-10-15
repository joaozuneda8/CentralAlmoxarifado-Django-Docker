import json
import uuid
from decimal import Decimal
from urllib.error import URLError

import pytest
from django.conf import settings as configuracao

from pedidos.models import ItemPedido, Pedido
from pedidos.regras import AB, LIMPEZA
from pedidos.telegram import notificar_pedido, texto_aviso

pytestmark = pytest.mark.django_db


class Resposta200:
    status = 200

    def read(self):
        return b"{}"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def pedido(origem=LIMPEZA, solicitante="Ana", obs="", itens=None):
    p = Pedido.objects.create(
        id=uuid.uuid4(),
        numero="P-000001",
        origem=origem,
        solicitante=solicitante,
        destino="ETA II",
        obs=obs,
    )
    for codigo, nome, qtd in itens or [("023.001.002", "DETERGENTE", Decimal(2))]:
        ItemPedido.objects.create(
            pedido=p, codigo=codigo, material=nome, unidade="UN", qtd_pedida=qtd
        )
    return p


def test_testes_nao_tem_telegram_configurado():
    assert configuracao.TELEGRAM_TOKEN == "" and configuracao.TELEGRAM_CHAT_ID == ""


def test_texto_escapa_html_e_formata_quantidades():
    texto = texto_aviso(
        pedido(
            solicitante="Teste <html> & cia",
            obs="Urgente",
            itens=[("023.001.002", "DETERGENTE", Decimal("1.5"))],
        )
    )
    assert texto.startswith(
        "📦 <b>Pedido P-000001</b> — Limpeza, copa/cozinha e escritório\n"
        "Teste &lt;html&gt; &amp; cia\nDestino: ETA II\n\n"
    )
    assert "• DETERGENTE (023.001.002) — <b>1,5 UN</b>" in texto
    assert texto.endswith("\n\n📝 Urgente")


def test_ab_mostra_quantidade_inteira():
    texto = texto_aviso(pedido(origem=AB, itens=[("016.005.010", "FITA", Decimal("3.000"))]))
    assert "Materiais AB" in texto and "— <b>3 UN</b>" in texto


def test_aviso_corta_em_15_itens():
    itens = [(f"000.000.{n:03d}", f"ITEM {n}", Decimal(1)) for n in range(17)]
    texto = texto_aviso(pedido(itens=itens))
    assert texto.count("• ") == 15
    assert "<i>e mais 2 itens</i>" in texto


def test_sem_configuracao_nao_acessa_a_rede(monkeypatch):
    monkeypatch.setattr("pedidos.telegram.urlopen", lambda *a, **k: pytest.fail("acessou a rede"))
    assert notificar_pedido(pedido()) == "sem_configuracao"


def test_envia_para_a_api(settings, monkeypatch):
    settings.TELEGRAM_TOKEN, settings.TELEGRAM_CHAT_ID = "t", "c"
    pedidos = []

    def falso(req, timeout):
        assert timeout == 10
        pedidos.append(req)
        return Resposta200()

    monkeypatch.setattr("pedidos.telegram.urlopen", falso)
    assert notificar_pedido(pedido(), "https://almox/almoxarifado/") == "enviado"
    corpo = json.loads(pedidos[0].data)
    assert pedidos[0].full_url == "https://api.telegram.org/bott/sendMessage"
    assert (corpo["chat_id"], corpo["parse_mode"]) == ("c", "HTML")
    assert corpo["reply_markup"]["inline_keyboard"][0][0] == {
        "text": "Abrir painel",
        "url": "https://almox/almoxarifado/",
    }


def test_falha_da_rede_vira_falhou_e_vai_para_o_log(settings, monkeypatch, caplog):
    settings.TELEGRAM_TOKEN, settings.TELEGRAM_CHAT_ID = "segredo-do-bot", "c"

    def falha(req, timeout):
        raise URLError("sem rede")

    monkeypatch.setattr("pedidos.telegram.urlopen", falha)
    assert notificar_pedido(pedido()) == "falhou"
    assert "Falha ao avisar no Telegram" in caplog.text
    assert "segredo-do-bot" not in caplog.text

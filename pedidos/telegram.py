"""Aviso no Telegram a cada pedido novo (traduz `Telegram.gs`).

Sem `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`, o aviso não sai e o pedido segue gravado. É chamado
só depois da gravação (`transaction.on_commit`): falha aqui nunca desfaz o pedido. A URL da
API contém o token e por isso nunca vai para o log.
"""

import json
import logging
from html import escape
from urllib.request import Request, urlopen

from django.conf import settings

from pedidos.models import ItemPedido
from pedidos.regras import AB, LIMPEZA, qtd_br

logger = logging.getLogger("pedidos")

MAX_ITENS_AVISO = 15
FORMULARIOS = {LIMPEZA: "Limpeza, copa/cozinha e escritório", AB: "Materiais AB"}


def _esc(valor) -> str:
    return escape("" if valor is None else str(valor), quote=False)


def _quantidade(qtd) -> str:
    """A quantidade exata, em pt-BR e sem zeros à direita, em qualquer origem."""
    return qtd_br(qtd)


def texto_aviso(pedido) -> str:
    # Só o que o funcionário pediu (o aviso sai antes do atendimento; o filtro é por segurança).
    itens = list(pedido.itens.filter(origem=ItemPedido.Origem.PEDIDO))
    linhas = []
    for i in itens[:MAX_ITENS_AVISO]:
        unidade = f" {_esc(i.unidade)}" if i.unidade else ""
        linhas.append(
            f"• {_esc(i.material)} ({_esc(i.codigo)}) — <b>{_quantidade(i.qtd_pedida)}{unidade}</b>"
        )
    if len(itens) > MAX_ITENS_AVISO:
        linhas.append(f"<i>e mais {len(itens) - MAX_ITENS_AVISO} itens</i>")
    texto = (
        f"📦 <b>Pedido {_esc(pedido.numero)}</b> — {FORMULARIOS.get(pedido.origem, '')}\n"
        f"{_esc(pedido.solicitante)}\nDestino: {_esc(pedido.destino)}\n\n" + "\n".join(linhas)
    )
    if pedido.obs:
        texto += f"\n\n📝 {_esc(pedido.obs)}"
    return texto


def notificar_pedido(pedido, url_painel: str = "") -> str:
    """Envia o aviso. Devolve "enviado", "falhou" ou "sem_configuracao"; nunca lança."""
    token = settings.TELEGRAM_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return "sem_configuracao"
    corpo = {"chat_id": chat_id, "text": texto_aviso(pedido), "parse_mode": "HTML"}
    if url_painel:
        corpo["reply_markup"] = {"inline_keyboard": [[{"text": "Abrir painel", "url": url_painel}]]}
    requisicao = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(requisicao, timeout=10) as resposta:
            if resposta.status != 200:
                raise RuntimeError(f"Telegram respondeu {resposta.status}")
    except Exception as exc:
        logger.warning("Falha ao avisar no Telegram: %s", exc)
        return "falhou"
    return "enviado"

"""Proteção dos formulários públicos contra envio automático (spec, fluxo 1).

A página leva um token assinado com o identificador do envio e o momento em que abriu: o
identificador vira o `Pedido.id` (nunca escolhido pelo navegador) e o momento barra o envio
feito em menos de `PEDIDOS_TEMPO_MINIMO` segundos. Um campo isca, invisível para pessoas,
recusa robôs que preenchem tudo.
"""

import time
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core import signing

SALT = "pedidos.envio"
CAMPO_ISCA = "confirmacao_extra"
MENSAGEM_RECUSA = "Não foi possível registrar o pedido. Procure o almoxarifado."
MENSAGEM_EXPIRADO = (
    "O formulário expirou ou foi alterado. Abra o formulário de novo para enviar o pedido."
)


@dataclass(frozen=True)
class Envio:
    id: uuid.UUID
    aberto_em: float
    token: str


def emitir(envio_id: uuid.UUID | None = None, aberto_em: float | None = None) -> Envio:
    envio_id = envio_id or uuid.uuid4()
    aberto_em = time.time() if aberto_em is None else aberto_em
    token = signing.dumps({"id": str(envio_id), "aberto_em": aberto_em}, salt=SALT)
    return Envio(envio_id, aberto_em, token)


def ler(token: str) -> Envio | None:
    """O envio do token, ou None se a assinatura ou o conteúdo não valem."""
    try:
        dados = signing.loads(token or "", salt=SALT)
        return Envio(uuid.UUID(dados["id"]), float(dados["aberto_em"]), token)
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return None


def recusar(envio: Envio, isca: str, agora: float | None = None) -> bool:
    """Campo isca preenchido ou envio rápido demais depois de abrir a página."""
    agora = time.time() if agora is None else agora
    return bool((isca or "").strip()) or agora - envio.aberto_em < settings.PEDIDOS_TEMPO_MINIMO

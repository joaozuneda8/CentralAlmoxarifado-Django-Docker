"""Gravação da carga das planilhas do Apps Script no banco (migração única, subprojeto 5).

`gravar` recebe a `Carga` de `conversao.converter` e a salva numa transação só: ou entra tudo
ou nada. A importação substitui os dados vindos da planilha, por isso recusa o que poderia
apagar trabalho feito no Django.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from catalogo.models import CentroCusto, ItemLimpeza, Material, Opcao
from implantacao.conversao import Carga
from pedidos import regras
from pedidos.models import Atendimento, ItemPedido, LinhaSaida, Pedido
from pedidos.servicos import travar_sequencia

# Usuário (inativo, sem senha) a quem se atribui o que a planilha não diz quem fez.
USUARIO_PLANILHA = "planilha"

_MAX_NUMEROS_NA_RECUSA = 10
_LOTE = 500


class MigracaoRecusada(Exception):
    """Uma trava impediu a importação; nada foi alterado."""


def _conferir_travas(carga: Carga) -> None:
    if settings.LANCAMENTO_REAL:
        raise MigracaoRecusada(
            "O lançamento real já foi liberado (LANCAMENTO_REAL=1): depois da virada, a "
            "importação das planilhas substituiria dados do sistema."
        )
    ids = [pedido.id for pedido in carga.pedidos]
    fora = Pedido.objects.exclude(id__in=ids).order_by("numero")
    if fora.exists():
        numeros = list(fora.values_list("numero", flat=True)[:_MAX_NUMEROS_NA_RECUSA])
        raise MigracaoRecusada(
            f"O banco tem pedidos que não estão na planilha: {', '.join(numeros)}. "
            "A importação substituiria esses pedidos; apague-os pelo shell se forem de teste "
            "(deploy/VIRADA.md, seção 5)."
        )
    feitos = Atendimento.objects.exclude(atendido_por__username=USUARIO_PLANILHA).order_by(
        "pedido__numero"
    )
    if feitos.exists():
        numeros = list(feitos.values_list("pedido__numero", flat=True)[:_MAX_NUMEROS_NA_RECUSA])
        raise MigracaoRecusada(
            f"O banco tem atendimentos feitos no Django: {', '.join(numeros)}. "
            "A importação os apagaria; desfaça-os antes (veja deploy/VIRADA.md)."
        )
    if carga.itens_limpeza and not Material.objects.exists():
        raise MigracaoRecusada(
            "Nenhum material cadastrado: carregue o cadastro do SCPI antes (importar_cadastro)."
        )


def _usuario_planilha():
    modelo = get_user_model()
    usuario = modelo.objects.filter(username=USUARIO_PLANILHA).first()
    if usuario is None:
        usuario = modelo(username=USUARIO_PLANILHA, is_active=False)
        usuario.set_unusable_password()
        usuario.save()
    return usuario


def _itens_de_limpeza(carga: Carga, avisos: list[str]) -> list[ItemLimpeza]:
    codigos = [codigo for codigo, *_ in carga.itens_limpeza]
    materiais = {regras.norm_u(m.codigo): m for m in Material.objects.filter(codigo__in=codigos)}
    itens = []
    for codigo, categoria, nome, unidade, ordem in carga.itens_limpeza:
        material = materiais.get(regras.norm_u(codigo))
        if material is None:
            avisos.append(
                f"Lista_Limpeza: código {codigo} não está no cadastro do SCPI; item ignorado."
            )
            continue
        itens.append(
            ItemLimpeza(
                material=material,
                categoria=categoria,
                nome_exibido=nome,
                unidade_exibida=unidade,
                ordem=ordem,
            )
        )
    return itens


def gravar(carga: Carga) -> list[str]:
    """Substitui pedidos, centros de custo, opções e itens de limpeza pela carga.

    Devolve os avisos da gravação. Levanta `MigracaoRecusada` (sem alterar nada) se uma
    trava impedir."""
    avisos: list[str] = []
    with transaction.atomic():
        sequencia = (
            travar_sequencia()
        )  # serializa com quem registra pedidos: fecha a janela até o delete
        _conferir_travas(carga)
        Pedido.objects.all().delete()  # em cascata: itens, atendimentos e linhas de saída
        ItemLimpeza.objects.all().delete()
        CentroCusto.objects.all().delete()
        Opcao.objects.all().delete()

        usuario = _usuario_planilha()
        for atendimento in carga.atendimentos:
            atendimento.atendido_por = usuario
        for pedido in carga.pedidos:
            if pedido.origem == regras.AVULSA:
                pedido.registrado_por = usuario

        Pedido.objects.bulk_create(carga.pedidos, batch_size=_LOTE)
        ItemPedido.objects.bulk_create(carga.itens, batch_size=_LOTE)
        Atendimento.objects.bulk_create(carga.atendimentos, batch_size=_LOTE)
        LinhaSaida.objects.bulk_create(carga.linhas, batch_size=_LOTE)
        CentroCusto.objects.bulk_create(carga.centros, batch_size=_LOTE)
        Opcao.objects.bulk_create(carga.opcoes, batch_size=_LOTE)
        ItemLimpeza.objects.bulk_create(_itens_de_limpeza(carga, avisos), batch_size=_LOTE)

        sequencia.ultimo = max(sequencia.ultimo, carga.ultimo_numero)
        sequencia.save(update_fields=["ultimo"])
    return avisos

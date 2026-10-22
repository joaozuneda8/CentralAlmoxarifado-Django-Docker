"""Consultas do painel: filtros em SQL, para o painel não carregar todos os pedidos.

Os filtros de situação repetem `regras.situacao_pedido` e `regras.situacao_scpi` como
anotações `Exists`; `tests/test_painel.py` confere que os dois concordam em todas as
combinações.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django import forms
from django.db.models import Count, Exists, F, Min, OuterRef, Q, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalogo.models import Material
from pedidos.models import ItemPedido, LinhaSaida, Pedido
from pedidos.regras import (
    AVULSA,
    EM_LANCAMENTO,
    ERRO,
    LANCADA,
    NAO_LANCAR,
    PENDENTE,
    VERIFICAR,
)
from scpi.requisicoes import ESTADOS_TRAVA

OPCOES_SITUACAO = [
    ("aguardando", "Aguardando atendimento"),
    ("atendido", "Atendido"),
    ("parcial", "Atendido parcialmente"),
]
OPCOES_SCPI = [
    ("sem", "Aguarda o atendimento ou não será lançado"),
    ("aguardando", "Aguardando o robô"),
    ("lancado", "Lançado"),
    ("parcial", "Parcialmente lançado"),
    ("atencao", "Verificar / erro"),
]


class FiltrosPainel(forms.Form):
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.TextInput(
            attrs={
                "class": "campo-entrada",
                "type": "search",
                "placeholder": "Nº, solicitante, recebedor ou ocorrência",
            }
        ),
    )
    origem = forms.ChoiceField(
        required=False,
        label="Origem",
        choices=[("", "Todas")] + Pedido.Origem.choices,
        widget=forms.Select(attrs={"class": "campo-entrada"}),
    )
    situacao = forms.ChoiceField(
        required=False,
        label="Situação do pedido",
        choices=[("", "Todas")] + OPCOES_SITUACAO,
        widget=forms.Select(attrs={"class": "campo-entrada"}),
    )
    scpi = forms.ChoiceField(
        required=False,
        label="Integração SCPI",
        choices=[("", "Todas")] + OPCOES_SCPI,
        widget=forms.Select(attrs={"class": "campo-entrada"}),
    )
    recibo = forms.ChoiceField(
        required=False,
        label="Recibo",
        choices=[("", "Todos"), ("pendente", "Não impresso"), ("impresso", "Impresso")],
        widget=forms.Select(attrs={"class": "campo-entrada"}),
    )
    de = forms.DateField(
        required=False,
        label="De",
        widget=forms.DateInput(attrs={"type": "date", "class": "campo-entrada"}),
    )
    ate = forms.DateField(
        required=False,
        label="Até",
        widget=forms.DateInput(attrs={"type": "date", "class": "campo-entrada"}),
    )

    def filtros(self) -> dict:
        """Os valores válidos; o que não validou é ignorado."""
        self.is_valid()
        return {k: v for k, v in getattr(self, "cleaned_data", {}).items() if v}


def filtrar_situacao(qs: QuerySet, chave: str) -> QuerySet:
    entregue_a_menos = Exists(
        ItemPedido.objects.filter(pedido=OuterRef("pk"), origem=ItemPedido.Origem.PEDIDO)
        .filter(qtd_pedida__gt=Coalesce(F("qtd_entregue"), 0))
        .exclude(Exists(ItemPedido.objects.filter(no_lugar_de=OuterRef("pk"), qtd_entregue__gt=0)))
    )
    nao_avulsa = qs.exclude(origem=AVULSA)
    if chave == "aguardando":
        return nao_avulsa.filter(atendimento__isnull=True)
    if chave == "parcial":
        return nao_avulsa.filter(atendimento__isnull=False).filter(entregue_a_menos)
    if chave == "atendido":
        # A saída avulsa já nasce atendida.
        atendidos = nao_avulsa.filter(atendimento__isnull=False).exclude(entregue_a_menos)
        return qs.filter(Q(origem=AVULSA) | Q(pk__in=atendidos.values("pk")))
    return qs


def filtrar_scpi(qs: QuerySet, chave: str) -> QuerySet:
    ativas = LinhaSaida.objects.filter(atendimento__pedido=OuterRef("pk")).exclude(
        status=NAO_LANCAR
    )
    sem_req = Q(requisicao_scpi="")
    ativa = Exists(ativas)
    lancada = Exists(ativas.filter(~sem_req | Q(status=LANCADA)))
    atencao = Exists(ativas.filter(sem_req, status__in=[VERIFICAR, EM_LANCAMENTO, ERRO]))
    pendente = Exists(ativas.filter(sem_req, status=PENDENTE))
    if chave == "sem":
        return qs.exclude(ativa)
    if chave == "atencao":
        return qs.filter(atencao)
    if chave == "lancado":
        return qs.filter(ativa).exclude(atencao).exclude(pendente)
    if chave == "parcial":
        return qs.filter(lancada, pendente).exclude(atencao)
    if chave == "aguardando":
        return qs.filter(pendente).exclude(lancada).exclude(atencao)
    return qs


def inicio_do_dia(dia: date) -> datetime:
    """Começo do dia `dia` no fuso local (limite dos filtros de período)."""
    return timezone.make_aware(datetime.combine(dia, time.min))


def pedidos_do_painel(filtros: dict) -> QuerySet:
    qs = (
        Pedido.objects.select_related("atendimento")
        .prefetch_related("itens", "atendimento__linhas")
        .order_by("-criado_em", "-numero")
    )
    if q := (filtros.get("q") or "").strip():
        qs = qs.filter(
            Q(numero__icontains=q)
            | Q(solicitante__icontains=q)
            | Q(atendimento__recebedor__icontains=q)
            | Q(ocorrencia__icontains=q)
        )
    if origem := filtros.get("origem"):
        qs = qs.filter(origem=origem)
    if de := filtros.get("de"):
        qs = qs.filter(criado_em__gte=inicio_do_dia(de))
    if (ate := filtros.get("ate")) and ate < date.max:  # 31/12/9999 não limita nada
        qs = qs.filter(criado_em__lt=inicio_do_dia(ate + timedelta(days=1)))
    if situacao := filtros.get("situacao"):
        qs = filtrar_situacao(qs, situacao)
    if scpi := filtros.get("scpi"):
        qs = filtrar_scpi(qs, scpi)
    if recibo := filtros.get("recibo"):
        # Só tem recibo o que tem saída registrada (atendimento).
        qs = qs.filter(
            atendimento__isnull=False, atendimento__recibo_impresso_em__isnull=recibo == "pendente"
        )
    return qs


@dataclass
class RequisicaoNaFila:
    lote: str  # número do pedido ou da saída avulsa
    data: date
    recebedor: str
    centro_custo: str
    materiais: int  # linhas `PENDENTE` do lote


@dataclass
class Fila:
    total: int
    requisicoes: list[RequisicaoNaFila]

    @property
    def fora(self) -> int:
        """Quantas ficaram fora da lista mostrada."""
        return self.total - len(self.requisicoes)


def fila_do_robo(limite: int = 20) -> Fila:
    """As requisições que o robô lançaria agora, na ordem em que as percorre, até `limite`.

    Repete `requisicoes.agrupar` em SQL (lote com linha `PENDENTE` e sem nenhuma linha em
    `ESTADOS_TRAVA` nem `PENDENTE` com número de requisição), para não carregar todas as linhas
    pendentes a cada recarga da página; `tests/test_consultas_fila.py` confere que concordam."""
    trava = LinhaSaida.objects.filter(lote=OuterRef("lote")).filter(
        # "Com número" é com algum caractere que não seja espaço, como o `texto()` da regra.
        Q(status__in=ESTADOS_TRAVA) | Q(status=PENDENTE, requisicao_scpi__regex=r"[^[:space:]]")
    )
    lotes = (
        LinhaSaida.objects.filter(status=PENDENTE)
        .exclude(Exists(trava))
        .values("lote")
        .annotate(primeira=Min("id"), materiais=Count("id"))
        .order_by("primeira")
    )
    total = lotes.count()
    if not total or limite <= 0:
        return Fila(total, [])
    escolhidos = list(lotes[:limite])
    primeiras = LinhaSaida.objects.in_bulk([lote["primeira"] for lote in escolhidos])
    return Fila(
        total,
        [
            RequisicaoNaFila(
                lote=lote["lote"],
                data=primeiras[lote["primeira"]].data,
                recebedor=primeiras[lote["primeira"]].recebedor,
                centro_custo=primeiras[lote["primeira"]].centro_custo,
                materiais=lote["materiais"],
            )
            for lote in escolhidos
        ],
    )


def lotes_pendentes() -> int:
    """Lotes que o robô lançaria agora, pela regra de `requisicoes.agrupar`."""
    return fila_do_robo(limite=0).total


@dataclass
class LoteTravado:
    lote: str
    linhas: list[LinhaSaida]
    conferir: bool  # alguma linha `VERIFICAR` ou `EM_LANCAMENTO`: o SCPI pode ter gravado


def lotes_travados() -> list[LoteTravado]:
    """Linhas em `VERIFICAR`, `EM_LANCAMENTO` ou `ERRO`, agrupadas por lote (na ordem do `id`
    da primeira linha de cada um)."""
    linhas = LinhaSaida.objects.filter(status__in=[VERIFICAR, EM_LANCAMENTO, ERRO]).order_by("id")
    lotes: dict[str, LoteTravado] = {}
    for linha in linhas:
        lote = lotes.setdefault(linha.lote, LoteTravado(linha.lote, [], False))
        lote.linhas.append(linha)
        lote.conferir = lote.conferir or linha.status in (VERIFICAR, EM_LANCAMENTO)
    return list(lotes.values())


def unidades_scpi(pedidos) -> dict[str, str]:
    """Unidade do cadastro do SCPI de cada código dos pedidos, numa consulta. A área interna mostra
    a unidade como está no SCPI; a do item (`ItemPedido.unidade`) é a do formulário, que na limpeza
    pode ser a unidade exibida ("EMBALAGEM 500 g"), e só vale quando o código saiu do cadastro."""
    codigos = {i.codigo for p in pedidos for i in p.itens.all()}
    return dict(
        Material.objects.filter(codigo__in=codigos)
        .exclude(unidade="")
        .values_list("codigo", "unidade")
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from catalogo.consultas_curva import dados_da_curva
from catalogo.curva import INICIO_DADOS_CONFIAVEIS, periodo
from catalogo.models import ConfiguracaoCurva

ABAS_CURVA = [
    ("frequencia", "Frequência"),
    ("valor", "Valor"),
    ("reposicao", "Reposição"),
    ("pendentes", "Pendentes"),
]


def hoje():
    return timezone.localdate()


def _meses(request, padrao: int) -> int:
    """Janela pedida em `?meses=N` (inteiro ≥ 1); inválida volta ao padrão, com aviso."""
    bruto = request.GET.get("meses", "").strip()
    if not bruto:
        return padrao
    try:
        meses = int(bruto)
        if meses < 1:
            raise ValueError
    except ValueError:
        messages.warning(request, f"Janela inválida; usando a padrão de {padrao} meses.")
        return padrao
    return meses


@login_required
def curva(request):
    """Curva ABC consolidada pelo de/para: abas por frequência, por valor, reposição e
    pendentes."""
    configuracao = ConfiguracaoCurva.atual()
    meses = _meses(request, configuracao.janela_meses)
    aba = request.GET.get("aba")
    chaves = [chave for chave, _ in ABAS_CURVA]
    return render(
        request,
        "catalogo/curva.html",
        {
            "dados": dados_da_curva(periodo(hoje(), meses)),
            "meses": meses,
            "inicio_confiavel": INICIO_DADOS_CONFIAVEIS,
            "aba": aba if aba in chaves else "frequencia",
            "abas": ABAS_CURVA,
        },
    )

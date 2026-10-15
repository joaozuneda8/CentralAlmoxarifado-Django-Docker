"""Curva ABC e reposição sobre as saídas consolidadas pelo código canônico.

Traduz as abas `ABC_FREQ_CONSOL`, `ABC_VALOR_CONSOL` e as colunas de reposição da planilha
MAPEAMENTO DE/PARA CONSOLIDADO, com as divergências registradas na spec
(`specs/001-depara-curva-abc/spec.md`). Funções puras, sem ORM.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from catalogo.depara import LinhaConsolidada, LinhaSaidas, Par
from pedidos.regras import norm_u

# Os dados de saídas anteriores a esta data não são confiáveis e nunca entram nos cálculos.
INICIO_DADOS_CONFIAVEIS = date(2026, 1, 1)


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fim: date
    dias: int  # contados de forma inclusiva
    limitado: bool  # o início foi puxado para INICIO_DADOS_CONFIAVEIS


def _meses_antes(dia: date, meses: int) -> date:
    total = dia.year * 12 + dia.month - 1 - meses
    ano, mes = divmod(total, 12)
    mes += 1
    if ano < 1:  # antes do que o `date` representa; o recorte em `periodo` o descarta
        return date.min
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def periodo(hoje: date, meses: int) -> Periodo:
    """Janela móvel de `meses` até `hoje`, que nunca começa antes de INICIO_DADOS_CONFIAVEIS."""
    if meses < 1:
        raise ValueError("A janela precisa ter pelo menos um mês.")
    pedido = _meses_antes(hoje, meses)
    inicio = max(pedido, INICIO_DADOS_CONFIAVEIS)
    return Periodo(inicio, hoje, (hoje - inicio).days + 1, pedido < INICIO_DADOS_CONFIAVEIS)


# Cortes das classes pelo percentual acumulado, como `IF(G<=0.78,"A",IF(G<=0.95,"B","C"))`.
CORTE_A = Decimal("0.78")
CORTE_B = Decimal("0.95")
CHAVES = ("ocorrencias", "valor")


@dataclass(frozen=True)
class LinhaCurva:
    posicao: int
    canonico: str
    descricao: str
    unidade: str
    ocorrencias: int
    qtd: Decimal
    valor: Decimal
    percentual: Decimal  # fração: 0,0394 é 3,94%
    acumulado: Decimal
    classe: str


@dataclass(frozen=True)
class Pendente:
    codigo: str
    descricao: str
    motivo: str  # "sem cadastro" ou "oculto no cadastro"
    ocorrencias: int
    valor: Decimal


def classe(acumulado: Decimal) -> str:
    if acumulado <= CORTE_A:
        return "A"
    if acumulado <= CORTE_B:
        return "B"
    return "C"


def curva(
    linhas: Iterable[LinhaConsolidada], chave: str, descricoes: dict[str, tuple[str, str]]
) -> list[LinhaCurva]:
    """Curva ABC por ocorrências ou por valor. Ordem decrescente pela chave e, no empate, pelo
    código; `descricoes` leva o código normalizado a (nome, unidade). Total zero: lista vazia."""
    if chave not in CHAVES:
        raise ValueError(f"Chave da curva desconhecida: {chave}")

    def medida(linha: LinhaConsolidada) -> Decimal:
        return Decimal(linha.ocorrencias) if chave == "ocorrencias" else linha.valor

    linhas = list(linhas)
    total = sum((medida(linha) for linha in linhas), Decimal(0))
    if total <= 0:
        return []
    resultado = []
    soma = Decimal(0)
    ordem = sorted(linhas, key=lambda linha: (-medida(linha), norm_u(linha.canonico)))
    for posicao, linha in enumerate(ordem, start=1):
        soma += medida(linha)
        acumulado = soma / total
        nome, unidade = descricoes.get(norm_u(linha.canonico), ("", ""))
        resultado.append(
            LinhaCurva(
                posicao=posicao,
                canonico=linha.canonico,
                descricao=nome,
                unidade=unidade,
                ocorrencias=linha.ocorrencias,
                qtd=linha.qtd,
                valor=linha.valor,
                percentual=medida(linha) / total,
                acumulado=acumulado,
                classe=classe(acumulado),
            )
        )
    return resultado


def pendentes(
    brutas: Iterable[LinhaSaidas], pares: Iterable[Par], materiais: dict[str, tuple[str, bool]]
) -> list[Pendente]:
    """Códigos com saída que não são antigo nem destino de nenhum par e cujo material está oculto
    ou fora do cadastro (sinal de código antigo ainda sem par). `materiais` leva o código
    normalizado a (nome, oculto). Do maior valor para o menor."""
    pares = list(pares)
    com_par = {norm_u(p.antigo) for p in pares} | {norm_u(p.novo) for p in pares}
    resultado = []
    for linha in brutas:
        chave = norm_u(linha.codigo)
        if chave in com_par:
            continue
        material = materiais.get(chave)
        if material is None:
            motivo, nome = "sem cadastro", ""
        elif material[1]:
            motivo, nome = "oculto no cadastro", material[0]
        else:
            continue
        resultado.append(Pendente(linha.codigo, nome, motivo, linha.ocorrencias, linha.valor))
    return sorted(resultado, key=lambda p: (-p.valor, norm_u(p.codigo)))


ESGOTADO = "esgotado"
COMPRAR = "comprar"
EM_ESTOQUE = "em estoque"
UM = Decimal(1)


@dataclass(frozen=True)
class Reposicao:
    consumo_diario: Decimal
    estoque_seguranca: int
    ponto_pedido: int
    quanto_pedir: int
    cobertura_dias: Decimal | None  # None: sem consumo no período
    situacao: str


def _arredonda(valor: Decimal) -> int:
    """Como o ROUND da planilha: meio para cima."""
    return int(valor.quantize(UM, rounding=ROUND_HALF_UP))


def reposicao(
    consumo: Decimal, estoque: Decimal, prazo: int, cobertura: int, dias: int
) -> Reposicao:
    """Reposição de um material pelas fórmulas da aba de mapeamento (spec, FR-019 e FR-020):
    estoque de segurança = arredonda(consumo diário × prazo); ponto de pedido =
    arredonda(consumo diário × prazo + estoque de segurança); quanto pedir = teto(consumo diário ×
    cobertura + estoque de segurança). `consumo` já vem convertido pelo fator do de/para."""
    diario = consumo / dias
    seguranca = _arredonda(diario * prazo)
    ponto = _arredonda(diario * prazo + seguranca)
    pedir = int((diario * cobertura + seguranca).quantize(UM, rounding=ROUND_CEILING))
    cobertura_dias = (estoque / diario).quantize(Decimal("0.01")) if diario > 0 else None
    if estoque <= 0:
        situacao = ESGOTADO
    elif estoque <= ponto:
        situacao = COMPRAR
    else:
        situacao = EM_ESTOQUE
    return Reposicao(diario, seguranca, ponto, pedir, cobertura_dias, situacao)

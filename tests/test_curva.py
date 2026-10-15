from datetime import date
from decimal import Decimal

import pytest

from catalogo.curva import (
    COMPRAR,
    EM_ESTOQUE,
    ESGOTADO,
    INICIO_DADOS_CONFIAVEIS,
    Pendente,
    Periodo,
    classe,
    curva,
    pendentes,
    periodo,
    reposicao,
)
from catalogo.depara import (
    LinhaConsolidada,
    LinhaSaidas,
    Par,
    consolidar,
    resolver_canonicos,
)

# ---------------------------------------------------------------- periodo (puro)


def test_dados_confiaveis_comecam_em_2026():
    assert INICIO_DADOS_CONFIAVEIS == date(2026, 1, 1)


def test_janela_limitada_ao_inicio_dos_dados_confiaveis():
    assert periodo(date(2026, 10, 12), 12) == Periodo(
        inicio=date(2026, 1, 1), fim=date(2026, 10, 12), dias=285, limitado=True
    )


def test_janela_inteira_depois_do_inicio():
    assert periodo(date(2027, 10, 12), 12) == Periodo(
        inicio=date(2026, 10, 12), fim=date(2027, 10, 12), dias=366, limitado=False
    )


def test_janela_maior_que_12_meses():
    p = periodo(date(2028, 3, 31), 18)
    assert (p.inicio, p.limitado) == (date(2026, 9, 30), False)


def test_fim_de_mes_sem_o_dia_vira_o_ultimo_dia_do_mes():
    assert periodo(date(2027, 3, 31), 1).inicio == date(2027, 2, 28)


def test_primeiro_dia_conta_um_dia():
    assert periodo(date(2026, 1, 1), 12).dias == 1


def test_janela_maior_que_o_calendario_comeca_nos_dados_confiaveis():
    # Antes do recorte, 100000 meses dariam um ano antes do 1, que o `date` não representa.
    p = periodo(date(2026, 10, 12), 100_000)
    assert (p.inicio, p.limitado) == (INICIO_DADOS_CONFIAVEIS, True)


@pytest.mark.parametrize("meses", [0, -1])
def test_janela_precisa_de_pelo_menos_um_mes(meses):
    with pytest.raises(ValueError):
        periodo(date(2026, 10, 12), meses)


# ---------------------------------------------------------------- curva e pendentes (puro)


def consolidada(codigo, ocorrencias, valor="0", qtd="1"):
    return LinhaConsolidada(codigo, ocorrencias, Decimal(qtd), Decimal(valor))


@pytest.mark.parametrize(
    ("acumulado", "esperada"),
    [("0.5", "A"), ("0.78", "A"), ("0.7801", "B"), ("0.95", "B"), ("0.9501", "C"), ("1", "C")],
)
def test_classe_pelos_cortes_da_planilha(acumulado, esperada):
    assert classe(Decimal(acumulado)) == esperada


def test_curva_por_ocorrencias():
    linhas = [consolidada("B", 20), consolidada("A", 78), consolidada("C", 2)]
    resultado = curva(linhas, "ocorrencias", {"A": ("ALFA", "UN")})
    assert [(r.posicao, r.canonico, r.classe) for r in resultado] == [
        (1, "A", "A"),
        (2, "B", "C"),
        (3, "C", "C"),
    ]
    a = resultado[0]
    assert (a.descricao, a.unidade, a.percentual, a.acumulado) == (
        "ALFA",
        "UN",
        Decimal("0.78"),
        Decimal("0.78"),
    )
    assert resultado[1].acumulado == Decimal("0.98")
    assert resultado[2].descricao == ""


def test_curva_por_valor_e_desempate_pelo_codigo():
    linhas = [consolidada("B", 1, "10"), consolidada("A", 9, "10"), consolidada("C", 5, "80")]
    assert [r.canonico for r in curva(linhas, "valor", {})] == ["C", "A", "B"]


def test_curva_com_total_zero_fica_vazia():
    assert curva([consolidada("A", 3, "0")], "valor", {}) == []
    assert curva([], "ocorrencias", {}) == []


def test_pendentes_so_codigo_sem_par_oculto_ou_sem_cadastro():
    brutas = [
        LinhaSaidas("000.000.001", 2, Decimal("1"), Decimal("5")),  # oculto, sem par: pendente
        LinhaSaidas("003.000.025", 1, Decimal("1"), Decimal("50")),  # sem cadastro: pendente
        LinhaSaidas("000.000.002", 4, Decimal("1"), Decimal("1")),  # oculto, com par: não
        LinhaSaidas("001.001.001", 9, Decimal("1"), Decimal("1")),  # visível: não
        LinhaSaidas("002.002.002", 1, Decimal("1"), Decimal("1")),  # destino oculto: não
    ]
    pares = [Par("000.000.002", "001.001.001"), Par("000.000.009", "002.002.002")]
    materiais = {
        "000.000.001": ("VELHO", True),
        "000.000.002": ("VELHO 2", True),
        "001.001.001": ("NOVO", False),
        "002.002.002": ("OUTRO", True),
    }
    assert pendentes(brutas, pares, materiais) == [
        Pendente("003.000.025", "", "sem cadastro", 1, Decimal("50")),
        Pendente("000.000.001", "VELHO", "oculto no cadastro", 2, Decimal("5")),
    ]


# ---------------------------------------------------------------- reposição (puro)


def repor(consumo, estoque, prazo=30, cobertura=90, dias=300):
    return reposicao(Decimal(consumo), Decimal(estoque), prazo, cobertura, dias)


def test_reposicao_do_cenario_da_spec():
    r = repor("600", "100")
    assert r.consumo_diario == Decimal("2")
    assert (r.estoque_seguranca, r.ponto_pedido, r.quanto_pedir) == (60, 120, 240)
    assert r.cobertura_dias == Decimal("50.00")
    assert r.situacao == COMPRAR


def test_prazo_proprio_muda_estoque_de_seguranca_e_ponto_de_pedido():
    r = repor("600", "100", prazo=45)
    assert (r.estoque_seguranca, r.ponto_pedido) == (90, 180)


def test_saldo_zero_esta_esgotado():
    assert repor("600", "0").situacao == ESGOTADO
    assert repor("600", "-1").situacao == ESGOTADO


def test_acima_do_ponto_de_pedido_esta_em_estoque():
    assert repor("600", "121").situacao == EM_ESTOQUE
    assert repor("600", "120").situacao == COMPRAR


def test_arredonda_meio_para_cima_e_quanto_pedir_para_cima():
    # 1,5 por dia, prazo 1, cobertura 1: ES = arredonda(1,5) = 2; PP = arredonda(3,5) = 4;
    # quanto pedir = teto(1,5 + 2) = 4.
    r = repor("3", "10", prazo=1, cobertura=1, dias=2)
    assert (r.estoque_seguranca, r.ponto_pedido, r.quanto_pedir) == (2, 4, 4)


def test_sem_consumo_nao_tem_cobertura():
    r = repor("0", "10")
    assert r.cobertura_dias is None
    assert (r.estoque_seguranca, r.ponto_pedido, r.quanto_pedir) == (0, 0, 0)
    assert r.situacao == EM_ESTOQUE


def test_fator_converte_o_consumo_do_codigo_antigo():
    # Frasco de 5 L (antigo) virou item de 1 L (novo): cada saída no antigo conta como 5.
    canonicos = resolver_canonicos([Par("000.000.001", "001.001.001", Decimal("5"))])
    (linha,) = consolidar(
        [
            LinhaSaidas("000.000.001", 2, Decimal("2"), Decimal("0")),
            LinhaSaidas("001.001.001", 1, Decimal("3"), Decimal("0")),
        ],
        canonicos,
    )
    assert linha.qtd == Decimal("13")
    assert repor(linha.qtd, "0", dias=13).consumo_diario == Decimal("1")

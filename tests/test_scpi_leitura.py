from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from scpi.leitura import (
    ErroImportacao,
    data_br,
    decimal_br,
    ler_cadastro,
    ler_estoque,
    ler_saidas,
)

FIX = Path(__file__).parent / "fixtures" / "scpi"


def test_ler_cadastro():
    leitura = ler_cadastro((FIX / "cadastro.csv").read_bytes())
    codigos = [linha.codigo for linha in leitura.linhas]
    assert codigos == ["001.001.001", "001.001.002", "013.005.007", "013.005.007", "017.004"]
    primeira = leitura.linhas[0]
    assert (primeira.nome, primeira.unidade, primeira.grupo, primeira.subgrupo) == (
        "DETERGENTE NEUTRO 500 ML",
        "UN",
        "MATERIAL DE LIMPEZA",
        "PRODUTOS DE LIMPEZA",
    )
    assert not primeira.oculto and leitura.linhas[1].oculto
    assert leitura.avisos == ["Linhas sem código ou nome ignoradas: 1."]


def test_ler_cadastro_sem_bom_e_com_fim_de_linha_unix():
    conteudo = (FIX / "cadastro.csv").read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    assert len(ler_cadastro(conteudo.encode()).linhas) == 5


def test_ler_cadastro_junta_os_relatorios_de_cada_tipo_na_ordem():
    produtos = (FIX / "cadastro.csv").read_bytes()
    pneus = (
        "\ufeffCADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR;GRUPO\r\n"
        "021.001.001;PNEU 275/80 R22,5;UN;AUTO PECAS;PNEUS;Não\r\n"
        "021.001.002;;UN;AUTO PECAS;PNEUS;Não\r\n"
    ).encode()
    vazio = b"CADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR;GRUPO\r\n"
    leitura = ler_cadastro([produtos, vazio, pneus])
    codigos = [linha.codigo for linha in leitura.linhas]
    assert codigos == [
        "001.001.001",
        "001.001.002",
        "013.005.007",
        "013.005.007",
        "017.004",
        "021.001.001",
    ]
    assert leitura.avisos == ["Linhas sem código ou nome ignoradas: 2."]


def test_ler_estoque_com_milhar_e_quantidade_invalida():
    leitura = ler_estoque((FIX / "estoque.csv").read_bytes())
    assert {linha.codigo: linha.qtd for linha in leitura.linhas} == {
        "001.001.001": Decimal("12"),
        "013.005.007": Decimal("1234.5"),
        "999.999.999": Decimal("5"),
    }
    assert leitura.avisos == ["Quantidade inválida ignorada: 001.001.002 ('abc')."]


def test_ler_saidas():
    leitura = ler_saidas((FIX / "saidas.csv").read_bytes())
    primeira = leitura.linhas[0]
    assert (primeira.id_requi, primeira.cadpro, primeira.data, primeira.qtd, primeira.valor) == (
        "2",
        "013.005.007",
        date(2026, 1, 12),
        Decimal("2"),
        Decimal("6.2"),
    )
    assert len(leitura.linhas) == 5 and leitura.linhas[-1].valor == Decimal(0)
    assert leitura.avisos == []


def test_saida_com_data_invalida_vira_aviso():
    conteudo = (
        "GRUPO;ID_REQUI;CADPRO;DTLAN;QUAN2;VATO2\r\n12/01/2026;7;001.001.001;32/13/2026;1;1\r\n"
    )
    leitura = ler_saidas(conteudo.encode())
    assert leitura.linhas == []
    assert leitura.avisos == ["Data inválida ignorada: requisição 7, 001.001.001 ('32/13/2026')."]


def test_linha_curta_completa_com_vazio():
    conteudo = "CADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR;GRUPO\r\n001.001.001;SABÃO\r\n"
    linha = ler_cadastro(conteudo.encode()).linhas[0]
    assert (linha.nome, linha.unidade, linha.oculto) == ("SABÃO", "", False)


@pytest.mark.parametrize(
    ("texto", "valor"),
    [("8,9948", "8.9948"), ("1.234,5", "1234.5"), ("172", "172"), ("-3", "-3"), (" 2,5 ", "2.5")],
)
def test_decimal_br(texto, valor):
    assert decimal_br(texto) == Decimal(valor)


@pytest.mark.parametrize("texto", ["", "abc", "1,2,3", "NaN", "Infinity"])
def test_decimal_br_recusa(texto):
    with pytest.raises(ValueError):
        decimal_br(texto)


def test_data_br():
    assert data_br("12/01/2026") == date(2026, 1, 12)
    assert data_br("12/01/2026 10:30:00") == date(2026, 1, 12)
    with pytest.raises(ValueError):
        data_br("2026-01-12")


def test_cabecalho_ausente():
    with pytest.raises(ErroImportacao, match=r"^Estoque: cabeçalho\(s\) ausente\(s\): QUAN3$"):
        ler_estoque(b"CADPRO;DISC1\r\n001.001.001;X\r\n")


def test_arquivo_vazio_e_cabecalho_ausente():
    with pytest.raises(ErroImportacao, match="Cadastro: cabeçalho"):
        ler_cadastro(b"")


def test_saidas_sem_cabecalho():
    with pytest.raises(ErroImportacao, match=r"^Saídas do SCPI: cabeçalho"):
        ler_saidas(b"12/01/2026;2\r\n")


def test_arquivo_fora_do_utf8():
    with pytest.raises(ErroImportacao, match="^Cadastro: o arquivo não está em UTF-8.$"):
        ler_cadastro("CADPRO;DISC1\n001.001.001;AÇÚCAR\n".encode("cp1252"))


def test_aspas_no_comeco_de_um_campo_nao_engolem_os_registros_seguintes():
    """O SCPI não põe campos entre aspas (as quebras de linha vêm soltas): uma aspa no começo
    de um campo é dado e não pode juntar o registro com os seguintes."""
    conteudo = (
        "CADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR;GRUPO\r\n"
        '001.001.001;"TUBO 1/2 POL;UN;G;S;Não\r\n'
        "001.001.002;OUTRO;UN;G;S;Não\r\n"
        "001.001.003;MAIS UM;UN;G;S;Sim\r\n"
    )
    linhas = ler_cadastro(conteudo.encode()).linhas
    assert [(x.codigo, x.nome, x.unidade) for x in linhas] == [
        ("001.001.001", '"TUBO 1/2 POL', "UN"),
        ("001.001.002", "OUTRO", "UN"),
        ("001.001.003", "MAIS UM", "UN"),
    ]
    assert linhas[2].oculto


def test_campo_entre_aspas_com_ponto_e_virgula_continua_lido():
    conteudo = (
        "CADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR;GRUPO\r\n"
        '001.001.001;"PARAFUSO; SEXTAVADO";UN;G;S;Não;001\r\n'
    )
    linha = ler_cadastro(conteudo.encode()).linhas[0]
    assert (linha.nome, linha.unidade) == ("PARAFUSO; SEXTAVADO", "UN")


# ------------------------------------------------- CSV salvo por planilha (vírgula, com aspas)


def _como_planilha(nome, registros, quebra_no_campo=None):
    """A fixture do SCPI regravada como o Google Sheets ou o Excel salvam: separada por vírgula,
    com aspas em volta do que tem vírgula ou quebra de linha. `quebra_no_campo` põe uma quebra de
    linha dentro desse campo do primeiro registro de dados."""
    import csv
    import io

    from scpi.leitura import _campos

    linhas = registros((FIX / nome).read_text(encoding="utf-8-sig"))
    cabecalho = _campos(linhas[0])
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\r\n")
    escritor.writerow(cabecalho)
    for n, registro in enumerate(linhas[1:]):
        campos = _campos(registro, len(cabecalho))
        if n == 0 and quebra_no_campo:
            i = cabecalho.index(quebra_no_campo)
            campos[i] = campos[i] + "\nsegunda linha"
        escritor.writerow(campos)
    return saida.getvalue().encode("utf-8")


@pytest.mark.parametrize(
    ("nome", "ler", "registros"),
    [
        ("cadastro.csv", ler_cadastro, "registros_produtos"),
        ("estoque.csv", ler_estoque, "registros_produtos"),
        ("saidas.csv", ler_saidas, "registros_saidas"),
    ],
)
def test_csv_separado_por_virgula_le_igual_ao_do_scpi(nome, ler, registros):
    from scpi import normalizadores

    virgula = _como_planilha(nome, getattr(normalizadores, registros))
    assert b";" not in virgula.split(b"\r\n")[0]
    assert ler(virgula) == ler((FIX / nome).read_bytes())


def test_csv_com_virgula_aceita_quebra_de_linha_dentro_de_campo_entre_aspas():
    from scpi.normalizadores import registros_saidas

    virgula = _como_planilha("saidas.csv", registros_saidas, quebra_no_campo="DISC1")
    assert ler_saidas(virgula) == ler_saidas((FIX / "saidas.csv").read_bytes())


def test_csv_com_virgula_sem_as_colunas_continua_recusado():
    with pytest.raises(ErroImportacao, match="cabeçalho"):
        ler_saidas(b"GRUPO,OUTRA\n12/01/2026,x\n")


def test_ler_cadastro_descarta_o_grupo_800_dos_servicos():
    conteudo = (
        "CADPRO;DISC1;UNID1;GRUPO;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR\r\n"
        "016.002.170;EXTREMIDADE FOFO;UN;016;MATERIAL PARA REDES DE ÁGUA;CONEXÕES;Não\r\n"
        "800.009.185;ABRIGO DO ELEMENTO SECUNDÁRIO;UN;800;SERVICOS;SERVIÇOS;Não\r\n"
        "800.004;LEGADO SEM O TERCEIRO BLOCO;UN;800;GERAL;GERAL;Não\r\n"
        "800.009.999;;UN;800;SERVICOS;SERVIÇOS;Não\r\n"
    ).encode()
    leitura = ler_cadastro(conteudo)
    assert [linha.codigo for linha in leitura.linhas] == ["016.002.170"]
    assert leitura.avisos == []  # o descarte é silencioso, não é "linha sem código ou nome"


def test_ler_cadastro_sem_a_coluna_grupo_e_recusado():
    # Sem ela o descarte do grupo 800 não teria como acontecer.
    conteudo = (
        b"CADPRO;DISC1;UNID1;NOMEGRUPO;NOMESUBGRUPO;NOCULTAR\r\n001.001.001;SABAO;UN;G;S;Nao\r\n"
    )
    with pytest.raises(ErroImportacao, match="cabeçalho.*GRUPO"):
        ler_cadastro(conteudo)

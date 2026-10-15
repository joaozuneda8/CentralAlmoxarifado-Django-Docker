"""Leitura dos CSVs do SCPI: bytes do relatório → linhas tipadas. Sem ORM.

As colunas são localizadas pelo nome do cabeçalho, nunca pela posição. Linha que não dá para
ler vira aviso (a importação segue); arquivo ilegível ou sem as colunas vira `ErroImportacao`.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pedidos.regras import norm_u
from scpi.normalizadores import registros_produtos, registros_saidas


class ErroImportacao(Exception):
    """Falha esperada de uma importação; a mensagem vai para a saúde do catálogo."""


@dataclass(frozen=True)
class Leitura:
    linhas: list = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LinhaCadastro:
    codigo: str
    nome: str
    unidade: str
    grupo: str
    subgrupo: str
    oculto: bool


@dataclass(frozen=True)
class LinhaEstoque:
    codigo: str
    qtd: Decimal


@dataclass(frozen=True)
class LinhaSaidaSCPI:
    id_requi: str
    cadpro: str
    data: date
    qtd: Decimal
    valor: Decimal


def decimal_br(texto: str) -> Decimal:
    """'1.234,5' → Decimal('1234.5'); '8,9948' → Decimal('8.9948'). Inválido: ValueError."""
    t = (texto or "").strip()
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        valor = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"número inválido: {texto!r}") from None
    if not valor.is_finite():
        raise ValueError(f"número inválido: {texto!r}")
    return valor


def data_br(texto: str) -> date:
    """'12/01/2026' (com ou sem hora depois) → date(2026, 1, 12). Inválida: ValueError."""
    return datetime.strptime((texto or "").strip()[:10], "%d/%m/%Y").date()


def _campos(registro: str, esperado: int | None = None) -> list[str]:
    """Campos de um registro (uma linha, já recolada).

    Cada registro é lido sozinho, para uma aspa solta nunca juntar registros. O SCPI não põe
    campos entre aspas (as quebras de linha vêm soltas), então uma aspa no começo de um campo é
    dado: se a leitura com aspas não bate com o número de colunas do cabeçalho e a leitura
    literal (só `;`) chega mais perto, vale a literal.
    """
    try:
        com_aspas = next(csv.reader([registro], delimiter=";"), [])
    except csv.Error:
        com_aspas = []
    literal = registro.split(";")
    if esperado is None:
        return com_aspas or literal
    if len(com_aspas) != esperado and abs(len(literal) - esperado) < abs(len(com_aspas) - esperado):
        return literal
    return com_aspas


def _salvo_por_planilha(texto: str, inicio_cabecalho: str) -> bool:
    """O cabeçalho é separado por vírgula: o CSV do SCPI passou por uma planilha (Google Sheets,
    Excel) e foi salvo de novo. O do SCPI usa ";"."""
    cabecalho = next(
        (linha for linha in texto.splitlines() if linha.startswith(inicio_cabecalho)), ""
    )
    return cabecalho.count(",") > cabecalho.count(";")


def _registros_da_planilha(texto: str) -> list[list[str]]:
    """CSV padrão separado por vírgula: as aspas protegem vírgulas e quebras de linha dentro dos
    campos, então não há registro partido para recolar. A quebra de linha de um campo vira
    espaço, como na recolagem dos CSVs do SCPI."""
    return [
        [" ".join(campo.split("\n")) if "\n" in campo else campo for campo in linha]
        for linha in csv.reader(io.StringIO(texto, newline=""))
    ]


def _tabela(conteudo: bytes, rotulo: str, registros, inicio_cabecalho: str, colunas: list[str]):
    """Linhas do CSV como dicionários {coluna pedida → texto}. Aceita o CSV do SCPI (";") e o
    mesmo relatório salvo por uma planilha (",")."""
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ErroImportacao(f"{rotulo}: o arquivo não está em UTF-8.") from None
    cabecalho: list[str] = []
    corpo: list[list[str]] = []
    if _salvo_por_planilha(texto, inicio_cabecalho):
        divididos = _registros_da_planilha(texto.replace("\r\n", "\n").replace("\r", "\n"))
        pos = next(
            (i for i, c in enumerate(divididos) if c and c[0].startswith(inicio_cabecalho)), None
        )
        if pos is not None:
            cabecalho = [c.strip() for c in divididos[pos]]
            corpo = divididos[pos + 1 :]
    else:
        linhas = registros(texto)
        pos = next(
            (i for i, linha in enumerate(linhas) if linha.startswith(inicio_cabecalho)), None
        )
        if pos is not None:
            cabecalho = [c.strip() for c in _campos(linhas[pos])]
            corpo = [_campos(registro, len(cabecalho)) for registro in linhas[pos + 1 :]]
    faltando = [c for c in colunas if c not in cabecalho]
    if faltando:
        raise ErroImportacao(f"{rotulo}: cabeçalho(s) ausente(s): {', '.join(faltando)}")
    indices = {c: cabecalho.index(c) for c in colunas}
    tabela = []
    for linha in corpo:
        if not any(c.strip() for c in linha):
            continue
        tabela.append({c: (linha[i].strip() if i < len(linha) else "") for c, i in indices.items()})
    return tabela


# Grupos do SCPI que nunca entram no cadastro: o 800 é o dos serviços, que o SCPI deixa sair nos
# relatórios dos tipos de produto. A linha é descartada antes de tudo, como se não viesse no CSV.
GRUPOS_DESCARTADOS = frozenset({"800"})


def ler_cadastro(conteudo: bytes | list[bytes]) -> Leitura:
    """Um CSV ou vários (o robô baixa um relatório por tipo de produto): as linhas de todos são
    juntadas na ordem, como se fossem um só cadastro. As dos `GRUPOS_DESCARTADOS` ficam de fora."""
    colunas = ["CADPRO", "DISC1", "UNID1", "GRUPO", "NOMEGRUPO", "NOMESUBGRUPO", "NOCULTAR"]
    partes = conteudo if isinstance(conteudo, list) else [conteudo]
    tabela = [
        linha
        for parte in partes
        for linha in _tabela(parte, "Cadastro", registros_produtos, "CADPRO", colunas)
    ]
    linhas, ignoradas = [], 0
    for r in tabela:
        if r["GRUPO"] in GRUPOS_DESCARTADOS:
            continue
        if not r["CADPRO"] or not r["DISC1"]:
            ignoradas += 1
            continue
        linhas.append(
            LinhaCadastro(
                codigo=r["CADPRO"],
                nome=r["DISC1"],
                unidade=r["UNID1"],
                grupo=r["NOMEGRUPO"],
                subgrupo=r["NOMESUBGRUPO"],
                oculto=norm_u(r["NOCULTAR"]) == "SIM",
            )
        )
    avisos = [f"Linhas sem código ou nome ignoradas: {ignoradas}."] if ignoradas else []
    return Leitura(linhas, avisos)


def ler_estoque(conteudo: bytes) -> Leitura:
    tabela = _tabela(conteudo, "Estoque", registros_produtos, "CADPRO", ["CADPRO", "QUAN3"])
    linhas, avisos = [], []
    for r in tabela:
        if not r["CADPRO"]:
            continue
        try:
            linhas.append(LinhaEstoque(r["CADPRO"], decimal_br(r["QUAN3"])))
        except ValueError:
            avisos.append(f"Quantidade inválida ignorada: {r['CADPRO']} ('{r['QUAN3']}').")
    return Leitura(linhas, avisos)


def ler_saidas(conteudo: bytes) -> Leitura:
    colunas = ["ID_REQUI", "CADPRO", "DTLAN", "QUAN2", "VATO2"]
    tabela = _tabela(conteudo, "Saídas do SCPI", registros_saidas, "GRUPO", colunas)
    linhas, avisos, sem_chave = [], [], 0
    for r in tabela:
        if not r["ID_REQUI"] or not r["CADPRO"]:
            sem_chave += 1
            continue
        onde = f"requisição {r['ID_REQUI']}, {r['CADPRO']}"
        try:
            data = data_br(r["DTLAN"])
        except ValueError:
            avisos.append(f"Data inválida ignorada: {onde} ('{r['DTLAN']}').")
            continue
        try:
            qtd = decimal_br(r["QUAN2"])
        except ValueError:
            avisos.append(f"Quantidade inválida ignorada: {onde} ('{r['QUAN2']}').")
            continue
        try:
            valor = decimal_br(r["VATO2"]) if r["VATO2"] else Decimal(0)
        except ValueError:
            avisos.append(f"Valor inválido ignorado: {onde} ('{r['VATO2']}').")
            continue
        linhas.append(LinhaSaidaSCPI(r["ID_REQUI"], r["CADPRO"], data, qtd, valor))
    if sem_chave:
        avisos.append(f"Linhas sem requisição ou código ignoradas: {sem_chave}.")
    return Leitura(linhas, avisos)

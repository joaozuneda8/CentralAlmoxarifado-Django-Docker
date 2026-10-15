"""Recolagem dos registros dos CSVs do SCPI.

Os CSVs do SCPI trazem campos com quebra de linha: um registro sai partido em várias linhas.
Estas funções juntam cada registro numa linha só (as continuações entram com um espaço).

Copiado de `saep/normalizers/produtos.py` e `saep/normalizers/saidas.py` do extrair-relatorio
(commit cce15aa3706be09bf1cdb2b6c8768b2ab9a4a622). O algoritmo é o mesmo; só recebe o texto
inteiro e devolve a lista de registros em vez de ler e gravar arquivos.
"""

import re

# O terceiro bloco do CADPRO pode faltar (800.004) ou conter caracteres
# não numéricos (000.009.0-1) em registros legados do SAEP.
CADPRO_RE = re.compile(r"^\d{3}\.\d{3}(\.[\w-]{1,3})?;")
DATA_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")


def _linhas(texto: str) -> list[str]:
    """Linhas como o `readlines()` em modo texto: \\r\\n, \\r e \\n separam linhas."""
    linhas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if linhas and linhas[-1] == "":
        linhas.pop()
    return linhas


def _recolar(texto: str, inicio_re: re.Pattern, cabecalho: str) -> list[str]:
    registros: list[str] = []
    buffer: list[str] = []

    for linha in _linhas(texto):
        if inicio_re.match(linha) or (not registros and not buffer and linha.startswith(cabecalho)):
            if buffer:
                registros.append(" ".join(buffer))
                buffer = []
            buffer.append(linha)
        else:
            if buffer:
                buffer.append(linha.strip())
            else:
                registros.append(linha)

    if buffer:
        registros.append(" ".join(buffer))
    return registros


def registros_produtos(texto: str) -> list[str]:
    """Registros do relatório de produtos (cadastro e estoque); cabeçalho começa por CADPRO."""
    return _recolar(texto, CADPRO_RE, "CADPRO")


def registros_saidas(texto: str) -> list[str]:
    """Registros da relação de requisições de saída; cabeçalho começa por GRUPO."""
    return _recolar(texto, DATA_RE, "GRUPO")

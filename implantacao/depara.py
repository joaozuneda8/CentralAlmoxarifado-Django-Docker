"""Leitura dos pares de/para do .xlsx exportado da planilha MAPEAMENTO DE/PARA CONSOLIDADO (sem
banco; do modelo só o tamanho da observação). Usada pelo comando `importar_depara`, carga única
da implantação.

Os pares do espelho vêm da aba de mapeamento original, e não do `DEPARA_MAP` (uma fórmula
`FILTER`, cujo valor no .xlsx pode estar velho): o sistema aplica as regras declaradas no próprio
`DEPARA_MAP` (os dois códigos no formato 000.000.000, antigo diferente do novo, a primeira
ocorrência vale). As correções da aba `DEPARA` vencem o espelho e trazem o fator.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

from catalogo.depara import FORMATO_CODIGO, CicloDePara, Par, resolver_canonicos, validar_par
from catalogo.models import ParDePara
from implantacao.planilha import ErroPlanilha, Linha, ler_xlsx, texto_celula
from pedidos.regras import norm_u

PREFIXO_ABA_MAPEAMENTO = "PLANILHA DE MAPEAMENTO"
COLUNAS_MAPEAMENTO = ("Código Antigo", "Código Novo")
ABA_DEPARA = "DEPARA"
COLUNAS_DEPARA = ("Código Antigo", "Código Novo")
MAX_OBSERVACAO = ParDePara._meta.get_field("observacao").max_length


@dataclass
class CargaDePara:
    pares: list[Par] = field(default_factory=list)
    observacoes: dict[str, str] = field(default_factory=dict)  # código antigo → observação
    recusados: list[str] = field(default_factory=list)
    lidos_mapeamento: int = 0
    ignorados: int = 0  # linhas da aba de mapeamento sem par no formato (PRODUTO NOVO, traço...)
    correcoes: int = 0  # linhas da aba DEPARA


def _aba_de_mapeamento(caminho: Path) -> str:
    livro = openpyxl.load_workbook(caminho, read_only=True)
    try:
        nomes = livro.sheetnames
    finally:
        livro.close()
    for nome in nomes:
        if norm_u(nome).startswith(PREFIXO_ABA_MAPEAMENTO):
            return nome
    raise ErroPlanilha(
        'A planilha não tem a aba de mapeamento (o nome deve começar por "Planilha de mapeamento").'
    )


def _fator(valor: object) -> Decimal | None:
    """Fator da célula: vazio vale 1; número ou texto com vírgula ou ponto; inválido (inclusive
    NaN e infinito) → None."""
    texto = texto_celula(valor)
    if not texto:
        return Decimal("1")
    try:
        fator = Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None
    return fator if fator.is_finite() else None


def ler_pares(caminho: Path) -> CargaDePara:
    """Pares aceitos e o relatório do que ficou de fora. Aba ou coluna ausente: `ErroPlanilha`."""
    aba_mapeamento = _aba_de_mapeamento(caminho)
    abas = ler_xlsx(caminho, {aba_mapeamento: COLUNAS_MAPEAMENTO, ABA_DEPARA: COLUNAS_DEPARA})
    carga = CargaDePara(lidos_mapeamento=len(abas[aba_mapeamento]))
    aceitos: dict[str, tuple[Par, str, int]] = {}  # antigo normalizado → (par, aba, linha)

    def recusar(aba: str, linha: Linha, antigo: str, novo: str, motivo: str) -> None:
        carga.recusados.append(f"{aba}, linha {linha['_linha']}: {antigo} → {novo}: {motivo}")

    def aceitar(aba: str, linha: Linha, par: Par) -> bool:
        """Registra o par em `aceitos`; devolve se foi aceito."""
        chave = norm_u(par.antigo)
        if chave in aceitos:
            _, aba_anterior, linha_anterior = aceitos[chave]
            if aba == aba_anterior:
                recusar(
                    aba,
                    linha,
                    par.antigo,
                    par.novo,
                    f"o código antigo já aparece na linha {linha_anterior}; vale a primeira "
                    "ocorrência.",
                )
            return False  # na aba de mapeamento, um código já corrigido pela DEPARA: vale a DEPARA
        erros = validar_par(par.antigo, par.novo, par.fator)
        if erros:
            recusar(aba, linha, par.antigo, par.novo, " ".join(erros))
            return False
        try:
            resolver_canonicos([par, *(p for p, _, _ in aceitos.values())])
        except CicloDePara as ciclo:
            recusar(
                aba, linha, par.antigo, par.novo, f"fecha um ciclo: {' → '.join(ciclo.caminho)}."
            )
            return False
        aceitos[chave] = (par, aba, linha["_linha"])
        return True

    for linha in abas[ABA_DEPARA]:
        carga.correcoes += 1
        antigo = texto_celula(linha.get("Código Antigo"))
        novo = texto_celula(linha.get("Código Novo"))
        fator = _fator(linha.get("Fator p/ Qtd"))
        if fator is None:
            bruto = texto_celula(linha.get("Fator p/ Qtd"))
            recusar(ABA_DEPARA, linha, antigo, novo, f"fator inválido ('{bruto}').")
            continue
        observacao = texto_celula(linha.get("Observação"))
        if len(observacao) > MAX_OBSERVACAO:
            motivo = f"observação com {len(observacao)} caracteres (máximo {MAX_OBSERVACAO})."
            recusar(ABA_DEPARA, linha, antigo, novo, motivo)
            continue
        if aceitar(ABA_DEPARA, linha, Par(antigo, novo, fator)) and observacao:
            carga.observacoes[antigo] = observacao

    for linha in abas[aba_mapeamento]:
        antigo = texto_celula(linha.get("Código Antigo"))
        novo = texto_celula(linha.get("Código Novo"))
        if (
            not FORMATO_CODIGO.match(antigo)
            or not FORMATO_CODIGO.match(novo)
            or norm_u(antigo) == norm_u(novo)
        ):
            carga.ignorados += 1
            continue
        aceitar(aba_mapeamento, linha, Par(antigo, novo))

    carga.pares = [par for par, _, _ in aceitos.values()]
    return carga

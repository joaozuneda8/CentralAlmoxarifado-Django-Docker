"""Dados de exemplo da planilha exportada do Apps Script, para os testes da implantação.

Datas sem aspas são `datetime` (célula de data); entre aspas, texto, como o Apps Script grava.
"""

from datetime import datetime
from pathlib import Path

import openpyxl

U1 = "11111111-1111-4111-8111-111111111111"
U2 = "22222222-2222-4222-8222-222222222222"
U3 = "33333333-3333-4333-8333-333333333333"
A1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
A2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _numerar(linhas):
    return [{**linha, "_linha": numero} for numero, linha in enumerate(linhas, start=2)]


def abas_exemplo() -> dict[str, list[dict[str, object]]]:
    pedidos = [
        {
            "Nº": "P-000120",
            "ID": U1,
            "Origem": "LIMPEZA",
            "Criado em": datetime(2026, 9, 1, 8, 30),
            "Solicitante": "Ana Exemplo",
            "Destino": "ETA II",
            "Observação": "",
            "Atendimento_ID": A1,
            "Data efetiva": "02/09/2026",
            "Recebedor": "Ana Exemplo",
            "Centro de custo": "ETA II",
            "Tipo Saída": "BALCÃO",
            "Placa": "",
            "Obs. da saída": "",
            "Atendido em": datetime(2026, 9, 2, 9, 0),
            "Recibo impresso em": datetime(2026, 9, 2, 9, 5),
        },
        {
            "Nº": "P-000121",
            "ID": U2,
            "Origem": "AB",
            "Criado em": datetime(2026, 9, 3, 10, 0),
            "Solicitante": "João Fictício",
            "Destino": "ETE Santa Fé",
            "Observação": "urgente",
            "Atendimento_ID": A2,
            "Data efetiva": "05/09/2026",
            "Recebedor": "João Fictício",
            "Centro de custo": "ETE Santa Fé",
            "Tipo Saída": "ENTREGA",
            "Placa": "",
            "Obs. da saída": "",
            "Atendido em": datetime(2026, 9, 5, 11, 0),
            "Recibo impresso em": None,
        },
        {
            "Nº": "AV-000122",
            "ID": U3,
            "Origem": "AVULSA",
            "Criado em": datetime(2026, 9, 4, 14, 0),
            "Solicitante": "almox@saep.sp.gov.br",
            "Destino": "",
            "Observação": "",
            "Atendimento_ID": U3,
            "Data efetiva": "04/09/2026",
            "Recebedor": "Motorista Teste",
            "Centro de custo": "FROTA",
            "Tipo Saída": "ENTREGA",
            "Placa": "CZA-1614",
            "Obs. da saída": "",
            "Atendido em": datetime(2026, 9, 4, 14, 0),
            "Recibo impresso em": None,
        },
    ]

    def item(
        pedido_id,
        numero,
        codigo,
        material,
        unidade,
        categoria,
        grupo,
        subgrupo,
        estoque,
        pedida,
        entregue,
    ):
        return {
            "Nº": numero,
            "ID": pedido_id,
            "Código": codigo,
            "Material": material,
            "Unidade": unidade,
            "Categoria": categoria,
            "Grupo": grupo,
            "Subgrupo": subgrupo,
            "Estoque no pedido": estoque,
            "Qtd pedida": pedida,
            "Qtd entregue": entregue,
        }

    itens = [
        item(
            U1,
            "P-000120",
            "023.001.002",
            "DETERGENTE NEUTRO",
            "UN",
            "Limpeza",
            "LIMPEZA",
            "SUB",
            "",
            2,
            2,
        ),
        item(
            U1,
            "P-000120",
            "008.001.002",
            "CAFÉ 500 G",
            "PCT",
            "Copa/cozinha",
            "GÊNEROS",
            "SUB",
            "",
            1.5,
            1.5,
        ),
        item(
            U2,
            "P-000121",
            "016.005.010",
            "FITA VEDA ROSCA",
            "UN",
            "",
            "REDES DE ÁGUA",
            "SUB",
            10,
            3,
            3,
        ),
        item(U3, "AV-000122", "023.004.001", "PAPEL HIGIÊNICO", "UN", "", "LIMPEZA", "", "", 1, 1),
    ]

    def saida(
        data,
        qtd,
        codigo,
        descricao,
        recebimento,
        centro,
        tipo,
        placa,
        requisicao,
        status,
        lancado,
        origem,
    ):
        return {
            "Data": data,
            "Qtd": qtd,
            "Código": codigo,
            "Descrição do Material": descricao,
            "Recebimento": recebimento,
            "Centro de Custo": centro,
            "Tipo Saída": tipo,
            "Veículo (Placa)": placa,
            "Observações": "",
            "Requisição": requisicao,
            "Status SCPI": status,
            "Lançado SCPI em": lancado,
            "Origem_ID": origem,
            "Lote_SCPI": origem,
        }

    saidas = [
        saida(
            "02/09/2026",
            "2",
            "023.001.002",
            "DETERGENTE NEUTRO",
            "Ana Exemplo",
            "ETA II",
            "BALCÃO",
            "",
            "003354/26",
            "LANÇADA",
            "02/09/2026 17:10:00",
            "P-000120",
        ),
        saida(
            "02/09/2026",
            "1,5",
            "008.001.002",
            "CAFÉ 500 G",
            "Ana Exemplo",
            "ETA II",
            "BALCÃO",
            "",
            "003354/26",
            "LANÇADA",
            "02/09/2026 17:10:00",
            "P-000120",
        ),
        saida(
            "05/09/2026",
            "3",
            "016.005.010",
            "FITA VEDA ROSCA",
            "João Fictício",
            "ETE Santa Fé",
            "ENTREGA",
            "",
            "",
            "",
            "",
            "P-000121",
        ),
        saida(
            "04/09/2026",
            "1",
            "023.004.001",
            "PAPEL HIGIÊNICO",
            "Motorista Teste",
            "FROTA",
            "ENTREGA",
            "CZA1614",
            "",
            "VERIFICAR NO SCPI: tempo esgotado",
            "",
            "AV-000122",
        ),
    ]

    centros = [
        {"DESCR": "ETA II", "CODCCUSTO": "101", "PLACA": ""},
        {"DESCR": "ETE Santa Fé", "CODCCUSTO": "102", "PLACA": ""},
        {"DESCR": "FROTA", "CODCCUSTO": "205", "PLACA": "CZA1614"},
    ]

    listas = [
        {
            "Destinos": "ETA II",
            "Tipos de saída": "BALCÃO",
            "Grupos ocultos (AB)": "GERAL",
            "Categorias (limpeza)": "Limpeza",
            "Funcionários": "Ana Exemplo",
        },
        {
            "Destinos": None,
            "Tipos de saída": "ENTREGA",
            "Grupos ocultos (AB)": None,
            "Categorias (limpeza)": "Copa/cozinha",
            "Funcionários": None,
        },
    ]

    lista_limpeza = [
        {
            "Código": "023.001.002",
            "Categoria": "Limpeza",
            "Nome exibido": "Detergente",
            "Unidade exibida": "",
        },
        {
            "Código": "008.001.002",
            "Categoria": "Copa/cozinha",
            "Nome exibido": "",
            "Unidade exibida": "PCT",
        },
    ]

    return {
        "Pedidos": _numerar(pedidos),
        "Itens": _numerar(itens),
        "Saídas": _numerar(saidas),
        "Centros de Custo": _numerar(centros),
        "Listas": _numerar(listas),
        "Lista_Limpeza": _numerar(lista_limpeza),
    }


def salvar_xlsx(abas: dict[str, list[dict[str, object]]], caminho: Path) -> Path:
    """Grava uma aba por chave; o cabeçalho são as chaves da primeira linha, sem `_linha`."""
    livro = openpyxl.Workbook()
    livro.remove(livro.active)
    for nome, linhas in abas.items():
        folha = livro.create_sheet(nome)
        cabecalho = [chave for chave in linhas[0] if chave != "_linha"]
        folha.append(cabecalho)
        for linha in linhas:
            folha.append([linha.get(chave) for chave in cabecalho])
    livro.save(caminho)
    return caminho

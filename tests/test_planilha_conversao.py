import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from implantacao.conversao import converter, status_da_planilha
from tests.planilha_exemplo import abas_exemplo


def test_exemplo_converte_sem_erros():
    c = converter(abas_exemplo())
    assert c.erros == [] and c.avisos == []
    assert [p.numero for p in c.pedidos] == ["P-000120", "P-000121", "AV-000122"]
    assert len(c.itens) == 4 and len(c.atendimentos) == 3 and c.ultimo_numero == 122
    assert [(linha.lote, linha.seq, linha.status) for linha in c.linhas] == [
        ("P-000120", 1, "LANCADA"),
        ("P-000120", 2, "LANCADA"),
        ("P-000121", 1, "PENDENTE"),
        ("AV-000122", 1, "VERIFICAR"),
    ]
    av = c.linhas[3]
    assert av.placa == "CZA1614" and av.mensagem == "VERIFICAR NO SCPI: tempo esgotado"
    assert c.linhas[1].qtd == Decimal("1.5") and c.linhas[0].requisicao_scpi == "003354/26"
    lancado = timezone.localtime(c.linhas[0].lancado_em).replace(tzinfo=None)
    assert lancado == datetime(2026, 9, 2, 17, 10)
    assert c.atendimentos[2].id == c.pedidos[2].id and c.atendimentos[2].placa == "CZA1614"
    assert c.atendimentos[0].recibo_impresso_em is not None
    assert c.atendimentos[1].recibo_impresso_em is None
    assert [(o.lista, o.valor) for o in c.opcoes] == [
        ("TIPO_SAIDA", "BALCÃO"),
        ("TIPO_SAIDA", "ENTREGA"),
        ("GRUPO_OCULTO_AB", "GERAL"),
        ("CATEGORIA_LIMPEZA", "Limpeza"),
        ("CATEGORIA_LIMPEZA", "Copa/cozinha"),
        ("FUNCIONARIO", "Ana Exemplo"),
    ]
    assert [(x.codigo, x.placa) for x in c.centros] == [
        ("101", None),
        ("102", None),
        ("205", "CZA1614"),
    ]
    assert c.itens_limpeza == [
        ("023.001.002", "Limpeza", "Detergente", "", 0),
        ("008.001.002", "Copa/cozinha", "", "PCT", 0),
    ]


def test_registros_apontam_para_os_objetos_da_carga():
    c = converter(abas_exemplo())
    assert c.atendimentos[0].pedido is c.pedidos[0]
    assert [i.pedido for i in c.itens] == [c.pedidos[0], c.pedidos[0], c.pedidos[1], c.pedidos[2]]
    assert [linha.atendimento for linha in c.linhas] == [
        c.atendimentos[0],
        c.atendimentos[0],
        c.atendimentos[1],
        c.atendimentos[2],
    ]
    assert c.itens[1].qtd_pedida == Decimal("1.5") and c.itens[2].estoque_no_pedido == 10
    assert c.itens[0].estoque_no_pedido is None
    assert c.pedidos[0].registrado_por_id is None and c.atendimentos[0].atendido_por_id is None


@pytest.mark.parametrize(
    ("status", "requisicao", "obs", "esperado"),
    [
        ("LANÇADA", "003354/26", "", "LANCADA"),
        ("", "003354/26", "", "LANCADA"),
        ("ERRO: x", "003354/26", "NÃO LANÇAR", "LANCADA"),
        ("", "", "FORA DE ESTOQUE", "NAO_LANCAR"),
        ("", "", "não lançar", "NAO_LANCAR"),
        ("VERIFICAR NO SCPI: x", "", "", "VERIFICAR"),
        ("EM LANÇAMENTO 09/10", "", "", "EM_LANCAMENTO"),
        ("ERRO: saldo", "", "", "ERRO"),
        ("LANÇADA", "", "", "LANCADA"),
        ("", "", "", "PENDENTE"),
        ("OK", "", "", None),
    ],
)
def test_status_da_planilha(status, requisicao, obs, esperado):
    assert status_da_planilha(status, requisicao, obs) == esperado


@pytest.mark.parametrize(
    ("aba", "indice", "campos", "erro"),
    [
        ("Pedidos", 0, {"ID": "abc"}, "Pedidos, linha 2: ID inválido"),
        ("Pedidos", 0, {"Nº": "X-1"}, "Pedidos, linha 2: número inválido"),
        ("Pedidos", 0, {"Origem": "OUTRA"}, "Pedidos, linha 2: origem inválida"),
        (
            "Pedidos",
            2,
            {"Nº": "P-000122"},
            "Pedidos, linha 4: o número P-000122 não combina com a origem AVULSA",
        ),
        ("Pedidos", 0, {"Criado em": ""}, "Pedidos, linha 2: data de criação inválida"),
        ("Pedidos", 0, {"Data efetiva": "31/02/2026"}, "Pedidos, linha 2: data efetiva inválida"),
        ("Pedidos", 0, {"Atendimento_ID": "x"}, "Pedidos, linha 2: ID do atendimento inválido"),
        ("Pedidos", 2, {"Atendimento_ID": ""}, "Pedidos, linha 4: saída avulsa sem atendimento"),
        ("Itens", 0, {"Qtd pedida": "1.5"}, "Itens, linha 2: quantidade pedida inválida"),
        ("Itens", 0, {"Qtd entregue": "abc"}, "Itens, linha 2: quantidade entregue inválida"),
        ("Saídas", 2, {"Qtd": "0"}, "Saídas, linha 4: quantidade inválida"),
        ("Saídas", 2, {"Data": ""}, "Saídas, linha 4: data inválida"),
        ("Saídas", 2, {"Origem_ID": "P-000999"}, "Saídas, linha 4: saída sem atendimento"),
        ("Centros de Custo", 0, {"CODCCUSTO": ""}, "Centros de Custo, linha 2: código vazio"),
        (
            "Centros de Custo",
            0,
            {"PLACA": "cza-1614"},
            "Centros de Custo, linha 4: a placa CZA1614 já está na linha 2",
        ),
    ],
)
def test_erros(aba, indice, campos, erro):
    abas = abas_exemplo()
    abas[aba][indice].update(campos)
    assert any(e.startswith(erro) for e in converter(abas).erros), converter(abas).erros


def test_id_e_numero_repetidos():
    abas = abas_exemplo()
    abas["Pedidos"][1].update({"ID": abas["Pedidos"][0]["ID"], "Nº": "P-000120"})
    erros = converter(abas).erros
    assert any(e.startswith("Pedidos, linha 3: ID repetido (linha 2)") for e in erros)
    assert any(e.startswith("Pedidos, linha 3: número repetido (linha 2)") for e in erros)


def test_pedido_com_erro_nao_gera_erro_enganoso_nas_saidas_e_itens():
    """O erro é do pedido: a saída dele não pede para concluir a transferência no Apps Script,
    nem o item vira "gravação incompleta"."""
    abas = abas_exemplo()
    abas["Pedidos"][1]["Criado em"] = ""
    c = converter(abas)
    assert any(e.startswith("Pedidos, linha 3: data de criação inválida") for e in c.erros)
    assert not any(e.startswith("Saídas, linha 4") for e in c.erros)
    assert not any(a.startswith("Itens, linha 4") for a in c.avisos)


def test_saida_de_pedido_sem_atendimento_e_erro():
    abas = abas_exemplo()
    abas["Pedidos"][1]["Atendimento_ID"] = ""
    assert any(
        e.startswith("Saídas, linha 4: saída sem atendimento") for e in converter(abas).erros
    )


@pytest.mark.parametrize(
    "campos",
    [
        {"Origem_ID": "P-000999", "Requisição": "003400/26"},
        {"Origem_ID": "P-000999", "Observações": "NÃO LANÇAR"},
    ],
)
def test_saida_sem_atendimento_ja_resolvida_e_so_aviso(campos):
    abas = abas_exemplo()
    abas["Saídas"][2].update(campos)
    c = converter(abas)
    assert c.erros == []
    assert any(a.startswith("Saídas, linha 4: saída sem atendimento ignorada") for a in c.avisos)
    assert len(c.linhas) == 3


def test_status_desconhecido_trava_a_linha_com_aviso():
    abas = abas_exemplo()
    abas["Saídas"][2]["Status SCPI"] = "OK"
    c = converter(abas)
    assert c.linhas[2].status == "VERIFICAR" and c.linhas[2].mensagem == "OK"
    assert any(a.startswith("Saídas, linha 4: status desconhecido") for a in c.avisos)


def test_item_sem_pedido_e_aviso_e_conta_na_numeracao():
    abas = abas_exemplo()
    abas["Itens"].append(
        {**abas["Itens"][0], "ID": str(uuid.uuid4()), "Nº": "P-000130", "_linha": 6}
    )
    c = converter(abas)
    assert c.erros == [] and c.ultimo_numero == 130 and len(c.itens) == 4
    assert any(a.startswith("Itens, linha 6: item sem pedido") for a in c.avisos)


def test_lista_limpeza_repetida_ou_com_categoria_fora_da_lista():
    abas = abas_exemplo()
    abas["Lista_Limpeza"].append({**abas["Lista_Limpeza"][0], "_linha": 4})
    abas["Lista_Limpeza"][1]["Categoria"] = "Escritório"
    c = converter(abas)
    assert [i[0] for i in c.itens_limpeza] == ["023.001.002", "008.001.002"]
    assert any(a.startswith("Lista_Limpeza, linha 4: código repetido") for a in c.avisos)
    assert any(a.startswith("Lista_Limpeza, linha 3:") and "Escritório" in a for a in c.avisos)


def test_pedido_sem_itens_e_linha_sem_id_geram_avisos():
    abas = abas_exemplo()
    abas["Itens"] = [i for i in abas["Itens"] if i["ID"] != abas["Pedidos"][1]["ID"]]
    abas["Pedidos"].append({**abas["Pedidos"][0], "ID": "", "Nº": "P-000140", "_linha": 5})
    c = converter(abas)
    assert any(a.startswith("Pedidos, linha 3: pedido sem itens") for a in c.avisos)
    assert any(a.startswith("Pedidos, linha 5: linha sem ID ignorada") for a in c.avisos)
    assert len(c.pedidos) == 3 and c.ultimo_numero == 140


def test_saida_sem_lote_usa_o_numero_e_lancado_ilegivel_vira_aviso():
    abas = abas_exemplo()
    abas["Saídas"][0].update({"Lote_SCPI": "", "Lançado SCPI em": "ontem"})
    c = converter(abas)
    assert c.erros == [] and c.linhas[0].lote == "P-000120" and c.linhas[0].lancado_em is None
    assert any(a.startswith("Saídas, linha 2:") and "Lançado SCPI em" in a for a in c.avisos)


def test_atendido_em_vazio_usa_criado_em_e_nao_lancar_vem_da_observacao():
    abas = abas_exemplo()
    abas["Pedidos"][1].update({"Atendido em": None, "Obs. da saída": "FORA DE ESTOQUE"})
    c = converter(abas)
    assert c.atendimentos[1].atendido_em == c.pedidos[1].criado_em
    assert c.atendimentos[1].nao_lancar is True and c.atendimentos[0].nao_lancar is False


def test_listas_ignoram_vazios_e_repetidos():
    abas = abas_exemplo()
    abas["Listas"][1]["Tipos de saída"] = "balcão"
    abas["Listas"].append({"Tipos de saída": "", "Funcionários": "Ana Exemplo", "_linha": 4})
    c = converter(abas)
    assert [o.valor for o in c.opcoes if o.lista == "TIPO_SAIDA"] == ["BALCÃO"]
    assert [o.valor for o in c.opcoes if o.lista == "FUNCIONARIO"] == ["Ana Exemplo"]


@pytest.mark.parametrize(
    ("aba", "indice", "campo", "tamanho", "erro"),
    [
        ("Pedidos", 0, "Observação", 201, "Pedidos, linha 2: Observação com 201 caracteres"),
        ("Pedidos", 0, "Solicitante", 201, "Pedidos, linha 2: Solicitante com 201 caracteres"),
        ("Pedidos", 0, "Recebedor", 201, "Pedidos, linha 2: Recebedor com 201 caracteres"),
        ("Pedidos", 0, "Obs. da saída", 201, "Pedidos, linha 2: Observações com 201 caracteres"),
        ("Itens", 0, "Material", 256, "Itens, linha 2: Material com 256 caracteres"),
        ("Saídas", 2, "Observações", 201, "Saídas, linha 4: Observações com 201 caracteres"),
        ("Saídas", 2, "Lote_SCPI", 13, "Saídas, linha 4: Lote com 13 caracteres (máximo 12)."),
        ("Centros de Custo", 0, "DESCR", 201, "Centros de Custo, linha 2: Descrição com 201"),
        ("Lista_Limpeza", 0, "Nome exibido", 256, "Lista_Limpeza, linha 2: Nome exibido com 256"),
    ],
)
def test_texto_maior_que_o_campo_e_erro_listado(aba, indice, campo, tamanho, erro):
    abas = abas_exemplo()
    abas[aba][indice][campo] = "x" * tamanho
    erros = converter(abas).erros
    assert any(e.startswith(erro) for e in erros), erros
    assert any("(máximo " in e and e.endswith(").") for e in erros), erros


def test_opcao_maior_que_o_campo_e_erro():
    abas = abas_exemplo()
    abas["Listas"][0]["Funcionários"] = "x" * 201
    erros = converter(abas).erros
    assert any(e.startswith("Listas, linha 2: Valor com 201 caracteres") for e in erros), erros


def test_texto_no_limite_nao_e_erro():
    abas = abas_exemplo()
    abas["Pedidos"][0]["Observação"] = "x" * 200
    abas["Saídas"][2]["Lote_SCPI"] = "P-000121xxxx"
    assert converter(abas).erros == []


def test_atendimento_id_repetido_entre_pedidos_e_erro():
    abas = abas_exemplo()
    abas["Pedidos"][1]["Atendimento_ID"] = abas["Pedidos"][0]["Atendimento_ID"]
    erros = converter(abas).erros
    assert "Pedidos, linha 3: ID do atendimento repetido (linha 2)." in erros, erros


def test_itens_importados_sao_pedidos_pelo_solicitante():
    c = converter(abas_exemplo())
    assert c.itens
    assert all(i.origem == "PEDIDO" for i in c.itens)


def test_codigo_repetido_no_mesmo_pedido_e_erro():
    abas = abas_exemplo()
    repetido = {**abas["Itens"][1], "Nº": "P-000131", "_linha": 6}
    abas["Itens"].append(repetido)
    c = converter(abas)
    assert any(e == "Itens, linha 6: código 008.001.002 repetido no pedido" for e in c.erros)
    assert len([i for i in c.itens if i.codigo == "008.001.002"]) == 1

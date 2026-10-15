from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from catalogo.models import CentroCusto, Importacao, ItemLimpeza, Material, Opcao, SaidaSCPI
from catalogo.saude import (
    GrupoAvisos,
    ItemSaude,
    agrupar_avisos,
    ha_quanto,
    resumo_do_erro,
    saude_do_catalogo,
    situacao_do_catalogo,
)

pytestmark = pytest.mark.django_db

# 10/10/2026 14:30 no horário de Brasília (UTC-3).
AGORA = timezone.make_aware(datetime(2026, 10, 10, 14, 30))


def itens_de(prefixo, agora=AGORA):
    return [i for i in saude_do_catalogo(agora) if i.texto.startswith(prefixo)]


def texto_de(prefixo):
    (item,) = itens_de(prefixo)
    return item


def test_banco_vazio_nao_quebra():
    itens = saude_do_catalogo(AGORA)
    assert itens[:3] == [
        ItemSaude("erro", "Cadastro: nenhuma importação ainda."),
        ItemSaude("erro", "Estoque: nenhuma importação ainda."),
        ItemSaude("erro", "Saídas do SCPI: nenhuma importação ainda."),
    ]
    assert (
        ItemSaude(
            "erro",
            "Sem saldo importado: o formulário AB fica indisponível até a próxima importação "
            "de estoque.",
        )
        in itens
    )
    assert (
        ItemSaude(
            "aviso",
            "Nenhum centro de custo cadastrado: não é possível confirmar atendimentos nem "
            "registrar saídas.",
        )
        in itens
    )


def test_importacao_concluida_sem_avisos():
    Importacao.objects.create(
        tipo="CADASTRO", situacao="SUCESSO", inicio=AGORA - timedelta(minutes=5), fim=AGORA
    )
    assert texto_de("Cadastro: atualizado") == ItemSaude(
        "ok", "Cadastro: atualizado em 10/10/2026 14:30."
    )


def test_importacao_concluida_com_avisos():
    Importacao.objects.create(
        tipo="ESTOQUE", situacao="SUCESSO", fim=AGORA, avisos=["Aviso um.", "Aviso dois."]
    )
    assert texto_de("Estoque: atualizado") == ItemSaude(
        "aviso", "Estoque: atualizado em 10/10/2026 14:30, com avisos: Aviso um. Aviso dois."
    )


def test_falha_recente_aparece_como_erro_mesmo_com_sucesso_antes():
    Importacao.objects.create(
        tipo="ESTOQUE", situacao="SUCESSO", inicio=AGORA - timedelta(hours=1), fim=AGORA
    )
    Importacao.objects.create(
        tipo="ESTOQUE",
        situacao="FALHA",
        erro="Estoque: o CSV não tem nenhum material; nada foi alterado.",
        inicio=AGORA - timedelta(minutes=5),
        fim=AGORA - timedelta(minutes=4),
    )
    assert itens_de("Estoque:") == [
        ItemSaude(
            "erro",
            "Estoque: a última importação falhou em 10/10/2026 14:26: Estoque: o CSV não tem "
            "nenhum material; nada foi alterado. Os dados anteriores continuam valendo.",
        )
    ]


def test_importacao_interrompida_vira_aviso():
    Importacao.objects.create(tipo="CADASTRO", inicio=AGORA - timedelta(hours=2))
    assert texto_de("Cadastro: a importação") == ItemSaude(
        "aviso", "Cadastro: a importação iniciada em 10/10/2026 12:30 não terminou (interrompida)."
    )


def test_importacao_em_andamento(trava_importacao_ocupada):
    trava_importacao_ocupada("SAIDAS")
    Importacao.objects.create(tipo="SAIDAS", inicio=AGORA - timedelta(minutes=10))
    assert texto_de("Saídas do SCPI: importação") == ItemSaude(
        "ok", "Saídas do SCPI: importação em andamento desde 10/10/2026 14:20."
    )


def test_cadastro_e_duplicados():
    Material.objects.create(codigo="A", nome="A")
    Material.objects.create(codigo="B", nome="B", oculto=True)
    Material.objects.create(codigo="C", nome="C", duplicado=True)
    assert texto_de("Cadastro: 3") == ItemSaude(
        "ok", "Cadastro: 3 materiais; 1 ocultos no SCPI ficam fora de todos os formulários."
    )
    assert texto_de("Códigos repetidos") == ItemSaude(
        "aviso", "Códigos repetidos no cadastro (bloqueados): C."
    )


def test_saldo_velho_gera_aviso():
    Material.objects.create(codigo="A", nome="A", estoque_em=AGORA - timedelta(hours=25))
    assert texto_de("O saldo de estoque") == ItemSaude(
        "aviso", "O saldo de estoque não é atualizado desde 09/10/2026 13:30 (mais de 24 h)."
    )
    assert not itens_de("Sem saldo importado")


def test_saldo_recente_nao_gera_aviso():
    Material.objects.create(codigo="A", nome="A", estoque_em=AGORA - timedelta(hours=23))
    assert not itens_de("O saldo de estoque")


def test_limpeza_e_itens_ocultos():
    Opcao.objects.create(lista="CATEGORIA_LIMPEZA", valor="Limpeza")
    for codigo, oculto in [("A", False), ("B", False), ("X", True)]:
        m = Material.objects.create(codigo=codigo, nome=codigo, oculto=oculto)
        ItemLimpeza.objects.create(material=m, categoria="Limpeza")
    assert texto_de("Formulário de limpeza") == ItemSaude("ok", "Formulário de limpeza: 2 itens.")
    assert texto_de("Itens da lista de limpeza") == ItemSaude(
        "aviso", "Itens da lista de limpeza ocultos no SCPI (não aparecem): X."
    )


def test_formulario_ab_e_codigos_sem_cadastro():
    Material.objects.create(codigo="A", nome="A", estoque_em=AGORA)
    Material.objects.create(codigo="O", nome="O", oculto=True, estoque_em=AGORA)
    for n, codigo in enumerate(["A", "O", "Z"]):
        SaidaSCPI.objects.create(
            id_requi=str(n), cadpro=codigo, data=date(2026, 1, 1), qtd=1, valor=0
        )
    assert texto_de("Formulário AB") == ItemSaude(
        "ok",
        "Formulário AB: 1 itens de 3 códigos com saída no SCPI (0 também na lista de limpeza, "
        "que prevalece; 1 ocultos ou em grupo oculto).",
    )
    assert texto_de("Códigos com saída") == ItemSaude(
        "aviso", "Códigos com saída no SCPI sem cadastro (não aparecem): Z."
    )


def test_com_centro_de_custo_nao_avisa():
    CentroCusto.objects.create(descricao="Oficina", codigo="20")
    assert not itens_de("Nenhum centro de custo")


def test_agora_padrao_e_o_momento_atual():
    assert saude_do_catalogo()[0].texto == "Cadastro: nenhuma importação ainda."


def test_codigo_antigo_com_par_nao_aparece_como_sem_cadastro():
    from catalogo.models import ParDePara

    Material.objects.create(codigo="001.001.001", nome="NOVO", estoque_em=AGORA)
    ParDePara.objects.create(antigo="000.000.001", novo="001.001.001")
    ParDePara.objects.create(antigo="000.000.002", novo="002.002.002")
    for n, codigo in enumerate(["000.000.001", "001.001.001", "000.000.002"]):
        SaidaSCPI.objects.create(
            id_requi=str(n), cadpro=codigo, data=date(2026, 1, 1), qtd=1, valor=0
        )
    assert texto_de("Formulário AB") == ItemSaude(
        "ok",
        "Formulário AB: 1 itens de 2 códigos com saída no SCPI (0 também na lista de limpeza, "
        "que prevalece; 0 ocultos ou em grupo oculto).",
    )
    assert texto_de("Códigos com saída") == ItemSaude(
        "aviso", "Códigos com saída no SCPI sem cadastro (não aparecem): 002.002.002."
    )


def test_pares_de_para_so_aparecem_depois_da_primeira_carga():
    assert not itens_de("Pares de/para")
    Importacao.objects.create(
        tipo="DEPARA", situacao="SUCESSO", fim=AGORA - timedelta(hours=1), linhas=3
    )
    (item,) = itens_de("Pares de/para")
    assert item.nivel == "ok"


# ---- avisos agrupados, tempo e erro ------------------------------------------------------------


def test_agrupar_avisos_junta_pelo_comeco_e_mantem_a_ordem():
    avisos = [
        "Texto cortado em nome (255 caracteres): 001.",
        "Códigos com saldo sem cadastro (ignorados): 9, 8.",
        "Texto cortado em nome (255 caracteres): 002.",
        "Aviso sem detalhe.",
    ]
    assert agrupar_avisos(avisos) == [
        GrupoAvisos("Texto cortado em nome (255 caracteres)", ("001", "002")),
        GrupoAvisos("Códigos com saldo sem cadastro (ignorados)", ("9, 8",)),
        GrupoAvisos("Aviso sem detalhe", ()),
    ]
    textos = [g.texto for g in agrupar_avisos(avisos)]
    assert textos == [
        "Texto cortado em nome (255 caracteres) (2): 001, 002.",
        "Códigos com saldo sem cadastro (ignorados): 9, 8.",
        "Aviso sem detalhe.",
    ]


def test_saude_do_painel_agrupa_os_avisos_repetidos():
    Importacao.objects.create(
        tipo="CADASTRO",
        situacao="SUCESSO",
        fim=AGORA,
        avisos=[f"Texto cortado em nome (255 caracteres): 00{i}." for i in range(3)],
    )
    assert texto_de("Cadastro: atualizado") == ItemSaude(
        "aviso",
        "Cadastro: atualizado em 10/10/2026 14:30, com avisos: Texto cortado em nome "
        "(255 caracteres) (3): 000, 001, 002.",
    )


def test_ha_quanto():
    assert ha_quanto(AGORA - timedelta(seconds=20), AGORA) == "agora há pouco"
    assert ha_quanto(AGORA - timedelta(minutes=5), AGORA) == "há 5 min"
    assert ha_quanto(AGORA - timedelta(hours=3), AGORA) == "há 3 h"
    assert ha_quanto(AGORA - timedelta(days=1), AGORA) == "ontem às 14:30"
    assert ha_quanto(AGORA - timedelta(days=3), AGORA) == "07/10 às 14:30"


def test_resumo_do_erro():
    previsto = "Estoque: o CSV não tem nenhum material; nada foi alterado."
    assert resumo_do_erro(previsto) == previsto
    assert resumo_do_erro("Falha inesperada: Locator.click: Timeout 30000ms exceeded.\nCall") == (
        "O SCPI demorou demais para responder e a importação parou."
    )
    assert (
        resumo_do_erro("Falha inesperada: KeyError 'x'") == "O robô parou por um erro inesperado."
    )


def test_situacao_falha_mantem_os_dados_da_ultima_carga_que_deu_certo():
    Importacao.objects.create(
        tipo="ESTOQUE",
        situacao="SUCESSO",
        linhas=1385,
        inicio=AGORA - timedelta(hours=2),
        fim=AGORA - timedelta(hours=2),
    )
    Importacao.objects.create(
        tipo="ESTOQUE", situacao="FALHA", erro="Estoque: deu errado.", inicio=AGORA, fim=AGORA
    )
    situacao = situacao_do_catalogo(AGORA)
    estoque = next(f for f in situacao.fontes if f.tipo == "ESTOQUE")
    assert (estoque.nivel, estoque.selo) == ("erro", "Falhou")
    assert estoque.resumo == "1.385 saldos" and estoque.ha_quanto == "há 2 h"
    assert estoque.complemento == "" and estoque.resumo_completo == "1.385 saldos"
    assert estoque.erro == "Estoque: deu errado."
    assert situacao.resumo == "Precisa de atenção: Cadastro, Estoque e Saídas do SCPI."


def test_situacao_em_andamento(trava_importacao_ocupada):
    trava_importacao_ocupada("SAIDAS")
    Importacao.objects.create(tipo="SAIDAS", inicio=AGORA - timedelta(minutes=10))
    situacao = situacao_do_catalogo(AGORA)
    assert situacao.em_andamento.rotulo == "Saídas do SCPI"
    assert situacao.resumo == "Saídas do SCPI: importação em andamento desde 14:20."

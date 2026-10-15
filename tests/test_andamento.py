"""Apresentação de uma execução do robô (`pedidos/andamento.py`): funções puras, sem banco."""

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from pedidos.andamento import (
    contadores,
    duracao,
    explicar_falha,
    feitas,
    frase,
    momento,
    n_de_m,
    precisa_conferir,
)
from pedidos.models import ExecucaoRobo
from scpi.lancamento import LANCAMENTO_BLOQUEADO

# 14/10/2026 13:25 no horário de Brasília (UTC-3).
AGORA = timezone.make_aware(datetime(2026, 10, 14, 13, 25))


def execucao(**campos):
    campos.setdefault("inicio", AGORA)
    return ExecucaoRobo(**campos)


def test_feitas_conta_simuladas_na_simulacao_e_lancadas_no_real():
    resumo = {"requisicoes": 3, "simuladas": 3, "lancadas": 1}
    assert feitas(execucao(simulacao=True, resumo=resumo)) == 3
    assert feitas(execucao(simulacao=False, resumo=resumo)) == 1
    assert feitas(execucao(simulacao=True, resumo={})) == 0


def test_n_de_m():
    simulada = execucao(simulacao=True, resumo={"requisicoes": 3, "simuladas": 3})
    assert n_de_m(simulada) == "3 de 3 requisições"
    assert n_de_m(execucao(resumo={"requisicoes": 3, "lancadas": 2})) == "2 de 3 requisições"
    assert n_de_m(execucao(resumo={"requisicoes": 1, "lancadas": 1})) == "1 de 1 requisição"


def test_n_de_m_nunca_mostra_zero_de_zero():
    assert n_de_m(execucao(resumo={})) is None
    assert n_de_m(execucao(resumo={"requisicoes": 0, "ignoradas": 2})) is None


def test_duracao():
    assert duracao(AGORA, None) == "—"
    assert duracao(AGORA, AGORA + timedelta(seconds=45)) == "45 s"
    assert duracao(AGORA, AGORA + timedelta(minutes=2, seconds=5)) == "2 min 5 s"
    assert duracao(AGORA, AGORA + timedelta(minutes=2)) == "2 min"
    assert duracao(AGORA, AGORA + timedelta(hours=1, minutes=3, seconds=20)) == "1 h 3 min"
    assert duracao(AGORA, AGORA) == "0 s"


def test_momento_em_hora_local():
    assert momento(AGORA, AGORA) == "hoje, 13:25"
    assert momento(AGORA - timedelta(days=1), AGORA) == "ontem, 13:25"
    assert momento(AGORA - timedelta(days=7), AGORA) == "07/10, 13:25"


def test_momento_usa_o_dia_local_e_nao_o_utc():
    # 22:30 de 13/10 em Brasília já é 01:30 de 14/10 em UTC: continua sendo "ontem".
    noite = timezone.make_aware(datetime(2026, 10, 13, 22, 30))
    assert momento(noite, AGORA) == "ontem, 22:30"


def falha(simulacao=True, erro="Falha inesperada: boom", log="10:00 → (1/3)\n", **resumo):
    return execucao(
        simulacao=simulacao, situacao="FALHA", fim=AGORA, erro=erro, log=log, resumo=resumo
    )


def test_sem_falha_nao_ha_explicacao():
    assert explicar_falha(execucao(situacao="SUCESSO")) is None


@pytest.mark.parametrize("erro", [LANCAMENTO_BLOQUEADO, "Outro lançamento já está em andamento."])
def test_erro_conhecido_vem_como_esta(erro):
    f = explicar_falha(falha(erro=erro, log=""))
    assert f.frase == erro and not f.tecnico


def test_falha_inesperada_vira_erro_do_sistema_com_detalhe_tecnico():
    f = explicar_falha(
        falha(
            erro="Falha inesperada: You cannot call this from an async context",
            requisicoes=3,
            processadas=1,
        )
    )
    assert f.frase == "O robô parou por um erro do sistema." and f.tecnico
    assert f.ate_onde == "Chegou a processar 1 de 3 requisições."


def test_timeout_vira_demora_do_scpi():
    f = explicar_falha(falha(erro="Falha inesperada: Timeout 30000ms exceeded.\nCall log: …"))
    assert f.frase == "O SCPI demorou demais para responder e o robô parou." and f.tecnico


def test_processo_que_nao_subiu_nao_chegou_a_iniciar():
    f = explicar_falha(falha(erro="[WinError 2] O sistema não pode encontrar o arquivo", log=""))
    assert f.frase == "O robô não chegou a iniciar." and f.tecnico
    assert f.ate_onde == "Parou antes de começar."


def test_frase_de_uma_linha_vem_como_esta_e_varias_linhas_sao_tecnicas():
    assert not explicar_falha(falha(erro="não foi possível travar o lote P-000001: x.")).tecnico
    f = explicar_falha(falha(erro="primeira linha\nsegunda linha"))
    assert f.frase == "primeira linha\nsegunda linha" and f.tecnico


def test_ate_onde_sem_total_parou_antes_de_comecar():
    assert explicar_falha(falha(requisicoes=0)).ate_onde == "Parou antes de começar."
    assert explicar_falha(falha(requisicoes=1, processadas=1)).ate_onde == (
        "Chegou a processar 1 de 1 requisição."
    )


def test_proximo_passo_depende_do_modo():
    simulacao = explicar_falha(falha(simulacao=True))
    assert "Nenhuma linha mudou de estado." in simulacao.proximo_passo
    assert "simular de novo" in simulacao.proximo_passo and simulacao.simular_de_novo
    real = explicar_falha(falha(simulacao=False))
    assert real.proximo_passo == "Confira as travas abaixo antes de lançar de novo."
    assert not real.simular_de_novo


def test_contadores_so_os_diferentes_de_zero_com_plural():
    assert contadores({}, simulacao=True) == []
    assert contadores({"requisicoes": 3, "processadas": 3, "simuladas": 3}, simulacao=True) == [
        "3 simuladas"
    ]
    assert contadores(
        {"requisicoes": 2, "lancadas": 1, "verificar": 1, "falhas": 2, "ignoradas": 1},
        simulacao=False,
    ) == ["1 lançada", "2 com erro", "1 para verificar", "1 deixada de fora"]


def test_precisa_conferir():
    assert precisa_conferir(execucao(resumo={"verificar": 1}))
    assert precisa_conferir(execucao(resumo={"falhas": 1}))
    assert precisa_conferir(falha(simulacao=False))
    assert not precisa_conferir(falha(simulacao=True))
    assert not precisa_conferir(execucao(situacao="SUCESSO", resumo={"lancadas": 2}))


def test_frase_concluida_e_com_pendencias():
    simulacao = execucao(
        simulacao=True, situacao="SUCESSO", fim=AGORA, resumo={"requisicoes": 3, "simuladas": 3}
    )
    assert frase(simulacao, AGORA, False) == (
        "Simulação de hoje, 13:25, concluída: 3 de 3 requisições preenchidas."
    )
    real = execucao(
        situacao="ATENCAO", fim=AGORA, resumo={"requisicoes": 2, "lancadas": 1, "verificar": 1}
    )
    assert frase(real, AGORA, False) == (
        "Lançamento de hoje, 13:25, concluído com pendências: 1 de 2 requisições lançadas."
    )
    uma = execucao(situacao="SUCESSO", fim=AGORA, resumo={"requisicoes": 1, "lancadas": 1})
    assert frase(uma, AGORA, False).endswith("1 de 1 requisição lançada.")


def test_frase_sem_nada_a_lancar():
    vazia = execucao(simulacao=True, situacao="SUCESSO", fim=AGORA, resumo={"requisicoes": 0})
    assert frase(vazia, AGORA, False) == "Simulação de hoje, 13:25, concluída: nada a lançar."


def test_frase_em_andamento():
    rodando = execucao(simulacao=True, resumo={"requisicoes": 5, "processadas": 1})
    assert frase(rodando, AGORA, False) == "Simulação em andamento: requisição 2 de 5."
    no_fim = execucao(resumo={"requisicoes": 5, "processadas": 5})
    assert frase(no_fim, AGORA, False) == "Lançamento em andamento: requisição 5 de 5."
    assert frase(execucao(resumo={}), AGORA, False) == (
        "Lançamento em andamento: preparando a fila."
    )


def test_frase_interrompida_e_falha():
    morta = execucao(simulacao=True, resumo={"requisicoes": 5, "processadas": 1})
    assert frase(morta, AGORA, True) == (
        "Simulação de hoje, 13:25, interrompida: o robô parou sem registrar o fim."
    )
    assert frase(falha(simulacao=False), AGORA, False) == "Lançamento de hoje, 13:25, falhou."

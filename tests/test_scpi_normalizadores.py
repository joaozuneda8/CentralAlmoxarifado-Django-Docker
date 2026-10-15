from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Error as PlaywrightError

from scpi.browser import abrir_sessao, interceptar_csv
from scpi.leitura import ErroImportacao
from scpi.normalizadores import registros_produtos, registros_saidas


def test_registro_de_produto_quebrado_em_linhas_e_recolado():
    texto = (
        "CADPRO;DISC1;DISCR1\r\n"
        "001.001.001;DETERGENTE;Detergente neutro,\r\n"
        "frasco de 500 ml\r\n"
        "800.004;LEGADO;\r\n"
    )
    assert registros_produtos(texto) == [
        "CADPRO;DISC1;DISCR1",
        "001.001.001;DETERGENTE;Detergente neutro, frasco de 500 ml",
        "800.004;LEGADO;",
    ]


def test_codigo_legado_com_hifen_inicia_registro():
    assert registros_produtos("CADPRO;X\n000.009.0-1;A\n")[1] == "000.009.0-1;A"


def test_registro_de_saida_recolado_e_cabecalho_preservado():
    texto = "GRUPO;ID_REQUI;OBS\n12/01/2026;2;linha um\nlinha dois\n13/01/2026;3;\n"
    assert registros_saidas(texto) == [
        "GRUPO;ID_REQUI;OBS",
        "12/01/2026;2;linha um linha dois",
        "13/01/2026;3;",
    ]


def test_sessao_sem_credenciais_nao_abre_o_navegador(settings):
    settings.SAEP_USER = ""
    settings.SAEP_PASS = ""
    with pytest.raises(ErroImportacao, match="SAEP_USER e SAEP_PASS"):
        abrir_sessao(None, Path("x"))


def test_sessao_valida_o_certificado_do_scpi(settings, tmp_path):
    """O SCPI tem certificado válido (Let's Encrypt): a validação TLS fica ligada, para um
    intermediário não capturar a senha nem adulterar o CSV."""
    settings.SAEP_USER = "usuario"
    settings.SAEP_PASS = "senha"
    playwright = MagicMock()
    abrir_sessao(playwright, tmp_path)
    opcoes = playwright.chromium.launch_persistent_context.call_args.kwargs
    assert opcoes.get("ignore_https_errors", False) is False
    assert opcoes["user_data_dir"] == str(tmp_path)


def test_scpi_sem_https_e_recusado_antes_de_abrir_o_navegador(settings, tmp_path):
    settings.SAEP_USER = "usuario"
    settings.SAEP_PASS = "senha"
    settings.SCPI_URL = "http://transparencia.saep.sp.gov.br:8445/scpi9/"
    playwright = MagicMock()
    with pytest.raises(ErroImportacao, match="SCPI_URL precisa começar com https://"):
        abrir_sessao(playwright, tmp_path)
    playwright.chromium.launch_persistent_context.assert_not_called()


def test_sessao_bloqueia_requisicoes_sem_https(settings, tmp_path):
    """Nem um redirecionamento para http leva a senha ou o CSV sem TLS."""
    settings.SAEP_USER = "usuario"
    settings.SAEP_PASS = "senha"
    playwright = MagicMock()
    context = playwright.chromium.launch_persistent_context.return_value
    context.pages = []
    ordem = []
    context.route.side_effect = lambda *args: ordem.append("bloqueio")
    context.new_page.return_value.goto.side_effect = lambda *a, **k: ordem.append("login")
    abrir_sessao(playwright, tmp_path)
    padrao, tratador = context.route.call_args.args
    assert padrao.match("http://exemplo/login") and not padrao.match("https://exemplo/")
    rota = MagicMock()
    tratador(rota)
    rota.abort.assert_called_once()
    assert ordem == ["bloqueio", "login"]


def test_falha_no_login_fecha_o_navegador(settings, tmp_path):
    settings.SAEP_USER = "usuario"
    settings.SAEP_PASS = "senha"
    playwright = MagicMock()
    context = playwright.chromium.launch_persistent_context.return_value
    context.pages = []
    context.new_page.return_value.goto.side_effect = RuntimeError("SCPI fora do ar")
    with pytest.raises(RuntimeError, match="SCPI fora do ar"):
        abrir_sessao(playwright, tmp_path)
    context.close.assert_called_once()


def _resposta(status=200, location=None, corpo=b""):
    resposta = MagicMock(status=status, headers={"location": location} if location else {})
    resposta.body.return_value = corpo
    return resposta


def _baixar_csv(url, respostas, tmp_path, settings):
    """Roda `interceptar_csv` com um Playwright falso: o clique em "CSV (Dados)" dispara a
    rota registrada com uma requisição para `url`; `route.fetch` devolve `respostas`."""
    settings.LOG_DIR = tmp_path
    page, frame, rota = MagicMock(), MagicMock(), MagicMock()
    rota.request.url = url
    rota.fetch.side_effect = respostas

    def avaliar(js):
        if "CSV (Dados)" in js:
            page.route.call_args.args[1](rota)

    frame.evaluate.side_effect = avaliar
    return interceptar_csv(page, frame, "teste"), rota


def test_csv_por_https_e_recebido(settings, tmp_path):
    corpo, rota = _baixar_csv(
        "https://scpi/relatorio.csv", [_resposta(corpo=b"CADPRO")], tmp_path, settings
    )
    assert corpo == b"CADPRO"
    assert rota.fetch.call_args.kwargs["max_redirects"] == 0
    # Devolvido à página, o CSV vira um download que fecha o navegador e a sessão se perde.
    rota.abort.assert_called_once()
    rota.fulfill.assert_not_called()


def test_csv_segue_redirecionamento_para_https(settings, tmp_path):
    respostas = [_resposta(302, "/outro.csv"), _resposta(corpo=b"ok")]
    corpo, rota = _baixar_csv("https://scpi/relatorio.csv", respostas, tmp_path, settings)
    assert corpo == b"ok"
    assert rota.fetch.call_args.kwargs["url"] == "https://scpi/outro.csv"


def test_csv_por_http_e_recusado_sem_buscar(settings, tmp_path):
    with pytest.raises(ErroImportacao, match="sem HTTPS"):
        _baixar_csv("http://scpi/relatorio.csv", [], tmp_path, settings)


def test_csv_redirecionado_para_http_e_recusado(settings, tmp_path):
    respostas = [_resposta(302, "http://scpi/relatorio.csv")]
    with pytest.raises(ErroImportacao, match="sem HTTPS"):
        _baixar_csv("https://scpi/relatorio.csv", respostas, tmp_path, settings)


def test_csv_recebido_vale_mesmo_se_o_scpi_fecha_o_navegador(settings, tmp_path):
    """O SCPI fecha a página logo depois de entregar o download: o CSV já guardado vale."""
    settings.LOG_DIR = tmp_path
    page, frame, rota = MagicMock(), MagicMock(), MagicMock()
    rota.request.url = "https://scpi/relatorio.csv"
    rota.fetch.return_value = _resposta(corpo=b"CADPRO")

    def esperar(ms):
        # a rota só roda durante as esperas; logo em seguida a página some
        if ms == 1000:
            page.route.call_args.args[1](rota)
            raise PlaywrightError("Target page, context or browser has been closed")

    page.wait_for_timeout.side_effect = esperar
    assert interceptar_csv(page, frame, "teste") == b"CADPRO"
    page.unroute.assert_not_called()


def test_navegador_fechado_sem_csv_e_erro_claro(settings, tmp_path):
    settings.LOG_DIR = tmp_path
    page, frame = MagicMock(), MagicMock()

    def esperar(ms):
        if ms == 1000:
            raise PlaywrightError("Target page, context or browser has been closed")

    page.wait_for_timeout.side_effect = esperar
    with pytest.raises(ErroImportacao, match="fechou o navegador antes de entregar o CSV"):
        interceptar_csv(page, frame, "teste")
    page.screenshot.assert_not_called()


def test_erro_do_playwright_com_a_pagina_aberta_nao_e_engolido(settings, tmp_path):
    settings.LOG_DIR = tmp_path
    page, frame = MagicMock(), MagicMock()
    page.is_closed.return_value = False

    def esperar(ms):
        if ms == 1000:
            raise PlaywrightError("outra falha")

    page.wait_for_timeout.side_effect = esperar
    with pytest.raises(PlaywrightError, match="outra falha"):
        interceptar_csv(page, frame, "teste")

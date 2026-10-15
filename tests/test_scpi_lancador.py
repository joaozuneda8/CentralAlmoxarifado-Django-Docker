def test_navegador_implementa_o_protocolo_do_lancamento():
    from scpi.lancador import NavegadorSCPI
    from scpi.lancamento import SCPI

    metodos = {n for n in vars(SCPI) if not n.startswith("_")}
    assert metodos <= set(dir(NavegadorSCPI))


def test_lancador_nao_importa_playwright_no_topo():
    import scpi.lancador

    assert "sync_playwright" not in vars(scpi.lancador)


def test_navegador_libera_o_orm_enquanto_esta_aberto(monkeypatch):
    # A API síncrona do Playwright mantém um laço asyncio na thread enquanto o navegador está
    # aberto, e o lançamento grava no banco nesse meio (SynchronousOnlyOperation).
    import os
    from contextlib import nullcontext

    import playwright.sync_api

    from scpi import lancador

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: nullcontext(object()))
    monkeypatch.setattr(lancador.NavegadorSCPI, "abrir", lambda self: None)
    monkeypatch.delenv("DJANGO_ALLOW_ASYNC_UNSAFE", raising=False)
    with lancador.navegador():
        assert os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] == "true"
    assert "DJANGO_ALLOW_ASYNC_UNSAFE" not in os.environ

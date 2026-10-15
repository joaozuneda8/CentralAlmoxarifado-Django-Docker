"""Sessão do Playwright no SCPI: login, módulo COMPRAS e captura do CSV.

Copiado de `saep/browser.py` do extrair-relatorio (commit
cce15aa3706be09bf1cdb2b6c8768b2ab9a4a622). A navegação é a mesma; mudam só a origem das
credenciais e da URL (settings), o ano do exercício (o corrente, não fixo), a pasta do perfil
(uma por tipo de importação), o destino do screenshot de depuração (pasta de logs) e a
validação do certificado, que passa a valer.
"""

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone

from scpi.leitura import ErroImportacao

HTTP_SEM_TLS = re.compile(r"^http://", re.IGNORECASE)
REDIRECIONAMENTOS = (301, 302, 303, 307, 308)
MAX_REDIRECIONAMENTOS = 5

# Django recusa o ORM quando vê um laço asyncio rodando na thread, e a API síncrona do
# Playwright mantém um enquanto o navegador está aberto. Aqui nada roda em paralelo nesse laço (o
# Playwright executa tudo em sequência, na mesma thread), então a checagem é desligada só
# enquanto o navegador existe, que é quando as gravações acontecem com ele aberto.
LIBERA_ORM = "DJANGO_ALLOW_ASYNC_UNSAFE"


@contextmanager
def orm_liberado() -> Iterator[None]:
    """Liga `DJANGO_ALLOW_ASYNC_UNSAFE` dentro do bloco e o devolve ao que era no fim."""
    antes = os.environ.get(LIBERA_ORM)
    os.environ[LIBERA_ORM] = "true"
    try:
        yield
    finally:
        if antes is None:
            os.environ.pop(LIBERA_ORM, None)
        else:
            os.environ[LIBERA_ORM] = antes


JS_SALVAR_ARQUIVO = """
    const links = [...document.querySelectorAll('a')];
    const salvar = links.find(el => el.textContent.includes('Salvar Arquivo'));
    if (salvar) salvar.click();
"""

JS_CSV_DADOS = """
    const items = [...document.querySelectorAll('a[role="menuitem"]')];
    const csv = items.find(el => el.textContent.includes('CSV (Dados)'));
    if (csv) csv.click();
"""


def abrir_sessao(playwright, perfil: Path):
    """Abre contexto persistente e faz login. Retorna (context, page)."""
    usuario = settings.SAEP_USER
    senha = settings.SAEP_PASS
    if not usuario or not senha:
        raise ErroImportacao("Defina SAEP_USER e SAEP_PASS no .env.")
    if not settings.SCPI_URL.lower().startswith("https://"):
        raise ErroImportacao("SCPI_URL precisa começar com https://: a senha não sai sem TLS.")

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(perfil),
        headless=settings.SCPI_HEADLESS,
        # Sem ignore_https_errors (o original ignorava): o certificado do SCPI é válido e a
        # validação TLS protege a senha e o CSV baixado.
        accept_downloads=True,
        viewport=None,
        args=["--start-maximized"],
    )
    try:
        # Nenhuma requisição sem TLS, nem por redirecionamento ou ação de formulário.
        context.route(HTTP_SEM_TLS, lambda route: route.abort())
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(settings.SCPI_URL, wait_until="domcontentloaded")
        # Os campos são achados pelo que são, não pelo ID: o SCPI numera os IDs na ordem em que
        # monta a tela, e num perfil novo (sem cache) ele a monta mais devagar e com outra
        # numeração. Antes de preencher, espera a tela parar de ser redesenhada.
        usuario_input = page.get_by_placeholder("cpf, telefone / celular ou e-mail")
        usuario_input.wait_for(state="visible", timeout=60000)
        _esperar_tela_parada(page)
        usuario_input.fill(usuario)
        page.locator('input[type="password"]').filter(visible=True).fill(senha)
        # Os combos da tela são Município e Exercício, nessa ordem; o ano vem do perfil (ou 2014).
        ano = page.locator('input[role="combobox"]').filter(visible=True).last
        ano_id = ano.get_attribute("id") or ""
        page.locator(f"#{ano_id.replace('-inputEl', '-trigger-picker')}").click()
        ano.fill(str(timezone.localdate().year))
        page.get_by_role("button", name="Entrar").click()
    except BaseException:
        # Quem chama só fecha o contexto depois do login; aqui o perfil não pode ficar preso.
        context.close()
        raise

    return context, page


def _esperar_tela_parada(page) -> None:
    """Espera a rede sossegar (até 15 s: o SCPI pode manter pedidos abertos) e nenhuma máscara
    de carregamento à vista."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeout:
        pass
    page.wait_for_function(
        "!Array.from(document.querySelectorAll('.x-mask')).some(el => el.offsetParent !== null)",
        timeout=60000,
    )


def frame_compras(page):
    """Clica em COMPRAS e retorna o frame interno."""
    page.wait_for_function(
        "!Array.from(document.querySelectorAll('.x-mask')).some(el => el.offsetParent !== null)",
        timeout=60000,
    )
    page.get_by_text("COMPRAS", exact=True).click()
    iframe_el = page.locator('iframe[name^="name_URLCompras_"]').element_handle(timeout=60000)
    return iframe_el.content_frame()


def _buscar_https(route):
    """`route.fetch` seguindo redirecionamentos à mão, só por HTTPS.

    A rota do CSV tem precedência sobre o bloqueio de http do contexto, e o `fetch` seguiria
    sozinho um redirecionamento para http: cada destino é conferido antes de ser pedido.
    """
    url = route.request.url
    for _ in range(MAX_REDIRECIONAMENTOS + 1):
        if not url.lower().startswith("https://"):
            raise ErroImportacao(f"O SCPI mandou baixar o CSV sem HTTPS ({url}); recusado.")
        resp = route.fetch(url=url, max_redirects=0)
        if resp.status not in REDIRECIONAMENTOS:
            return resp
        url = urljoin(url, resp.headers.get("location", ""))
    raise ErroImportacao("O download do CSV passou por redirecionamentos demais; recusado.")


def interceptar_csv(page, frame, nome: str) -> bytes:
    """Clica 'Salvar Arquivo' → CSV (Dados) via intercept de rota. Retorna bytes do CSV."""
    from playwright.sync_api import Error as PlaywrightError

    csv_content: list[bytes] = []
    erros: list[ErroImportacao] = []

    def intercept(route):
        try:
            resp = _buscar_https(route)
        except ErroImportacao as exc:
            erros.append(exc)
            route.abort()
            return
        csv_content.append(resp.body())
        # O CSV já está guardado: o pedido é cancelado em vez de devolvido à página. Devolvido,
        # ele vira um download que fecha a página e o navegador do Playwright, e a sessão se perde.
        route.abort()

    page.route(re.compile(r"\.csv"), intercept)

    frame.evaluate(JS_SALVAR_ARQUIVO)

    page.wait_for_timeout(2000)

    frame.evaluate(JS_CSV_DADOS)

    fechada = False
    for _ in range(300):
        if csv_content or erros:
            break
        try:
            page.wait_for_timeout(1000)
        except PlaywrightError:
            # O SCPI fecha a página (e o navegador) logo depois de entregar o download; o que
            # importa é o CSV que a rota já guardou. Outro erro do Playwright segue adiante.
            if not page.is_closed():
                raise
            fechada = True
            break
    if not fechada:
        page.unroute(re.compile(r"\.csv"))

    if erros:
        raise erros[0]

    if not csv_content:
        if fechada:
            raise ErroImportacao("O SCPI fechou o navegador antes de entregar o CSV.")
        momento = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        debug_path = Path(settings.LOG_DIR) / f"scpi-{nome}-{momento}.png"
        page.screenshot(path=str(debug_path))
        raise ErroImportacao(f"Nenhum CSV recebido do SCPI. Tela salva em {debug_path}.")

    return csv_content[-1]

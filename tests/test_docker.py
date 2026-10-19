"""Imagem e compose da implantação (spec 2026-10-15-docker-design.md). Os testes leem o texto
dos arquivos: nenhum chama o docker."""

from pathlib import Path

import pytest
from waitress.adjustments import Adjustments

RAIZ = Path(__file__).resolve().parent.parent
DOCKERFILE = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = (RAIZ / "compose.yaml").read_text(encoding="utf-8")


def _trecho(nome: str) -> str:
    """O bloco do compose que começa na chave `nome` (de topo ou serviço, com recuo 0 ou 2) e
    vai até a próxima chave do mesmo nível."""
    linhas = COMPOSE.splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.split(":")[0] in (nome, f"  {nome}"))
    recuo = len(linhas[inicio]) - len(linhas[inicio].lstrip())
    fim = len(linhas)
    for i in range(inicio + 1, len(linhas)):
        linha = linhas[i]
        if linha.strip() and not linha.lstrip().startswith("#"):
            if len(linha) - len(linha.lstrip()) <= recuo:
                fim = i
                break
    return "\n".join(linhas[inicio:fim])


def test_imagem_python_313_sem_dependencias_de_dev_e_sem_root():
    assert "FROM python:3.13-slim-bookworm" in DOCKERFILE
    assert "uv sync --frozen --no-dev" in DOCKERFILE
    assert "collectstatic --noinput" in DOCKERFILE
    usuarios = [linha.split()[1] for linha in DOCKERFILE.splitlines() if linha.startswith("USER ")]
    assert usuarios and usuarios[-1] not in ("root", "0")


def test_imagem_no_fuso_de_sao_paulo():
    # Sem o fuso, o supercronic roda em UTC e o estoque cai das 04:00 às 14:00.
    assert "TZ=America/Sao_Paulo" in DOCKERFILE and "tzdata" in DOCKERFILE


def test_imagem_tem_chromium_cliente_do_banco_e_supercronic():
    assert "playwright install --with-deps chromium" in DOCKERFILE
    assert "mariadb-client" in DOCKERFILE and "supercronic" in DOCKERFILE
    assert "SUPERCRONIC_SHA1SUM" in DOCKERFILE and "sha1sum -c" in DOCKERFILE


def test_imagem_sem_env_nem_dados_locais():
    ignorados = (RAIZ / ".dockerignore").read_text(encoding="utf-8").split()
    for caminho in (".env*", ".venv", ".git", "logs", "dados", ".pw-profile", "staticfiles"):
        assert caminho in ignorados, caminho


def test_banco_sem_porta_publicada():
    assert "ports:" not in _trecho("banco")


def test_banco_com_nome_padrao_quando_db_name_vazio():
    assert "MARIADB_DATABASE: ${DB_NAME:-almoxarifado}" in _trecho("banco")


def test_web_publica_so_a_porta_configurada_com_o_prefixo_do_env():
    web = _trecho("web")
    assert "${PORTA_PUBLICADA:-127.0.0.1:8010}:8010" in web
    assert "--url-prefix=${PREFIXO_URL:-}" in web
    assert "--trusted-proxy=*" in web
    assert "--trusted-proxy-headers=x-forwarded-proto x-forwarded-for" in web


def test_waitress_aceita_o_prefixo_vazio_e_os_cabecalhos_do_compose():
    # PREFIXO_URL vazio (site na raiz) vira --url-prefix= e não pode quebrar a partida.
    opcoes, _ = Adjustments.parse_args(
        [
            "--url-prefix=",
            "--trusted-proxy=*",
            "--trusted-proxy-headers=x-forwarded-proto x-forwarded-for",
        ]
    )
    opcoes = {k: v for k, v in opcoes.items() if k not in ("help", "call")}
    ajustes = Adjustments(**opcoes)
    assert ajustes.url_prefix == ""
    assert ajustes.trusted_proxy_headers == {"x-forwarded-proto", "x-forwarded-for"}


def test_compose_forca_os_caminhos_e_o_banco_do_container():
    comum = _trecho("x-aplicacao")
    for par in (
        "DB_HOST: banco",
        'DB_PORT: "3306"',
        'SCPI_HEADLESS: "1"',
        "MYSQLDUMP: mariadb-dump",
        "LOG_DIR: /dados/logs",
        "BACKUP_DIR: /dados/backups",
        "SCPI_PERFIL_DIR: /dados/perfil",
    ):
        assert par in comum, par
    for servico in ("web", "agendador"):
        assert "<<: *aplicacao" in _trecho(servico), servico


@pytest.mark.parametrize("servico", ["web", "agendador"])
def test_logs_e_perfil_comuns_aos_dois_servicos(servico):
    trecho = _trecho(servico)
    assert "./dados/logs:/dados/logs" in trecho
    assert "perfil-navegador:/dados/perfil" in trecho


def test_backups_no_agendador_e_importacao_so_leitura_no_web():
    assert "./dados/backups:/dados/backups" in _trecho("agendador")
    assert "./dados/importacao:/dados/importacao:ro" in _trecho("web")


def test_agendador_roda_o_crontab():
    assert "supercronic /app/deploy/crontab" in _trecho("agendador")


def test_env_example_avisa_do_cifrao_nas_senhas():
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert "PORTA_PUBLICADA=127.0.0.1:8010" in exemplo
    assert "MARIADB_ROOT_PASSWORD=" not in exemplo
    assert "$" in exemplo and "aspas simples" in exemplo


def _variaveis_env_example() -> set[str]:
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    return {
        linha.split("=", 1)[0]
        for linha in texto.splitlines()
        if "=" in linha and not linha.startswith("#")
    }


def _variaveis_env_dockerfile() -> set[str]:
    """Os nomes definidos por ENV no Dockerfile (inclusive nas linhas de continuação)."""
    nomes = set()
    dentro = False
    for linha in DOCKERFILE.splitlines():
        if linha.startswith("ENV "):
            dentro = True
            linha = linha[4:]
        if dentro:
            for parte in linha.replace("\\", " ").split():
                if "=" in parte:
                    nomes.add(parte.split("=", 1)[0])
            dentro = linha.rstrip().endswith("\\")
    return nomes


def test_env_vazio_nao_apaga_o_env_da_imagem():
    # O env_file passa "NOME=" vazio ao container, por cima do ENV da imagem: toda variável que
    # a imagem define e o .env.example também traz precisa ser forçada no compose.
    comum = _trecho("x-aplicacao")
    for nome in _variaveis_env_dockerfile() & _variaveis_env_example():
        assert f"{nome}: " in comum, nome


def test_compose_forca_o_chromium_da_imagem():
    assert "PLAYWRIGHT_BROWSERS_PATH: /ms-playwright" in _trecho("x-aplicacao")


def test_backup_manual_pelo_web_tambem_vai_para_o_host():
    # "docker compose exec web python manage.py backup_banco" gravaria dentro do container.
    assert "./dados/backups:/dados/backups" in _trecho("web")


def test_senha_do_root_so_no_env_do_banco():
    # O env_file .env vai inteiro ao web (exposto à internet): a senha do root fica num arquivo
    # só do banco.
    assert "env_file: .env.banco" in _trecho("banco")
    assert "MARIADB_ROOT_PASSWORD" not in COMPOSE
    assert "env_file: .env.banco" not in _trecho("x-aplicacao")
    exemplo = (RAIZ / ".env.banco.example").read_text(encoding="utf-8")
    assert "MARIADB_ROOT_PASSWORD=" in exemplo
    assert ".env.banco" in (RAIZ / ".gitignore").read_text(encoding="utf-8").split()


def test_comentario_do_init_nao_atribui_os_robos_ao_tini():
    comum = _trecho("x-aplicacao")
    assert "init: true" in comum
    assert "subprocess" in comum and "O tini recolhe os processos dos robôs" not in comum


def test_dockerignore_exclui_todo_env_menos_o_exemplo():
    linhas = (RAIZ / ".dockerignore").read_text(encoding="utf-8").split()
    assert ".env*" in linhas and "!.env.example" in linhas
    assert linhas.index(".env*") < linhas.index("!.env.example")

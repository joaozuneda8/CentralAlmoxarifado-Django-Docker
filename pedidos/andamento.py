"""Uma `ExecucaoRobo` em texto de tela: frase, contadores, duração, "N de M" e a falha explicada.

Funções puras: recebem a execução (ou só os campos que usam) e o momento atual, nunca consultam
o banco. O `resumo` pode estar vazio (`{}`) quando a execução falhou antes de começar, por isso
toda leitura dele passa por `_num`.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from catalogo.saude import PREFIXO_FALHA_INESPERADA
from scpi.lancamento import LANCAMENTO_BLOQUEADO


def _num(resumo: dict, chave: str) -> int:
    return int(resumo.get(chave) or 0)


def feitas(execucao) -> int:
    """Requisições que a execução fez: simuladas na simulação, lançadas no lançamento real."""
    return _num(execucao.resumo or {}, "simuladas" if execucao.simulacao else "lancadas")


def n_de_m(execucao) -> str | None:
    """Requisições feitas do total, "3 de 3 requisições"; None sem total (falhou antes de
    começar ou não havia nada), nunca "0 de 0"."""
    total = _num(execucao.resumo or {}, "requisicoes")
    if not total:
        return None
    return f"{feitas(execucao)} de {total} {_requisicoes(total)}"


def duracao(inicio: datetime, fim: datetime | None) -> str:
    """Duração curta: "45 s", "2 min 5 s", "1 h 3 min"; "—" sem fim."""
    if fim is None:
        return "—"
    segundos = max(int((fim - inicio).total_seconds()), 0)
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas} h {minutos} min" if minutos else f"{horas} h"
    if minutos:
        return f"{minutos} min {segundos} s" if segundos else f"{minutos} min"
    return f"{segundos} s"


def momento(inicio: datetime, agora: datetime) -> str:
    """Quando começou, no horário local: "hoje, 13:25", "ontem, 13:25" ou "07/10, 13:25"."""
    local = timezone.localtime(inicio)
    hoje = timezone.localtime(agora).date()
    hora = local.strftime("%H:%M")
    if local.date() == hoje:
        return f"hoje, {hora}"
    if local.date() == hoje - timedelta(days=1):
        return f"ontem, {hora}"
    return f"{local.strftime('%d/%m')}, {hora}"


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _requisicoes(n: int) -> str:
    return "requisição" if n == 1 else "requisições"


def _cabeca(execucao, agora: datetime) -> str:
    """Modo e momento: "Simulação de hoje, 13:25" ou "Lançamento de hoje, 13:25"."""
    modo = "Simulação" if execucao.simulacao else "Lançamento"
    return f"{modo} de {momento(execucao.inicio, agora)}"


def _feminino(execucao, palavra: str) -> str:
    """Concorda com o modo: simulação é feminino ("concluída"), lançamento é masculino."""
    return palavra + ("a" if execucao.simulacao else "o")


def contadores(resumo: dict, simulacao: bool) -> list[str]:
    """Os contadores da execução diferentes de zero, já com o rótulo: "3 simuladas"."""
    resumo = resumo or {}
    feitas_ = (
        ("simuladas", "simulada", "simuladas") if simulacao else ("lancadas", "lançada", "lançadas")
    )
    itens = [
        feitas_,
        ("falhas", "com erro", "com erro"),
        ("verificar", "para verificar", "para verificar"),
        ("ignoradas", "deixada de fora", "deixadas de fora"),
    ]
    return [
        _plural(_num(resumo, chave), um, varios)
        for chave, um, varios in itens
        if _num(resumo, chave)
    ]


def precisa_conferir(execucao) -> bool:
    """Se a execução deixou algo nas travas: lote com erro ou para verificar, ou um lançamento
    real que falhou (a simulação não muda nenhuma linha)."""
    resumo = execucao.resumo or {}
    if _num(resumo, "falhas") or _num(resumo, "verificar"):
        return True
    return execucao.situacao == execucao.Situacao.FALHA and not execucao.simulacao


def frase(execucao, agora: datetime, interrompida: bool) -> str:
    """A execução numa frase: modo, momento, situação e "N de M requisições"."""
    resumo = execucao.resumo or {}
    total = _num(resumo, "requisicoes")
    Situacao = execucao.Situacao
    if execucao.situacao == Situacao.ANDAMENTO and not interrompida:
        modo = "Simulação" if execucao.simulacao else "Lançamento"
        if not total:
            return f"{modo} em andamento: preparando a fila."
        atual = min(_num(resumo, "processadas") + 1, total)
        return f"{modo} em andamento: requisição {atual} de {total}."
    cabeca = _cabeca(execucao, agora)
    if interrompida:
        return f"{cabeca}, {_feminino(execucao, 'interrompid')}: o robô parou sem registrar o fim."
    if execucao.situacao == Situacao.FALHA:
        return f"{cabeca}, falhou."
    situacao = _feminino(execucao, "concluíd")
    if execucao.situacao == Situacao.ATENCAO:
        situacao += " com pendências"
    if not total:
        return f"{cabeca}, {situacao}: nada a lançar."
    feito = "preenchida" if execucao.simulacao else "lançada"
    feito += "" if total == 1 else "s"
    return f"{cabeca}, {situacao}: {feitas(execucao)} de {total} {_requisicoes(total)} {feito}."


@dataclass(frozen=True)
class Falha:
    frase: str  # o que aconteceu, em português
    ate_onde: str
    proximo_passo: str
    tecnico: bool  # se há "Detalhe técnico" (o erro original e o registro) a mostrar
    simular_de_novo: bool


ERROS_CONHECIDOS = (LANCAMENTO_BLOQUEADO, "Outro lançamento já está em andamento.")


def _o_que_aconteceu(execucao) -> tuple[str, bool]:
    erro = (execucao.erro or "").strip()
    if erro in ERROS_CONHECIDOS:
        return erro, False
    if erro.startswith(PREFIXO_FALHA_INESPERADA):
        primeira = erro.removeprefix(PREFIXO_FALHA_INESPERADA).strip().splitlines()[0:1]
        if primeira and "Timeout" in primeira[0]:
            return "O SCPI demorou demais para responder e o robô parou.", True
        return "O robô parou por um erro do sistema.", True
    if not (execucao.log or "").strip() and not execucao.resumo:
        # O disparo não conseguiu iniciar o processo e gravou a exceção como veio.
        return "O robô não chegou a iniciar.", True
    return erro, "\n" in erro


def explicar_falha(execucao) -> Falha | None:
    """A falha em português: o que aconteceu, até onde chegou e o próximo passo. O texto gravado
    pelo robô não muda; o técnico fica para o "Detalhe técnico"."""
    if execucao.situacao != execucao.Situacao.FALHA:
        return None
    o_que, tecnico = _o_que_aconteceu(execucao)
    resumo = execucao.resumo or {}
    total = _num(resumo, "requisicoes")
    if total:
        ate_onde = (
            f"Chegou a processar {_num(resumo, 'processadas')} de {total} {_requisicoes(total)}."
        )
    else:
        ate_onde = "Parou antes de começar."
    if execucao.simulacao:
        proximo = (
            "Nenhuma linha mudou de estado. Pode simular de novo; se o erro se repetir, avise "
            "quem cuida do sistema."
        )
    else:
        proximo = "Confira as travas abaixo antes de lançar de novo."
    return Falha(o_que, ate_onde, proximo, tecnico, simular_de_novo=execucao.simulacao)

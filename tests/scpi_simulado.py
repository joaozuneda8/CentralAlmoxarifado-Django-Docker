"""SCPI simulado para os testes do lançamento (sem pytest, reaproveitado pelo comando).

Cumpre o protocolo `scpi.lancamento.SCPI` sem navegador: registra as chamadas em
`chamadas`, falha quando pedido (por lote) e numera as requisições salvas em sequência.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager


class SCPISimulado:
    def __init__(self):
        self.falhas_preencher: dict[str, Exception] = {}
        self.falhas_salvar: dict[str, Exception] = {}
        self.ao_salvar: Callable | None = None
        self.chamadas: list[tuple[str, str]] = []
        self.abertas = 0
        self._lote = ""  # último lote preenchido (o formulário aberto)
        self._salvas = 0

    @contextmanager
    def abrir(self) -> Iterator["SCPISimulado"]:
        self.abertas += 1
        yield self

    def preencher(self, req) -> None:
        self._lote = req.lote
        self.chamadas.append(("preencher", req.lote))
        if req.lote in self.falhas_preencher:
            raise self.falhas_preencher[req.lote]

    def salvar(self) -> str:
        self.chamadas.append(("salvar", self._lote))
        if self._lote in self.falhas_salvar:
            raise self.falhas_salvar[self._lote]
        self._salvas += 1
        if self.ao_salvar is not None:
            self.ao_salvar()
        return f"{self._salvas:06d}/26"

    def depois_de_salvar(self) -> None:
        self.chamadas.append(("depois_de_salvar", self._lote))

    def encerrar_simulacao(self) -> None:
        self.chamadas.append(("simulacao", self._lote))

    def descartar(self, lote: str) -> None:
        self.chamadas.append(("descartar", lote))

    def reiniciar(self) -> None:
        self.chamadas.append(("reiniciar", ""))

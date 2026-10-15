"""Conversão das abas da planilha do Apps Script em registros do Django (sem salvar nada).

`converter` recebe as linhas lidas por `planilha.ler_xlsx` e devolve uma `Carga`: instâncias
ainda não gravadas, com as chaves estrangeiras apontando para os objetos da própria carga, mais
os erros (que impedem a importação) e os avisos (só informam). Quem grava (Task 4) preenche
`atendido_por` e `registrado_por`.
"""

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import models
from django.utils.text import capfirst

from catalogo.models import CentroCusto, ItemLimpeza, Opcao
from implantacao.planilha import Linha, data_celula, momento_celula, qtd_celula, texto_celula
from pedidos import regras
from pedidos.models import Atendimento, ItemPedido, LinhaSaida, Pedido

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_NUMERO = re.compile(r"^(P|AV)-([0-9]+)$")

# Prefixos do "Status SCPI" (após `norm_u`) que o robô antigo escrevia.
_PREFIXOS_STATUS = (
    ("VERIFICAR", regras.VERIFICAR),
    ("EM LANCAMENTO", regras.EM_LANCAMENTO),
    ("ERRO", regras.ERRO),
    ("LANCADA", regras.LANCADA),
)

# Coluna da aba `Listas` → lista de `Opcao`, na ordem em que entram na carga.
_LISTAS = (
    ("Tipos de saída", Opcao.Lista.TIPO_SAIDA),
    ("Grupos ocultos (AB)", Opcao.Lista.GRUPO_OCULTO_AB),
    ("Categorias (limpeza)", Opcao.Lista.CATEGORIA_LIMPEZA),
    ("Funcionários", Opcao.Lista.FUNCIONARIO),
)


@dataclass
class Carga:
    pedidos: list[Pedido] = field(default_factory=list)
    itens: list[ItemPedido] = field(default_factory=list)
    atendimentos: list[Atendimento] = field(default_factory=list)
    linhas: list[LinhaSaida] = field(default_factory=list)
    centros: list[CentroCusto] = field(default_factory=list)
    opcoes: list[Opcao] = field(default_factory=list)
    # (código, categoria, nome exibido, unidade exibida, ordem dentro da categoria)
    itens_limpeza: list[tuple[str, str, str, str, int]] = field(default_factory=list)
    ultimo_numero: int = 0
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass
class _Indice:
    """O que as abas seguintes precisam saber dos pedidos já convertidos."""

    por_id: dict[str, Pedido] = field(default_factory=dict)
    por_numero: dict[str, Pedido] = field(default_factory=dict)
    atendimento_do_numero: dict[str, Atendimento] = field(default_factory=dict)
    linha_do_pedido: dict[str, int] = field(default_factory=dict)
    # IDs e números das linhas de Pedidos recusadas: o erro já está listado, e os itens e as
    # saídas delas não ganham outro (que apontaria a causa errada).
    recusados: set[str] = field(default_factory=set)


def status_da_planilha(status: str, requisicao: str, obs: str) -> str | None:
    """Status da `LinhaSaida` a partir de Requisição, Observações e Status SCPI (`None` = o
    texto do status é desconhecido). Na dúvida a linha fica travada, nunca `PENDENTE`."""
    if requisicao:
        return regras.LANCADA
    if regras.marcado_nao_lancar(obs):
        return regras.NAO_LANCAR
    texto = regras.norm_u(status)
    if not texto:
        return regras.PENDENTE
    for prefixo, resultado in _PREFIXOS_STATUS:
        if texto.startswith(prefixo):
            return resultado
    return None


def _msg(aba: str, linha: Linha, texto: str) -> str:
    return f"{aba}, linha {linha['_linha']}: {texto}"


def _excessos(registro: models.Model) -> list[str]:
    """Textos do registro que não cabem no campo do banco (um aviso por campo)."""
    achados = []
    for campo in registro._meta.concrete_fields:
        valor = getattr(registro, campo.attname)
        if isinstance(campo, models.CharField) and isinstance(valor, str):
            if len(valor) > campo.max_length:
                achados.append(
                    f"{capfirst(campo.verbose_name)} com {len(valor)} caracteres "
                    f"(máximo {campo.max_length})."
                )
    return achados


def _registrar_numero(carga: Carga, numero: str) -> None:
    if m := _NUMERO.match(numero):
        carga.ultimo_numero = max(carga.ultimo_numero, int(m.group(2)))


def _momento(valor: object):
    """Momento da célula, ou `None` se vazio ou ilegível."""
    try:
        return momento_celula(valor)
    except ValueError:
        return None


def _data(valor: object):
    try:
        return data_celula(valor)
    except ValueError:
        return None


def _converter_atendimento(
    linha: Linha, atendimento_id: str, criado_em, problemas: list[str], carga: Carga
) -> Atendimento | None:
    """Atendimento da linha de `Pedidos`; o que estiver errado entra em `problemas`."""
    data_efetiva = _data(linha.get("Data efetiva"))
    if data_efetiva is None:
        problemas.append("data efetiva inválida")
    try:
        atendido_em = momento_celula(linha.get("Atendido em")) or criado_em
    except ValueError:
        atendido_em = None
        problemas.append("data do atendimento inválida")
    if data_efetiva is None or atendido_em is None:
        return None
    obs = texto_celula(linha.get("Obs. da saída"))
    atendimento = Atendimento(
        id=uuid.UUID(atendimento_id),
        data_efetiva=data_efetiva,
        recebedor=texto_celula(linha.get("Recebedor")),
        centro_custo=texto_celula(linha.get("Centro de custo")),
        tipo_saida=texto_celula(linha.get("Tipo Saída")),
        placa=regras.norm_placa(texto_celula(linha.get("Placa"))),
        obs=obs,
        nao_lancar=regras.marcado_nao_lancar(obs),
        atendido_em=atendido_em,
    )
    problemas += _excessos(atendimento)
    try:
        atendimento.recibo_impresso_em = momento_celula(linha.get("Recibo impresso em"))
    except ValueError:
        carga.avisos.append(_msg("Pedidos", linha, "Recibo impresso em ilegível, ignorado"))
    return atendimento


def _converter_pedidos(linhas: list[Linha], carga: Carga, indice: _Indice) -> None:
    ids_vistos: dict[str, int] = {}
    numeros_vistos: dict[str, int] = {}
    atendimentos_vistos: dict[str, int] = {}
    for linha in linhas:
        id_texto = texto_celula(linha.get("ID")).lower()
        numero = texto_celula(linha.get("Nº"))
        if not id_texto:
            _registrar_numero(carga, numero)
            if numero:
                carga.avisos.append(_msg("Pedidos", linha, "linha sem ID ignorada"))
            continue
        problemas: list[str] = []
        id_valido = bool(_UUID.match(id_texto))
        if not id_valido:
            problemas.append("ID inválido")
        elif id_texto in ids_vistos:
            problemas.append(f"ID repetido (linha {ids_vistos[id_texto]})")
        else:
            ids_vistos[id_texto] = linha["_linha"]

        origem = texto_celula(linha.get("Origem"))
        if origem not in (regras.LIMPEZA, regras.AB, regras.AVULSA):
            problemas.append("origem inválida")
        if not _NUMERO.match(numero):
            problemas.append("número inválido")
        else:
            _registrar_numero(carga, numero)
            if numero in numeros_vistos:
                problemas.append(f"número repetido (linha {numeros_vistos[numero]})")
            else:
                numeros_vistos[numero] = linha["_linha"]
            origem_valida = origem in (regras.LIMPEZA, regras.AB, regras.AVULSA)
            if origem_valida and numero.startswith("AV-") != (origem == regras.AVULSA):
                problemas.append(f"o número {numero} não combina com a origem {origem}")

        criado_em = _momento(linha.get("Criado em"))
        if criado_em is None:
            problemas.append("data de criação inválida")

        atendimento_id = texto_celula(linha.get("Atendimento_ID")).lower()
        atendimento = None
        if atendimento_id and not _UUID.match(atendimento_id):
            problemas.append("ID do atendimento inválido")
        elif atendimento_id in atendimentos_vistos:
            problemas.append(
                f"ID do atendimento repetido (linha {atendimentos_vistos[atendimento_id]})."
            )
        elif atendimento_id:
            atendimentos_vistos[atendimento_id] = linha["_linha"]
            atendimento = _converter_atendimento(linha, atendimento_id, criado_em, problemas, carga)
        elif origem == regras.AVULSA:
            problemas.append("saída avulsa sem atendimento")

        pedido = Pedido(
            id=uuid.UUID(id_texto) if id_valido else None,
            numero=numero,
            origem=origem,
            criado_em=criado_em,
            solicitante=texto_celula(linha.get("Solicitante")),
            destino=texto_celula(linha.get("Destino")),
            obs=texto_celula(linha.get("Observação")),
        )
        problemas += _excessos(pedido)
        if problemas:
            carga.erros += [_msg("Pedidos", linha, p) for p in problemas]
            indice.recusados.update({id_texto, numero} - {""})
            continue
        carga.pedidos.append(pedido)
        indice.por_id[id_texto] = pedido
        indice.por_numero[numero] = pedido
        indice.linha_do_pedido[id_texto] = linha["_linha"]
        if atendimento is not None:
            atendimento.pedido = pedido
            carga.atendimentos.append(atendimento)
            indice.atendimento_do_numero[numero] = atendimento


def _qtd(valor: object) -> tuple[Decimal | None, bool]:
    """(quantidade, legível): vazio é legível e dá `None`."""
    try:
        return qtd_celula(valor), True
    except ValueError:
        return None, False


def _converter_itens(linhas: list[Linha], carga: Carga, indice: _Indice) -> None:
    com_itens: set[str] = set()
    vistos: set[tuple[str, str]] = set()
    for linha in linhas:
        numero = texto_celula(linha.get("Nº"))
        _registrar_numero(carga, numero)
        id_texto = texto_celula(linha.get("ID")).lower()
        pedido = indice.por_id.get(id_texto)
        if pedido is None and id_texto in indice.recusados:
            continue
        if pedido is None:
            carga.avisos.append(
                _msg(
                    "Itens", linha, "item sem pedido (gravação incompleta no Apps Script) ignorado"
                )
            )
            continue
        com_itens.add(id_texto)
        pedida, _ = _qtd(linha.get("Qtd pedida"))
        entregue, entregue_legivel = _qtd(linha.get("Qtd entregue"))
        if pedida is None:
            carga.erros.append(_msg("Itens", linha, "quantidade pedida inválida"))
        if not entregue_legivel:
            carga.erros.append(_msg("Itens", linha, "quantidade entregue inválida"))
        if pedida is None or not entregue_legivel:
            continue
        estoque, _ = _qtd(linha.get("Estoque no pedido"))
        codigo = texto_celula(linha.get("Código"))
        if (id_texto, codigo) in vistos:
            carga.erros.append(_msg("Itens", linha, f"código {codigo} repetido no pedido"))
            continue
        vistos.add((id_texto, codigo))
        item = ItemPedido(
            pedido=pedido,
            codigo=codigo,
            origem=ItemPedido.Origem.PEDIDO,
            material=texto_celula(linha.get("Material")),
            unidade=texto_celula(linha.get("Unidade")),
            categoria=texto_celula(linha.get("Categoria")),
            grupo=texto_celula(linha.get("Grupo")),
            subgrupo=texto_celula(linha.get("Subgrupo")),
            estoque_no_pedido=estoque,
            qtd_pedida=pedida,
            qtd_entregue=entregue,
        )
        if excessos := _excessos(item):
            carga.erros += [_msg("Itens", linha, e) for e in excessos]
            continue
        carga.itens.append(item)
    for id_texto, numero_linha in indice.linha_do_pedido.items():
        if id_texto not in com_itens:
            carga.avisos.append(f"Pedidos, linha {numero_linha}: pedido sem itens")


def _converter_saidas(linhas: list[Linha], carga: Carga, indice: _Indice) -> None:
    sequencia: dict[str, int] = {}
    for linha in linhas:
        origem_id = texto_celula(linha.get("Origem_ID"))
        _registrar_numero(carga, origem_id)
        texto_status = texto_celula(linha.get("Status SCPI"))
        requisicao = texto_celula(linha.get("Requisição"))
        obs = texto_celula(linha.get("Observações"))
        status = status_da_planilha(texto_status, requisicao, obs)
        if status is None:
            status = regras.VERIFICAR
            carga.avisos.append(
                _msg("Saídas", linha, f'status desconhecido "{texto_status}": linha travada')
            )

        atendimento = indice.atendimento_do_numero.get(origem_id)
        if atendimento is None and origem_id in indice.recusados:
            continue
        if atendimento is None:
            if status in (regras.LANCADA, regras.NAO_LANCAR):
                carga.avisos.append(_msg("Saídas", linha, "saída sem atendimento ignorada"))
            else:
                carga.erros.append(
                    _msg(
                        "Saídas",
                        linha,
                        "saída sem atendimento, que o robô lançaria: conclua a transferência "
                        "no Apps Script ou marque NÃO LANÇAR",
                    )
                )
            continue

        data = _data(linha.get("Data"))
        qtd, _ = _qtd(linha.get("Qtd"))
        if data is None:
            carga.erros.append(_msg("Saídas", linha, "data inválida"))
        if not qtd:
            carga.erros.append(_msg("Saídas", linha, "quantidade inválida"))
        lancado_em = None
        try:
            lancado_em = momento_celula(linha.get("Lançado SCPI em"))
        except ValueError:
            carga.avisos.append(_msg("Saídas", linha, "Lançado SCPI em ilegível, ignorado"))
        if data is None or not qtd:
            continue

        sequencia[origem_id] = sequencia.get(origem_id, 0) + 1
        saida = LinhaSaida(
            atendimento=atendimento,
            seq=sequencia[origem_id],
            data=data,
            qtd=qtd,
            codigo=texto_celula(linha.get("Código")),
            descricao=texto_celula(linha.get("Descrição do Material")),
            recebedor=texto_celula(linha.get("Recebimento")),
            centro_custo=texto_celula(linha.get("Centro de Custo")),
            tipo_saida=texto_celula(linha.get("Tipo Saída")),
            placa=regras.norm_placa(texto_celula(linha.get("Veículo (Placa)"))),
            obs=obs,
            lote=texto_celula(linha.get("Lote_SCPI")) or origem_id,
            status=status,
            requisicao_scpi=requisicao,
            lancado_em=lancado_em,
            mensagem=texto_status,
        )
        if excessos := _excessos(saida):
            carga.erros += [_msg("Saídas", linha, e) for e in excessos]
            continue
        carga.linhas.append(saida)


def _converter_centros(linhas: list[Linha], carga: Carga) -> None:
    placas: dict[str, int] = {}
    for linha in linhas:
        descricao = texto_celula(linha.get("DESCR"))
        codigo = texto_celula(linha.get("CODCCUSTO"))
        placa = regras.norm_placa(texto_celula(linha.get("PLACA")))
        if not (descricao or codigo or placa):
            continue
        problemas = []
        if not descricao:
            problemas.append("descrição vazia")
        if not codigo:
            problemas.append("código vazio")
        if placa:
            if placa in placas:
                problemas.append(f"a placa {placa} já está na linha {placas[placa]}")
            else:
                placas[placa] = linha["_linha"]
        centro = CentroCusto(descricao=descricao, codigo=codigo, placa=placa or None)
        problemas += _excessos(centro)
        if problemas:
            carga.erros += [_msg("Centros de Custo", linha, p) for p in problemas]
            continue
        carga.centros.append(centro)


def _converter_listas(linhas: list[Linha], carga: Carga) -> None:
    for coluna, lista in _LISTAS:
        vistos: set[str] = set()
        for linha in linhas:
            valor = texto_celula(linha.get(coluna))
            if not valor:
                continue
            if regras.norm_u(valor) in vistos:
                carga.avisos.append(_msg("Listas", linha, f'"{valor}" repetido em {coluna}'))
                continue
            opcao = Opcao(lista=lista, valor=valor, ordem=len(vistos), ativo=True)
            if excessos := _excessos(opcao):
                carga.erros += [_msg("Listas", linha, e) for e in excessos]
                continue
            vistos.add(regras.norm_u(valor))
            carga.opcoes.append(opcao)


def _converter_lista_limpeza(linhas: list[Linha], carga: Carga) -> None:
    categorias = {
        regras.norm_u(o.valor) for o in carga.opcoes if o.lista == Opcao.Lista.CATEGORIA_LIMPEZA
    }
    codigos: set[str] = set()
    ordem_na_categoria: dict[str, int] = {}
    for linha in linhas:
        codigo = texto_celula(linha.get("Código"))
        categoria = texto_celula(linha.get("Categoria"))
        if not codigo or not categoria:
            carga.avisos.append(_msg("Lista_Limpeza", linha, "código ou categoria vazio, ignorada"))
            continue
        if regras.norm_u(codigo) in codigos:
            carga.avisos.append(
                _msg("Lista_Limpeza", linha, f"código repetido ({codigo}), ignorada")
            )
            continue
        codigos.add(regras.norm_u(codigo))
        if regras.norm_u(categoria) not in categorias:
            carga.avisos.append(
                _msg(
                    "Lista_Limpeza",
                    linha,
                    f'a categoria "{categoria}" não está em "Categorias (limpeza)"',
                )
            )
        ordem = ordem_na_categoria.get(categoria, 0)
        ordem_na_categoria[categoria] = ordem + 1
        nome = texto_celula(linha.get("Nome exibido"))
        unidade = texto_celula(linha.get("Unidade exibida"))
        # Só para conferir os tamanhos: a gravação monta o `ItemLimpeza` de verdade, com o material.
        modelo = ItemLimpeza(categoria=categoria, nome_exibido=nome, unidade_exibida=unidade)
        if excessos := _excessos(modelo):
            carga.erros += [_msg("Lista_Limpeza", linha, e) for e in excessos]
            continue
        carga.itens_limpeza.append((codigo, categoria, nome, unidade, ordem))


def converter(abas: dict[str, list[Linha]]) -> Carga:
    carga = Carga()
    indice = _Indice()
    _converter_pedidos(abas["Pedidos"], carga, indice)
    _converter_itens(abas["Itens"], carga, indice)
    _converter_saidas(abas["Saídas"], carga, indice)
    _converter_centros(abas["Centros de Custo"], carga)
    _converter_listas(abas["Listas"], carga)
    _converter_lista_limpeza(abas["Lista_Limpeza"], carga)
    return carga

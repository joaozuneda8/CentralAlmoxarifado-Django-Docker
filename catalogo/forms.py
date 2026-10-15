"""Formulários dos robôs de importação (página Catálogo): execução avulsa com parâmetros."""

from dataclasses import dataclass

from django import forms
from django.utils import timezone

from catalogo.models import Importacao, Material
from scpi.gravacao import periodo_cadastro_padrao, periodo_saidas
from scpi.leitura import ErroImportacao

TAMANHO_MAXIMO_CSV = 25 * 1024 * 1024
ORIGENS = [("scpi", "Baixar do SCPI"), ("csv", "Enviar um CSV já baixado")]
MODOS = [("novos", "Só os novos"), ("completo", "Recarga completa")]


def _data():
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "campo-entrada"})


class RoboForm(forms.Form):
    """O que todo robô de importação aceita: baixar do SCPI ou usar um CSV enviado."""

    origem = forms.ChoiceField(
        label="Origem dos dados", choices=ORIGENS, initial="scpi", widget=forms.RadioSelect
    )
    arquivo = forms.FileField(
        label="Arquivo CSV",
        required=False,
        widget=forms.FileInput(attrs={"accept": ".csv,text/csv", "class": "campo-entrada"}),
    )

    def clean(self):
        dados = super().clean()
        if dados.get("origem") != "csv":
            dados["arquivo"] = None
            return dados
        arquivo = dados.get("arquivo")
        if "arquivo" in self.errors:
            pass  # o próprio campo já recusou (por exemplo, arquivo vazio)
        elif not arquivo:
            self.add_error("arquivo", "Escolha o arquivo CSV.")
        elif arquivo.size > TAMANHO_MAXIMO_CSV:
            self.add_error("arquivo", "O arquivo passa de 25 MB.")
        elif not arquivo.name.lower().endswith(".csv"):
            self.add_error("arquivo", "Envie um arquivo .csv.")
        return dados


class PeriodoForm(forms.Form):
    """Período de/até (cadastro e saídas): vazio usa o padrão do comando."""

    desde = forms.DateField(label="De", required=False, widget=_data())
    ate = forms.DateField(label="Até", required=False, widget=_data())

    def clean(self):
        dados = super().clean()
        hoje = timezone.localdate()
        desde, ate = dados.get("desde"), dados.get("ate")
        if desde and desde > hoje:
            self.add_error("desde", "O início do período não pode ser no futuro.")
        if ate and ate > hoje:
            self.add_error("ate", "O fim do período não pode ser no futuro.")
        if desde and ate and desde > ate and not self.errors:
            self.add_error("ate", "O fim do período é antes do início.")
        return dados


class RoboCadastroForm(RoboForm):
    """Cadastro: só os novos desde a última carga (padrão depois da primeira) ou a recarga
    completa. Sem carga anterior e com CSV enviado, só a completa vale; o período do comando
    (`--desde`/`--ate`) não aparece na tela."""

    modo = forms.ChoiceField(label="Modo", choices=MODOS, required=False, widget=forms.RadioSelect)
    forcar = forms.BooleanField(
        label="Aceitar que o cadastro fique bem menor (forçar)", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O período dos novos (veja `scpi.gravacao.periodo_cadastro_padrao`); None sem carga.
        self.padrao = periodo_cadastro_padrao(timezone.localdate())
        self.ultima_carga = (
            Importacao.objects.filter(
                tipo=Importacao.Tipo.CADASTRO, situacao=Importacao.Situacao.SUCESSO
            )
            .order_by("-inicio")
            .first()
        )
        # O "forçar" só tem o que fazer onde há material visível que a carga poderia ocultar.
        self.visiveis = Material.objects.filter(oculto=False).count()
        self.fields["modo"].initial = "novos" if self.padrao else "completo"

    def clean(self):
        dados = super().clean()
        modo = dados.get("modo") or ("novos" if self.padrao else "completo")
        if dados.get("origem") == "csv":
            modo = "completo"  # o CSV enviado é sempre o cadastro inteiro
        elif modo == "novos" and not self.padrao:
            self.add_error("modo", "Ainda não há carga de cadastro: faça a recarga completa.")
        dados["modo"] = modo
        dados["completo"] = modo == "completo"
        dados["forcar"] = bool(dados.get("forcar")) and dados["completo"] and self.visiveis > 0
        return dados


class RoboEstoqueForm(RoboForm):
    pass


class RoboSaidasForm(PeriodoForm, RoboForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O período que o comando usaria sozinho: 7 dias antes do fim da última importação
        # bem-sucedida (ou 1º de janeiro), até hoje. Preenche os campos e o "Usar o padrão".
        try:
            self.padrao_periodo = periodo_saidas(timezone.localdate())
        except ErroImportacao:
            self.padrao_periodo = None
        if not self.is_bound and self.padrao_periodo:
            self.initial["desde"], self.initial["ate"] = self.padrao_periodo


@dataclass(frozen=True)
class Robo:
    chave: str
    rotulo: str
    descricao: str
    formulario: type[RoboForm]
    botao: str  # o que o botão faz (no cadastro, com "só os novos"; troca na completa)

    def novo(self, *args, **kwargs) -> RoboForm:
        """O formulário com ids próprios (`id_<robô>_<campo>`): os três ficam na mesma página."""
        return self.formulario(*args, auto_id=f"id_{self.chave}_%s", **kwargs)


ROBOS = [
    Robo(
        "cadastro",
        "Cadastro",
        "Traz do SCPI os materiais cadastrados. Depois da primeira carga, o normal é trazer só os "
        "novos, sem ocultar nenhum material; a recarga completa atualiza tudo e oculta os "
        "materiais que sumiram do SCPI.",
        RoboCadastroForm,
        "Importar só os novos",
    ),
    Robo(
        "estoque",
        "Estoque",
        "Traz do SCPI o saldo de estoque de cada material.",
        RoboEstoqueForm,
        "Importar estoque",
    ),
    Robo(
        "saidas",
        "Saídas",
        "Traz do SCPI as saídas do período. Saídas já importadas não se repetem.",
        RoboSaidasForm,
        "Importar saídas do período",
    ),
]
ROBOS_POR_CHAVE = {robo.chave: robo for robo in ROBOS}

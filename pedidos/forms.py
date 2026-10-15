"""Formulário do lançamento no SCPI: o modo (vem do botão clicado, "Simular" ou "Lançar no SCPI")
e o limite de requisições."""

from django import forms
from django.conf import settings

from scpi.lancamento import LANCAMENTO_BLOQUEADO

MODOS = [("lancar", "Lançar no SCPI"), ("simular", "Simular (preenche e descarta, sem salvar)")]


class LancamentoForm(forms.Form):
    modo = forms.ChoiceField(label="Modo", choices=MODOS)
    limite = forms.IntegerField(
        label="Limite de requisições",
        required=False,
        min_value=1,
        max_value=10000,
        help_text="Deixe vazio para lançar todas. Use 1 nos primeiros testes.",
        widget=forms.NumberInput(attrs={"class": "campo-entrada", "min": 1}),
    )

    def clean_modo(self):
        modo = self.cleaned_data["modo"]
        if modo == "lancar" and not settings.LANCAMENTO_REAL:
            raise forms.ValidationError(LANCAMENTO_BLOQUEADO)
        return modo

    @classmethod
    def da_requisicao(cls, post):
        """Aceita também o formato antigo dos botões (`simulacao=1`, sem `modo`)."""
        dados = post.copy()
        if not dados.get("modo"):
            dados["modo"] = "simular" if dados.get("simulacao") else "lancar"
        return cls(dados)

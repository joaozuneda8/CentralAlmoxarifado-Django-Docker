from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm


class FormularioEntrada(AuthenticationForm):
    """Login por matrícula.

    A tradução pt-BR do Django interpola o rótulo do campo e produz "entre com um matrícula";
    a recusa aqui é uma frase própria e genérica, igual para senha errada, matrícula
    desconhecida e conta desativada.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Matrícula ou senha incorretas.",
        "inactive": "Matrícula ou senha incorretas.",
    }


class FormularioEntradaAdmin(AdminAuthenticationForm):
    """Login do admin, com a mesma recusa em português correto do `FormularioEntrada`."""

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": "Matrícula ou senha incorretas, ou a conta não tem acesso aos cadastros.",
        "inactive": "Matrícula ou senha incorretas, ou a conta não tem acesso aos cadastros.",
    }

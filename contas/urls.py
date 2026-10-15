from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from contas.forms import FormularioEntrada

# Sem `app_name`: `LOGIN_URL = "login"` e `LOGOUT_REDIRECT_URL = "login"` usam nomes globais.
urlpatterns = [
    path(
        "entrar/",
        LoginView.as_view(
            template_name="contas/entrar.html",
            authentication_form=FormularioEntrada,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("sair/", LogoutView.as_view(), name="logout"),
]

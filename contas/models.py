from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário da área do almoxarifado. Entra pela matrícula (guardada em `username`)."""

    username = models.CharField(
        "matrícula",
        max_length=30,
        unique=True,
        error_messages={"unique": "Já existe um usuário com esta matrícula."},
    )

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

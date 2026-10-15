"""App `interface`: apresentação compartilhada (CSS, JS, layouts, parciais e template tags).

Sem regra de domínio e sem modelos.
"""

from django.apps import AppConfig


class InterfaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "interface"

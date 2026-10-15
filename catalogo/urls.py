from django.urls import path

from catalogo import views

app_name = "catalogo"

urlpatterns = [
    path("curva/", views.curva, name="curva"),
]

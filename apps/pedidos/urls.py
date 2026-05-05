from django.urls import path
from .views import crear_pedido

urlpatterns = [
    path('api/crear-pedido/', crear_pedido),
]

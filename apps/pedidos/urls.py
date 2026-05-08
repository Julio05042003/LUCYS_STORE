from django.urls import path
from .views import *

urlpatterns = [
    path('api/crear-pedido/', crear_pedido),
    path('buscar-pedidos/', buscar_pedidos, name='buscar_pedidos'),
]

from django.urls import path
from .views import *

urlpatterns = [
    path('crear-pedido/', crear_pedido, name='crear_pedido'),
    path('buscar-pedidos/', buscar_pedidos, name='buscar_pedidos'),
]

from django.urls import path
from .views import *

urlpatterns = [

    path(
        '',
        pedidos,
        name='pedidos'
    ),

    path(
        'crear/',
        crear_pedido,
        name='crear_pedido'
    ),

    path(
        'buscar-clientes/',
        buscar_clientes,
        name='buscar_clientes'
    ),

    path(
        'buscar-productos/',
        buscar_productos_pedidos,
        name='buscar_productos_pedidos'
    ),
    
    path(
    'cambiar-estado/<int:pedido_id>/',
    cambiar_estado_pedido,
    name='cambiar_estado_pedido'
),
]
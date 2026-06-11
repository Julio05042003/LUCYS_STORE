from django.urls import path
from .views import *

urlpatterns = [

    path('', pedidos, name='pedidos'),
    path('crear/', crear_pedido, name='crear_pedido'),
    path('editar/<int:pedido_id>/', editar_y_actualizar_pedido, name='editar_actualizar_pedido'),
    path('pedidos/detalle/<int:pedido_id>/', detalle_pedido, name='detalle_pedido'),
    path('buscar-clientes/', buscar_clientes, name='buscar_clientes'),
    path('buscar-direcciones-cliente/', obtener_direcciones_cliente, name='Buscar_direcciones_cliente'),    
    path('buscar-productos/', buscar_productos_pedidos, name='buscar_productos_pedidos'),
    path('cambiar-estado/<int:pedido_id>/', cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('pedidos/<int:pedido_id>/obtener/',obtener_pedido,name='obtener_pedido'),
]
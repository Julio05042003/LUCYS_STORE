from django.urls import path
from .views import *

urlpatterns = [
    path('', tienda_view, name='tienda'),
    path('crear/', crear_producto, name='crear_producto'),
    path('editar/<int:id>/', editar_producto, name='editar_producto'),
    path('json/<int:id>/', producto_detalle_json, name='producto_json'),
    path('buscar-productos/', buscar_productos, name='buscar_productos'),
    path('buscar-productos-compra/', buscar_productos_compra, name='buscar_productos_compra'),
    # CATEGORIA
    path('categoria/crear/', crear_categoria, name='crear_categoria'),
    path('categoria/editar/<int:id>/', editar_categoria, name='editar_categoria'),

    # MARCA
    path('marca/crear/', crear_marca, name='crear_marca'),
    path('marca/editar/<int:id>/', editar_marca, name='editar_marca'),

    # OTROS
    path('detalle/<int:id>/', producto_detalle_json),
    path('producto/estado/<int:id>/', cambiar_estado_producto, name='cambiar_estado_producto'),
]
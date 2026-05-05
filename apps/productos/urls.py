from django.urls import path
from .views import *

urlpatterns = [
    path('', catalogo, name='catalogo'),
    path('crear/', crear_producto, name='crear_producto'),
    path('editar/<int:id>/', editar_producto, name='editar_producto'),

    # CATEGORIA
    path('categoria/crear/', crear_categoria, name='crear_categoria'),
    path('categoria/editar/<int:id>/', editar_categoria, name='editar_categoria'),

    # MARCA
    path('marca/crear/', crear_marca, name='crear_marca'),
    path('marca/editar/<int:id>/', editar_marca, name='editar_marca'),

    # OTROS
    path('detalle/<int:id>/', producto_detalle_json),
    path('estado/<int:id>/', cambiar_estado_producto),
]
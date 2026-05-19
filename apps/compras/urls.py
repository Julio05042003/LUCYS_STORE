from django.urls import path
from .views import *

urlpatterns = [
    path('compras/', compras_view, name='compras'),
    path('crear-compra/', crear_compra, name='crear_compra'),
    path('proveedores/', proveedores, name='proveedores'),
    path('crear-proveedor/', crear_proveedor, name='crear_proveedor'),
    path('editar-proveedor/', editar_proveedor, name='editar_proveedor'),
]
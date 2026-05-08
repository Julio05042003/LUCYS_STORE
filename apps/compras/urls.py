from django.urls import path
from .views import *

urlpatterns = [
    path('', compras_view, name='compras'),
    path('crear-compra/', crear_compra, name='crear_compra'),
    path('crear-proveedor/', crear_proveedor, name='crear_proveedor'),
]
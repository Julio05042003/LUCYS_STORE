from django.urls import path
from .views import *

urlpatterns = [
    path('', vista_ventas, name='ventas'),
    path('crear/', crear_venta, name='crear_venta'),
    path('anular/<int:venta_id>', anular_venta, name='anular_venta'),
    path('cobrar/', cobrar_venta, name='cobrar_venta'),
    path('buscar-pedidos/', buscar_pedidos, name='buscar_pedidos'),
    path('detalle/<int:venta_id>/', detalle_venta, name='detalle_venta'),

]
from django.urls import path
from .views import *

urlpatterns = [
    path('', vista_ventas, name='ventas'),
    path('crear/', crear_venta, name='crear_venta'),
    path('anular/<int:venta_id>', anular_venta, name='anular_venta'),
    path('cobrar/', cobrar_venta, name='cobrar_venta')
]
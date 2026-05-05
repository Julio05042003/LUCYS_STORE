from django.urls import path
from .views import crear_venta, vista_ventas

urlpatterns = [
    path('', vista_ventas, name='ventas'),
    path('crear/', crear_venta, name='crear_venta'),
]
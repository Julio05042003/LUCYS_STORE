from django.urls import path
from .views import *

urlpatterns = [
    path('', caja_view, name='caja'),

    # Caja (GERENTE)
    path('crear/', crear_caja, name='crear_caja'),

    # Apertura (CAJERO)
    path('abrir/', abrir_caja, name='abrir_caja'),

    # Movimientos
    path('movimiento/', crear_movimiento, name='crear_movimiento'),

    # Cierre
    path('cerrar/', cerrar_caja, name='cerrar_caja'),

    # Arqueo
    path('arqueo/', crear_arqueo, name='crear_arqueo'),
    path('iniciar-arqueo/', iniciar_arqueo, name='iniciar_arqueo'),
]
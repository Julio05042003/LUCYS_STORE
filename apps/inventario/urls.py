from django.urls import path
from .views import *

urlpatterns = [
    path('', inventario_view, name='inventario'),
    path('kardex/<int:id>/', kardex_view, name='kardex_view'),
    path('transferencias/', transferencias_view, name='transferencias'),
    path('transferencias/crear/', crear_transferencia, name='crear_transferencia'),
    path('transferencias/aprobar/<int:id>/', aprobar_transferencia, name='aprobar_transferencia'),
    path('transferencias/detalle/<int:id>/', detalle_transferencia, name='detalle_transferencia'),

]

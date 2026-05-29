from django.urls import path
from .views import *

urlpatterns = [
    path('', inventario_view, name='inventario'),
    path('kardex/<int:id>/', kardex_view, name='kardex_view'),
    path('kardex/', kardex_global_view, name='kardex_global_view'),
    path('inventario/ajuste/',crear_ajuste_inventario,name='crear_ajuste_inventario'),
    path('transferencias/', transferencias_view, name='transferencias'),
    path('transferencias/crear/', crear_transferencia, name='crear_transferencia'),
    path('transferencias/detalle/<int:id>/', detalle_transferencia, name='detalle_transferencia'),
    path('validar-stock/', validar_stock, name='validar_stock')

]

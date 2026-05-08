from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', index_empleados, name='index_empleados'),
    path('registro/', registro_cliente_view, name='registro_cliente'),
    path('clientes/', clientes_view, name='clientes'),
    path('buscar-clientes/', buscar_clientes, name='buscar_clientes'),
    path('crear/', crear_cliente, name='crear_cliente'),
    path('usuarios/', usuarios_view, name='usuarios'),
    path('usuarios/crear/', crear_usuario, name='crear_usuario'),
    path('usuarios/desbloquear/<int:user_id>/', desbloquear_usuario, name='desbloquear_usuario'),
]
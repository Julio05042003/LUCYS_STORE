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
    path('editar/', editar_cliente, name='editar_cliente'),
    path('crear-user', crear_user_cliente, name='crear_user_cliente'),
    path('usuarios/', usuarios_view, name='usuarios'),
    path('usuarios/crear/', crear_usuario, name='crear_usuario'),
    path('bloquear/<int:user_id>/', bloquear_usuario, name='bloquear_usuario'),
    path('desbloquear/<int:user_id>/', desbloquear_usuario, name='desbloquear_usuario'),
    path('editar/', editar_usuario, name='editar_usuario'),
]
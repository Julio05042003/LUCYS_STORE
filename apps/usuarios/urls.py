from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/',password_reset_request,name='password_reset'),
    path('password-reset/<int:user_id>/<str:token>/',password_reset_confirm,name='password_reset_confirm'),
    path('', index_empleados, name='index_empleados'),
    path('registro/', registro_cliente_view, name='registro_cliente'),
    path('activar/<int:uid>/<str:token>/', activar_cuenta, name='activar_cuenta'),
    path('clientes/', clientes_view, name='clientes'),
    path('buscar-clientes/', buscar_clientes, name='buscar_clientes'),
    path('crear/', crear_cliente, name='crear_cliente'),
    path('editar/', editar_cliente, name='editar_cliente'),
    path('crear-user', crear_user_cliente, name='crear_user_cliente'),
    path('dashboard/', dashboard_view, name='dashboard_view'),
    path('dashboard/excel/',dashboard_excel,name='dashboard_excel'),
    path('usuarios/', usuarios_view, name='usuarios'),
    path('usuarios/crear/', crear_usuario, name='crear_usuario'),
    path('bloquear/<int:user_id>/', bloquear_usuario, name='bloquear_usuario'),
    path('desbloquear/<int:user_id>/', desbloquear_usuario, name='desbloquear_usuario'),
    path('usuarios/editar/', editar_usuario, name='editar_usuario'),
    path('ubicaciones/', ubicaciones, name='ubicaciones'),
    path('crear-sucursal/', crear_sucursal, name='crear_sucursal'),
    path('editar-sucursal/<int:id>/', editar_sucursal, name='editar_sucursal'),
    path('cambiar-estado/<int:id>/', cambiar_estado_sucursal, name='cambiar_estado_sucursal'),
]
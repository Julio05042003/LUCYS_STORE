from django.urls import path
from . import views

urlpatterns = [
    path('', views.compras_view, name='compras'),
    path('crear/', views.crear_compra, name='crear_compra'),
]
from django.contrib import admin
from django.utils.html import format_html
from .models import *

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('marca_id', 'nombre')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('categoria_id', 'nombre')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('producto_id', 'nombre', 'marca', 'categoria', 'precio_c', 'ver_imagen')

    def ver_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" width="50" height="50" />', obj.imagen.url)
        return "Sin imagen"

    ver_imagen.short_description = "Imagen"
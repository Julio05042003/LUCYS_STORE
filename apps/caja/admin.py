from django.contrib import admin
from .models import *

class MovimientoCajaInline(admin.TabularInline):
    model = MovimientoCaja
    extra = 1


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'ubicacion')


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'caja', 'empleado', 'estado', 'fecha_apertura')
    inlines = [MovimientoCajaInline]
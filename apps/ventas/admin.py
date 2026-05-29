from django.contrib import admin
from .models import *
from apps.inventario.models import Inventario, Kardex

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('metodo_id', 'nombre')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('venta_id', 'cliente', 'empleado', 'total', 'estado', 'fecha')
    inlines = [DetalleVentaInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        venta = form.instance

        for detalle in venta.detalleventa_set.all():
            inv = Inventario.objects.get(
                producto=detalle.producto,
                sucursal=venta.empleado.sucursal
            )
            inv.stock -= detalle.cantidad
            inv.save()

            Kardex.objects.create(
                producto=detalle.producto,
                bodega=venta.empleado.bodega,
                tipo='SALIDA',
                cantidad=detalle.cantidad,
                descripcion='Venta'
            )
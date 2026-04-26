from django.contrib import admin
from .models import *
from apps.inventario.models import Inventario, Kardex

class TelefonoProveedorInline(admin.TabularInline):
    model = TelefonoProveedor
    extra = 1


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'correo')
    inlines = [TelefonoProveedorInline]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'ubicacion', 'fecha', 'total')
    inlines = [DetalleCompraInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        compra = form.instance

        for detalle in compra.detallecompra_set.all():
            inv, _ = Inventario.objects.get_or_create(
                producto=detalle.producto,
                ubicacion=compra.ubicacion,
                defaults={'stock': 0}
            )
            inv.stock += detalle.cantidad
            inv.save()

            Kardex.objects.create(
                producto=detalle.producto,
                ubicacion=compra.ubicacion,
                tipo='ENTRADA',
                cantidad=detalle.cantidad,
                descripcion='Compra'
            )
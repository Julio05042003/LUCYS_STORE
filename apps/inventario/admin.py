from django.contrib import admin
from .models import *
from apps.inventario.models import Inventario, Kardex

class DetalleTransferenciaInline(admin.TabularInline):
    model = DetalleTransferencia
    extra = 1


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('inventario_id', 'producto', 'bodega', 'stock')


@admin.register(Kardex)
class KardexAdmin(admin.ModelAdmin):
    list_display = ('kardex_id', 'producto', 'bodega', 'tipo', 'cantidad', 'fecha')


@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'origen', 'destino', 'empleado', 'estado', 'fecha')
    inlines = [DetalleTransferenciaInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        transferencia = form.instance

        for detalle in transferencia.detalletransferencia_set.all():
            # RESTAR en origen
            inv_origen = Inventario.objects.get(
                producto=detalle.producto,
                ubicacion=transferencia.origen
            )
            inv_origen.stock -= detalle.cantidad
            inv_origen.save()

            # SUMAR en destino
            inv_destino, _ = Inventario.objects.get_or_create(
                producto=detalle.producto,
                ubicacion=transferencia.destino,
                defaults={'stock': 0}
            )
            inv_destino.stock += detalle.cantidad
            inv_destino.save()

            # Kardex
            Kardex.objects.create(
                producto=detalle.producto,
                ubicacion=transferencia.origen,
                tipo='SALIDA',
                cantidad=detalle.cantidad,
                descripcion='Transferencia salida'
            )

            Kardex.objects.create(
                producto=detalle.producto,
                ubicacion=transferencia.destino,
                tipo='ENTRADA',
                cantidad=detalle.cantidad,
                descripcion='Transferencia entrada'
            )
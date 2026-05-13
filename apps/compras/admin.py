from django.contrib import admin
from django.db.models import Sum

from .models import *
from apps.inventario.models import Inventario, Kardex


# =========================
# INLINE TELÉFONOS
# =========================

class TelefonoProveedorInline(admin.TabularInline):
    model = TelefonoProveedor
    extra = 1


# =========================
# INLINE DETALLE COMPRA
# =========================

class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1


# =========================
# PROVEEDORES
# =========================

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'nombre',
        'contacto',
        'correo',
        'direccion'
    )

    search_fields = (
        'nombre',
        'contacto',
        'correo'
    )

    ordering = ('id',)

    inlines = [TelefonoProveedorInline]


# =========================
# TELEFONOS PROVEEDOR
# =========================

@admin.register(TelefonoProveedor)
class TelefonoProveedorAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'proveedor',
        'numero',
        'operadora',
        'tipo',
        'estado'
    )

    search_fields = (
        'numero',
        'operadora',
        'tipo',
        'proveedor__nombre'
    )

    list_filter = (
        'operadora',
        'tipo',
        'estado'
    )

    ordering = ('id',)


# =========================
# DETALLE COMPRA
# =========================

@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'compra',
        'producto',
        'cantidad',
        'precio',
        'subtotal'
    )

    search_fields = (
        'producto__nombre',
        'compra__id'
    )

    ordering = ('id',)

    def subtotal(self, obj):
        return obj.cantidad * obj.precio

    subtotal.short_description = 'Subtotal'


# =========================
# COMPRAS
# =========================

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'proveedor',
        'ubicacion',
        'empleado',
        'fecha',
        'total'
    )

    search_fields = (
        'proveedor__nombre',
        'ubicacion__nombre',
        'empleado__user__first_name',
        'empleado__user__last_name'
    )

    list_filter = (
        'ubicacion',
        'fecha'
    )

    ordering = ('-fecha',)

    autocomplete_fields = (
        'proveedor',
        'ubicacion',
        'empleado'
    )

    inlines = [DetalleCompraInline]

    # =========================
    # VALIDAR Y GUARDAR
    # =========================

    def save_related(self, request, form, formsets, change):

        super().save_related(request, form, formsets, change)

        compra = form.instance

        total = 0

        for detalle in compra.detallecompra_set.all():

            subtotal = detalle.cantidad * detalle.precio
            total += subtotal

            # =========================
            # INVENTARIO
            # =========================

            inventario, creado = Inventario.objects.get_or_create(
                producto=detalle.producto,
                ubicacion=compra.ubicacion,
                defaults={'stock': 0}
            )

            inventario.stock += detalle.cantidad
            inventario.save()

            # =========================
            # KARDEX
            # =========================

            Kardex.objects.create(
                producto=detalle.producto,
                ubicacion=compra.ubicacion,
                tipo='ENTRADA',
                cantidad=detalle.cantidad,
                descripcion=f'Compra #{compra.id}'
            )

        # =========================
        # TOTAL COMPRA
        # =========================

        compra.total = total
        compra.save()
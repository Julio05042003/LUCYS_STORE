from django.contrib import admin

from .models import (
    Caja,
    HistorialTipoCambio,
    AperturaCaja,
    MovimientoCaja,
    ArqueoCaja,
    Denominacion,
    DetalleAperturaCaja,
    DetalleArqueo
)


# =========================================
# DETALLE APERTURA INLINE
# =========================================

class DetalleAperturaInline(admin.TabularInline):
    model = DetalleAperturaCaja
    extra = 1



# =========================================
# DETALLE ARQUEO INLINE
# =========================================

class DetalleArqueoInline(admin.TabularInline):
    model = DetalleArqueo
    extra = 1



# =========================================
# CAJAS
# =========================================

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = (
        'caja_id',
        'nombre',
        'sucursal'
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'sucursal',
    )



# =========================================
# HISTORIAL TIPO CAMBIO
# =========================================

@admin.register(HistorialTipoCambio)
class HistorialTipoCambioAdmin(admin.ModelAdmin):
    list_display = (
        'tipocambio_id',
        'valor',
        'fecha'
    )

    ordering = (
        '-fecha',
    )



# =========================================
# APERTURA CAJA
# =========================================

@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = (
        'apertura_id',
        'caja',
        'empleado',
        'estado',
        'saldo_inicial',
        'saldo_final',
        'fecha_apertura',
        'fecha_cierre'
    )

    list_filter = (
        'estado',
        'fecha_apertura'
    )

    search_fields = (
        'caja__nombre',
        'empleado__nombre'
    )

    inlines = [
        DetalleAperturaInline
    ]



# =========================================
# MOVIMIENTOS CAJA
# =========================================

@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = (
        'movimiento_id',
        'apertura',
        'tipo',
        'moneda',
        'monto',
        'fecha'
    )

    list_filter = (
        'tipo',
        'moneda',
        'fecha'
    )

    search_fields = (
        'descripcion',
    )



# =========================================
# ARQUEOS CAJA
# =========================================

@admin.register(ArqueoCaja)
class ArqueoCajaAdmin(admin.ModelAdmin):
    list_display = (
        'arqueo_id',
        'apertura',
        'empleado',
        'tipo',
        'monto_sistema',
        'monto_fisico',
        'diferencia',
        'fecha'
    )

    list_filter = (
        'tipo',
        'fecha'
    )

    search_fields = (
        'empleado__nombre',
    )

    readonly_fields = (
        'diferencia',
    )

    inlines = [
        DetalleArqueoInline
    ]



# =========================================
# DENOMINACIONES
# =========================================

@admin.register(Denominacion)
class DenominacionAdmin(admin.ModelAdmin):
    list_display = (
        'denominacion_id',
        'moneda',
        'valor',
        'tipo'
    )

    list_filter = (
        'moneda',
        'tipo'
    )



# =========================================
# DETALLE APERTURA
# =========================================

@admin.register(DetalleAperturaCaja)
class DetalleAperturaCajaAdmin(admin.ModelAdmin):
    list_display = (
        'detalleapertura_id',
        'apertura',
        'denominacion',
        'cantidad',
        'subtotal'
    )



# =========================================
# DETALLE ARQUEO
# =========================================

@admin.register(DetalleArqueo)
class DetalleArqueoAdmin(admin.ModelAdmin):
    list_display = (
        'detallarqueo_id',
        'arqueo',
        'denominacion',
        'cantidad',
        'subtotal'
    )
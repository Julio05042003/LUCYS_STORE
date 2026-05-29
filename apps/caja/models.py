from django.db import models
from apps.usuarios.models import (
    Sucursal,
    Empleado,
    Estado
)


# =========================================
# CAJAS
# =========================================

class Caja(models.Model):
    caja_id = models.AutoField(primary_key=True)

    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        db_column='Sucursal_id'
    )

    nombre = models.CharField(
        max_length=100
    )

    class Meta:
        db_table = 'Cajas'

    def __str__(self):
        return self.nombre



# =========================================
# HISTORIAL TIPO CAMBIO
# =========================================

class HistorialTipoCambio(models.Model):
    tipocambio_id = models.AutoField(primary_key=True)

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'Historial_TipoCambio'

    def __str__(self):
        return f'{self.valor}'



# =========================================
# APERTURAS DE CAJA
# =========================================

class AperturaCaja(models.Model):
    apertura_id = models.AutoField(primary_key=True)

    caja = models.ForeignKey(
        Caja,
        on_delete=models.CASCADE,
        db_column='Caja_id'
    )

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        db_column='Empleado_id'
    )

    estado = models.ForeignKey(
        Estado,
        on_delete=models.CASCADE,
        db_column='Estado_id'
    )

    tipocambio = models.ForeignKey(
        HistorialTipoCambio,
        on_delete=models.CASCADE,
        db_column='TipoCambio_id'
    )

    fecha_apertura = models.DateTimeField(
        auto_now_add=True
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True
    )

    saldo_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    saldo_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'Aperturas_Cajas'

    def __str__(self):
        return f'Apertura #{self.apertura_id}'



# =========================================
# MOVIMIENTOS DE CAJA
# =========================================

class MovimientoCaja(models.Model):

    TIPOS = (
        ('INGRESO', 'INGRESO'),
        ('EGRESO', 'EGRESO'),
    )

    MONEDAS = (
        ('CORDOBA', 'CORDOBA'),
        ('DOLAR', 'DOLAR'),
    )

    movimiento_id = models.AutoField(primary_key=True)

    apertura = models.ForeignKey(
        AperturaCaja,
        on_delete=models.CASCADE,
        db_column='Apertura_id'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    moneda = models.CharField(
        max_length=20,
        choices=MONEDAS
    )

    descripcion = models.CharField(
        max_length=200
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'Movimientos_Cajas'

    def __str__(self):
        return f'{self.tipo} - {self.monto}'



# =========================================
# ARQUEOS DE CAJA
# =========================================

class ArqueoCaja(models.Model):

    TIPOS = (
        ('PARCIAL', 'PARCIAL'),
        ('FINAL', 'FINAL'),
    )

    arqueo_id = models.AutoField(primary_key=True)

    apertura = models.ForeignKey(
        AperturaCaja,
        on_delete=models.CASCADE,
        db_column='Apertura_id'
    )

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        db_column='Empleado_id'
    )

    tipocambio = models.ForeignKey(
        HistorialTipoCambio,
        on_delete=models.CASCADE,
        db_column='TipoCambio_id'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    monto_sistema = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    monto_fisico = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    observacion = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    justificacion = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'Arqueos_Caja'

    @property
    def diferencia(self):
        return self.monto_fisico - self.monto_sistema

    def __str__(self):
        return f'Arqueo #{self.arqueo_id}'



# =========================================
# DENOMINACIONES
# =========================================

class Denominacion(models.Model):

    MONEDAS = (
        ('CORDOBA', 'CORDOBA'),
        ('DOLAR', 'DOLAR'),
    )

    TIPOS = (
        ('BILLETE', 'BILLETE'),
        ('MONEDA', 'MONEDA'),
    )

    denominacion_id = models.AutoField(primary_key=True)

    moneda = models.CharField(
        max_length=20,
        choices=MONEDAS
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    class Meta:
        db_table = 'Denominaciones'

    def __str__(self):
        return f'{self.moneda} - {self.valor}'



# =========================================
# DETALLE APERTURA CAJA
# =========================================

class DetalleAperturaCaja(models.Model):
    detalleapertura_id = models.AutoField(primary_key=True)

    apertura = models.ForeignKey(
        AperturaCaja,
        on_delete=models.CASCADE,
        db_column='Apertura_id'
    )

    denominacion = models.ForeignKey(
        Denominacion,
        on_delete=models.CASCADE,
        db_column='Denominacion_id'
    )

    cantidad = models.IntegerField()

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        db_table = 'Detalle_Apertura_Caja'

    def __str__(self):
        return f'{self.denominacion} x {self.cantidad}'



# =========================================
# DETALLE ARQUEO
# =========================================

class DetalleArqueo(models.Model):
    detallarqueo_id = models.AutoField(primary_key=True, db_column='DetalleArqueo_id')

    arqueo = models.ForeignKey(
        ArqueoCaja,
        on_delete=models.CASCADE,
        db_column='Arqueo_id'
    )

    denominacion = models.ForeignKey(
        Denominacion,
        on_delete=models.CASCADE,
        db_column='Denominacion_id'
    )

    cantidad = models.IntegerField()

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        db_table = 'Detalle_Arqueo'

    def __str__(self):
        return f'{self.denominacion} x {self.cantidad}'
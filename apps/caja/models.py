from django.db import models
from apps.usuarios.models import Ubicacion, Empleado, Estado


class Caja(models.Model):
    id = models.AutoField(db_column='Caja_id', primary_key=True)

    ubicacion = models.ForeignKey(Ubicacion, db_column='Ubicacion_id', on_delete=models.CASCADE)
    nombre = models.CharField(db_column='Nombre', max_length=100)

    class Meta:
        db_table = 'Cajas'

    def __str__(self):
        return self.nombre


class AperturaCaja(models.Model):
    id = models.AutoField(db_column='Apertura_id', primary_key=True)

    caja = models.ForeignKey(Caja, db_column='Caja_id', on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, db_column='Empleado_id', on_delete=models.CASCADE)
    estado = models.ForeignKey(Estado, db_column='Estado_id', on_delete=models.CASCADE)

    fecha_apertura = models.DateTimeField(db_column='Fecha_apertura', auto_now_add=True)
    fecha_cierre = models.DateTimeField(db_column='Fecha_cierre', null=True, blank=True)

    saldo_inicial = models.DecimalField(db_column='Saldo_inicial', max_digits=10, decimal_places=2)
    saldo_final = models.DecimalField(db_column='Saldo_final', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'Aperturas_Cajas'


class MovimientoCaja(models.Model):
    id = models.AutoField(db_column='Movimiento_id', primary_key=True)

    apertura = models.ForeignKey(AperturaCaja, db_column='Apertura_id', on_delete=models.CASCADE)

    tipo = models.CharField(db_column='Tipo', max_length=20)
    descripcion = models.CharField(db_column='Descripcion', max_length=200)
    monto = models.DecimalField(db_column='Monto', max_digits=10, decimal_places=2)

    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True)

    class Meta:
        db_table = 'Movimientos_Cajas'


class ArqueoCaja(models.Model):
    arqueo_id = models.AutoField(primary_key=True, db_column='Arqueo_id')

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

    fecha = models.DateTimeField(auto_now_add=True, db_column='Fecha')

    saldo_sistema = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_real = models.DecimalField(max_digits=10, decimal_places=2)
    diferencia = models.DecimalField(max_digits=10, decimal_places=2)

    justificacion = models.TextField(null=True, blank=True)

    estado = models.ForeignKey(
        Estado,
        on_delete=models.CASCADE,
        db_column='Estado_id'
    )

    class Meta:
        db_table = 'Arqueos_Caja'

    def __str__(self):
        return f"Arqueo {self.arqueo_id} - Dif: {self.diferencia}"
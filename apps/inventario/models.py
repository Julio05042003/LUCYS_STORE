from django.db import models
from apps.productos.models import Producto
from apps.usuarios.models import Sucursal, Empleado, Estado, Bodega

class Inventario(models.Model):
    inventario_id = models.AutoField(primary_key=True, db_column='Inventario_id')

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='Producto_id')
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, db_column='Bodega_id')

    stock = models.IntegerField(default=0, db_column='Stock')

    class Meta:
        db_table = 'Inventarios'
        unique_together = ('producto', 'bodega')


class Kardex(models.Model):
    kardex_id = models.AutoField(primary_key=True, db_column='Kardex_id')

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='Producto_id')
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, db_column='Bodega_id')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='Empleado_id')

    TIPOS = (
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida')
    )
    tipo = models.CharField(max_length=20, choices=TIPOS,db_column='Tipo')
    cantidad = models.IntegerField(db_column='Cantidad')
    saldo = models.IntegerField(db_column='Saldo')
    Precio = models.DecimalField(max_digits=10, decimal_places=2, db_column='Precio')    
    fecha = models.DateTimeField(auto_now_add=True, db_column='Fecha')
    descripcion = models.CharField(max_length=200, db_column='Descripcion')
    documento = models.CharField(max_length=100, db_column='Documento')

    class Meta:
        db_table = 'Kardex'

class AjusteInventario(models.Model):

    TIPOS = (
        ('ENTRADA', 'ENTRADA'),
        ('SALIDA', 'SALIDA'),
    )

    MOTIVOS = (

    # ENTRADAS
    ('AJUSTE_MANUAL', 'Ajuste por Error'),

    # SALIDAS
    ('PRODUCTO_DAÑADO', 'Producto Dañado'),
    ('PERDIDA', 'Pérdida'),
    ('REGALIA', 'Regalía'),
    ('AJUSTE_MANUAL', 'Ajuste Manual'),
    ('ERROR_INVENTARIO', 'Error de Inventario'),
    )

    ajuste_id = models.AutoField(
        primary_key=True,
        db_column='Ajuste_id'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column='Producto_id'
    )

    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        db_column='Bodega_id'
    )

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        db_column='Empleado_id'
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
        db_column='Tipo'
    )

    cantidad = models.IntegerField(
        db_column='Cantidad'
    )

    motivo = models.CharField(
        max_length=50,
        choices=MOTIVOS,
        db_column='Motivo'
    )

    observacion = models.TextField(
        blank=True,
        null=True,
        db_column='Observacion'
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        db_column='Fecha'
    )

    class Meta:
        db_table = 'AjustesInventario'


class Transferencia(models.Model):
    id = models.AutoField(db_column='Transferencia_id', primary_key=True)

    origen = models.ForeignKey(Bodega, db_column='BodegaOrigen_id', on_delete=models.CASCADE, related_name='transferencias_origen')
    destino = models.ForeignKey(Bodega,db_column='BodegaDestino_id',on_delete=models.CASCADE, related_name='transferencias_destino')
    empleado = models.ForeignKey(Empleado,db_column='Empleado_id',on_delete=models.CASCADE)
    estado = models.ForeignKey(Estado,db_column='Estado_id',on_delete=models.CASCADE)
    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True)

    class Meta:
        db_table = 'Transferencias'

    def __str__(self):
        return f"{self.id} - {self.origen} → {self.destino}"


class DetalleTransferencia(models.Model):
    id = models.AutoField(db_column='Detalle_id', primary_key=True)

    transferencia = models.ForeignKey('Transferencia',db_column='Transferencia_id',on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto,db_column='Producto_id',on_delete=models.CASCADE)
    cantidad = models.IntegerField(db_column='Cantidad')

    class Meta:
        db_table = 'Detalles_Transferencias'

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"
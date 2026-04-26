from django.db import models
from apps.usuarios.models import Empleado, Estado, Cliente
from apps.pedidos.models import Pedido
from apps.productos.models import Producto
from apps.caja.models import AperturaCaja

class MetodoPago(models.Model):
    metodo_id = models.AutoField(primary_key=True, db_column='Metodo_id')
    nombre = models.CharField(max_length=50, db_column='Nombre')

    class Meta:
        db_table = 'Metodos_Pagos'


class Venta(models.Model):
    venta_id = models.AutoField(primary_key=True, db_column='Venta_id')

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='Cliente_id')
    metodo = models.ForeignKey(MetodoPago, on_delete=models.CASCADE, db_column='Metodo_id')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='Empleado_id')
    apertura = models.ForeignKey(AperturaCaja, on_delete=models.CASCADE, db_column='Apertura_id')
    pedido = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, blank=True, db_column='Pedido_id')
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, db_column='Estado_id')

    numero_factura = models.IntegerField(unique=True, db_column='NumeroFactura')
    fecha = models.DateTimeField(auto_now_add=True, db_column='Fecha')
    total = models.DecimalField(max_digits=10, decimal_places=2, db_column='Total')

    class Meta:
        db_table = 'Ventas'


class DetalleVenta(models.Model):
    detalle_id = models.AutoField(primary_key=True, db_column='Detalle_id')

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, db_column='Venta_id')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='Producto_id')

    cantidad = models.IntegerField(db_column='Cantidad')
    precio = models.DecimalField(max_digits=10, decimal_places=2, db_column='Precio')
    descuento = models.DecimalField(max_digits=10, decimal_places=2, db_column='Descuento')

    class Meta:
        db_table = 'Detalles_Ventas'
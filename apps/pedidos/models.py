from django.db import models
from apps.productos.models import Producto
from apps.usuarios.models import Ubicacion, Estado, Cliente, ClienteDireccion


class TipoEntrega(models.Model):
    id = models.AutoField(db_column='TipoEntrega_id', primary_key=True)
    nombre = models.CharField(db_column='Nombre', max_length=50)

    class Meta:
        db_table = 'Tipos_Entregas'

    def __str__(self):
        return self.nombre


class MetodoEnvio(models.Model):
    id = models.AutoField(db_column='MetodoEnvio_id', primary_key=True)
    nombre = models.CharField(db_column='Nombre', max_length=50)

    class Meta:
        db_table = 'Metodos_Envios'

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    id = models.AutoField(db_column='Pedido_id', primary_key=True)

    cliente = models.ForeignKey(Cliente, db_column='Cliente_id', on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(Ubicacion, db_column='Ubicacion_id', on_delete=models.CASCADE)

    tipo_entrega = models.ForeignKey(TipoEntrega, db_column='TipoEntrega_id', on_delete=models.CASCADE)
    metodo_envio = models.ForeignKey(MetodoEnvio, db_column='MetodoEnvio_id', on_delete=models.SET_NULL, null=True)

    direccion_envio = models.ForeignKey(
        ClienteDireccion,
        db_column='DireccionEnvio_id',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    estado = models.ForeignKey(Estado, db_column='Estado_id', on_delete=models.CASCADE)

    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True)
    total = models.DecimalField(db_column='Total', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'Pedidos'


class DetallePedido(models.Model):
    id = models.AutoField(db_column='Detalle_id', primary_key=True)

    pedido = models.ForeignKey(Pedido, db_column='Pedido_id', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, db_column='Producto_id', on_delete=models.CASCADE)

    cantidad = models.IntegerField(db_column='Cantidad')
    precio = models.DecimalField(db_column='Precio', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'Detalles_Pedidos'
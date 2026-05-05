from django.db import models
from apps.usuarios.models import Direccion, Ubicacion, Empleado
from apps.productos.models import Producto


class Proveedor(models.Model):
    id = models.AutoField(db_column='Proveedor_id', primary_key=True)

    direccion = models.ForeignKey(Direccion, db_column='Direccion_id', on_delete=models.CASCADE)
    nombre = models.CharField(db_column='Nombre', max_length=100)
    contacto = models.CharField(db_column='Contacto', max_length=100)
    correo = models.EmailField(db_column='Correo')

    class Meta:
        db_table = 'Proveedores'

    def __str__(self):
        return self.nombre
    
class TelefonoProveedor(models.Model):
    id = models.AutoField(db_column='Telefono_id', primary_key=True)

    proveedor = models.ForeignKey(
        Proveedor,
        db_column='Proveedor_id',
        on_delete=models.CASCADE
    )

    numero = models.CharField(db_column='Numero', max_length=20)
    operadora = models.CharField(db_column='Operadora', max_length=20, null=True, blank=True)
    tipo = models.CharField(db_column='Tipo', max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'Telefonos_Proveedores'

    def __str__(self):
        return f"{self.numero} - {self.proveedor}"


class Compra(models.Model):
    id = models.AutoField(db_column='Compra_id', primary_key=True)

    proveedor = models.ForeignKey(Proveedor, db_column='Proveedor_id', on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(Ubicacion, db_column='Ubicacion_id', on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, db_column='Empleado_id', on_delete=models.CASCADE)

    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True)
    total = models.DecimalField(db_column='Total', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'Compras'


class DetalleCompra(models.Model):
    id = models.AutoField(db_column='Detalle_id', primary_key=True)

    compra = models.ForeignKey(Compra, db_column='Compra_id', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, db_column='Producto_id', on_delete=models.CASCADE)

    cantidad = models.IntegerField(db_column='Cantidad')
    precio = models.DecimalField(db_column='Precio', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'Detalles_Compras'
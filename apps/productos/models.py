from django.db import models
from apps.usuarios.models import Estado
from decimal import Decimal, ROUND_HALF_UP

class Marca(models.Model):
    marca_id = models.AutoField(primary_key=True, db_column='Marca_id')
    nombre = models.CharField(max_length=100, db_column='Marca')

    class Meta:
        db_table = 'Marcas'


class Categoria(models.Model):
    categoria_id = models.AutoField(primary_key=True, db_column='Categoria_id')
    nombre = models.CharField(max_length=100, db_column='Categoria')

    class Meta:
        db_table = 'Categorias'


class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True, db_column='Producto_id')

    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE, db_column='Marca_id')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, db_column='Categoria_id')

    nombre = models.CharField(max_length=100, db_column='Nombre')
    codigo = models.CharField(max_length=50, unique=True, db_column='Codigo')
    descripcion = models.CharField(max_length=100, db_column='Descripcion')
    precio_c = models.DecimalField(max_digits=10, decimal_places=2, db_column='Precio_C')
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True, db_column='Imagen')

    class Meta:
        db_table = 'Productos'

    @property
    def precio_venta(self):
        return (self.precio_c * Decimal('1.20')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)




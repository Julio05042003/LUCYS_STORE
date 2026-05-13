from django.db import models
from django.contrib.auth.models import User

class Estado(models.Model):
    estado_id = models.AutoField(primary_key=True, db_column='Estado_id')
    nombre = models.CharField(max_length=50, unique=True, db_column='Estado')

    class Meta:
        db_table = 'Estados'

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    rol_id = models.AutoField(primary_key=True, db_column='Rol_id')
    nombre = models.CharField(max_length=50, unique=True, db_column='Rol')

    class Meta:
        db_table = 'Roles'

    def __str__(self):
        return self.nombre


class Direccion(models.Model):
    direccion_id = models.AutoField(primary_key=True, db_column='Direccion_id')
    pais = models.CharField(max_length=100, db_column='Pais')
    departamento = models.CharField(max_length=100, db_column='Departamento')
    ciudad = models.CharField(max_length=100, db_column='Ciudad')
    detalle = models.CharField(max_length=200, db_column='Detalle')

    class Meta:
        db_table = 'Direcciones'


class Ubicacion(models.Model):
    ubicacion_id = models.AutoField(primary_key=True, db_column='Ubicacion_id')

    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='Direccion_id')

    nombre = models.CharField(max_length=100, db_column='Nombre')
    codigo = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=20, db_column='Tipo')
    nivel = models.CharField(max_length=20, db_column='Nivel')

    class Meta:
        db_table = 'Ubicaciones'


class TelefonoUbicacion(models.Model):
    id = models.AutoField(db_column='Telefono_id', primary_key=True)

    ubicacion = models.ForeignKey(
        Ubicacion,
        db_column='Ubicacion_id',
        on_delete=models.CASCADE
    )
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')

    numero = models.CharField(db_column='Numero', max_length=20)
    operadora = models.CharField(db_column='Operadora', max_length=20, null=True, blank=True)
    tipo = models.CharField(db_column='Tipo', max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'Telefonos_Ubicaciones'

    def __str__(self):
        return f"{self.numero} - {self.ubicacion}"


class Empleado(models.Model):
    empleado_id = models.AutoField(primary_key=True, db_column='Empleado_id')

    user = models.OneToOneField(User, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True)

    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='Rol_id')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE, db_column='Ubicacion_id')

    class Meta:
        db_table = 'Empleados'



class Cliente(models.Model):
    cliente_id = models.AutoField(primary_key=True, db_column='Cliente_id')

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    identificacion = models.CharField(max_length=50, unique=True, db_column='Identificacion')

    nombre = models.CharField(max_length=100, db_column='Nombre', null=True, blank=True)
    apellido = models.CharField(max_length=100, db_column='Apellido', null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column='FechaRegistro')
    class Meta:
        db_table = 'Clientes'

    def __str__(self):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        return f"{self.nombre or ''} {self.apellido or ''}".strip()


class ClienteDireccion(models.Model):
    cliente_direccion_id = models.AutoField(primary_key=True, db_column='ClienteDireccion_id')

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='Cliente_id')
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='Direccion_id')
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')

    tipo = models.CharField(max_length=20, db_column='Tipo')

    class Meta:
        db_table = 'Clientes_Direcciones'


class TelefonoCliente(models.Model):
    telefono_id = models.AutoField(primary_key=True, db_column='Telefono_id')

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='Cliente_id')
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='Estado_id')

    numero = models.CharField(max_length=20, db_column='Numero')
    operadora = models.CharField(max_length=20, null=True, blank=True, db_column='Operadora')
    tipo = models.CharField(max_length=20, null=True, blank=True, db_column='Tipo')

    class Meta:
        db_table = 'Telefonos_Clientes'
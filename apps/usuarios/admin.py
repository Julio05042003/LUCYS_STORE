from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import *
from .forms import (
    EmpleadoForm,
    ClienteForm,
    SucursalForm
)

# =========================
# INLINES
# =========================

class TelefonoClienteInline(admin.TabularInline):
    model = TelefonoCliente
    extra = 1


class ClienteDireccionInline(admin.TabularInline):
    model = ClienteDireccion
    extra = 1


class TelefonoSucursalInline(admin.TabularInline):
    model = TelefonoSucursal
    extra = 1


# =========================
# ESTADO
# =========================

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):

    list_display = (
        'estado_id',
        'nombre'
    )

    search_fields = (
        'nombre',
    )

    ordering = (
        'estado_id',
    )


# =========================
# ROL
# =========================

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):

    list_display = (
        'rol_id',
        'nombre'
    )

    search_fields = (
        'nombre',
    )

    ordering = (
        'rol_id',
    )


# =========================
# DIRECCION
# =========================

@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):

    list_display = (
        'direccion_id',
        'pais',
        'departamento',
        'ciudad',
        'detalle'
    )

    search_fields = (
        'pais',
        'departamento',
        'ciudad',
        'detalle'
    )

    list_filter = (
        'pais',
        'departamento'
    )

    ordering = (
        'direccion_id',
    )


# =========================
# SUCURSAL
# =========================

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):

    form = SucursalForm

    list_display = (
        'sucursal_id',
        'nombre',
        'codigo',
        'estado',
        'direccion',
        'get_bodega'
    )

    fields = (
        'estado',
        'nombre',
        'codigo',
        'pais',
        'departamento',
        'ciudad',
        'detalle'
    )

    search_fields = (
        'nombre',
        'codigo',
        'estado__nombre'
    )

    list_filter = (
        'estado',
    )

    ordering = (
        'sucursal_id',
    )

    inlines = [
        TelefonoSucursalInline
    ]

    def get_bodega(self, obj):

        if hasattr(obj, 'bodega'):
            return obj.bodega.nombre

        return "-"

    get_bodega.short_description = "Bodega"


# =========================
# TELEFONO SUCURSAL
# =========================

@admin.register(TelefonoSucursal)
class TelefonoSucursalAdmin(admin.ModelAdmin):

    list_display = (
        'telefono_id',
        'sucursal',
        'numero',
        'operadora',
        'tipo'
    )

    search_fields = (
        'numero',
        'operadora',
        'tipo',
        'sucursal__nombre'
    )

    list_filter = (
        'operadora',
        'tipo'
    )

    ordering = (
        'telefono_id',
    )


# =========================
# BODEGA
# =========================

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):

    list_display = (
        'bodega_id',
        'nombre',
        'codigo',
        'sucursal',
        'estado',
        'direccion'
    )

    search_fields = (
        'nombre',
        'codigo',
        'sucursal__nombre'
    )

    list_filter = (
        'estado',
    )

    ordering = (
        'bodega_id',
    )


# =========================
# EMPLEADO
# =========================

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):

    form = EmpleadoForm

    list_display = (
        'empleado_id',
        'get_nombre',
        'get_email',
        'rol',
        'sucursal',
        'estado'
    )

    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'rol__nombre',
        'sucursal__nombre'
    )

    list_filter = (
        'rol',
        'estado',
        'sucursal'
    )

    ordering = (
        'empleado_id',
    )

    autocomplete_fields = (
        'rol',
        'estado',
        'sucursal'
    )

    def get_nombre(self, obj):

        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"

        return "-"

    get_nombre.short_description = 'Nombre'

    def get_email(self, obj):

        if obj.user:
            return obj.user.email

        return "-"

    get_email.short_description = 'Correo'

    def save_model(self, request, obj, form, change):

        # =========================
        # NUEVO EMPLEADO
        # =========================
        if not obj.user:

            email = form.cleaned_data['email']

            existe = User.objects.filter(
                username=email
            ).exists()

            if existe:

                raise ValidationError(
                    "Ya existe un usuario con ese correo"
                )

            user = User.objects.create_user(

                username=email,
                email=email,
                password=form.cleaned_data['password']

            )

            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']

            user.is_staff = True

            user.save()

            obj.user = user

        # =========================
        # EDITAR EMPLEADO
        # =========================
        else:

            user = obj.user

            email = form.cleaned_data['email']

            existe = User.objects.filter(
                username=email
            ).exclude(id=user.id).exists()

            if existe:

                raise ValidationError(
                    "Ya existe un usuario con ese correo"
                )

            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']

            user.email = email
            user.username = email

            password = form.cleaned_data.get('password')

            if password:
                user.set_password(password)

            user.save()

        super().save_model(
            request,
            obj,
            form,
            change
        )


# =========================
# CLIENTE
# =========================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

    form = ClienteForm

    list_display = (
        'cliente_id',
        'identificacion',
        'get_nombre',
        'get_email',
        'fecha_registro'
    )

    search_fields = (
        'identificacion',
        'nombre',
        'apellido',
        'user__first_name',
        'user__last_name',
        'user__email'
    )

    list_filter = (
        'fecha_registro',
    )

    ordering = (
        '-fecha_registro',
    )

    inlines = [
        ClienteDireccionInline,
        TelefonoClienteInline
    ]

    def get_nombre(self, obj):

        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"

        return f"{obj.nombre or ''} {obj.apellido or ''}".strip()

    get_nombre.short_description = 'Nombre'

    def get_email(self, obj):

        if obj.user:
            return obj.user.email

        return "-"

    get_email.short_description = 'Correo'

    def save_model(self, request, obj, form, change):

        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        # =========================
        # CLIENTE CON USUARIO
        # =========================
        if email:

            # NUEVO
            if not obj.user:

                existe = User.objects.filter(
                    username=email
                ).exists()

                if existe:

                    raise ValidationError(
                        "Ya existe un usuario con ese correo"
                    )

                user = User.objects.create_user(

                    username=email,
                    email=email,
                    password=password

                )

                obj.user = user

            # EDITAR
            else:

                user = obj.user

                existe = User.objects.filter(
                    username=email
                ).exclude(id=user.id).exists()

                if existe:

                    raise ValidationError(
                        "Ya existe un usuario con ese correo"
                    )

                user.username = email
                user.email = email

                if password:
                    user.set_password(password)

            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')

            user.save()

            # LIMPIAR CLIENTE FISICO
            obj.nombre = None
            obj.apellido = None

        # =========================
        # CLIENTE FISICO
        # =========================
        else:

            obj.nombre = form.cleaned_data.get('nombre')
            obj.apellido = form.cleaned_data.get('apellido')

        super().save_model(
            request,
            obj,
            form,
            change
        )


# =========================
# CLIENTE DIRECCION
# =========================

@admin.register(ClienteDireccion)
class ClienteDireccionAdmin(admin.ModelAdmin):

    list_display = (
        'cliente_direccion_id',
        'cliente',
        'direccion',
        'tipo'
    )

    search_fields = (
        'cliente__nombre',
        'cliente__apellido',
        'tipo'
    )

    list_filter = (
        'tipo',
    )

    ordering = (
        'cliente_direccion_id',
    )


# =========================
# TELEFONO CLIENTE
# =========================

@admin.register(TelefonoCliente)
class TelefonoClienteAdmin(admin.ModelAdmin):

    list_display = (
        'telefono_id',
        'cliente',
        'numero',
        'operadora',
        'tipo'
    )

    search_fields = (
        'numero',
        'operadora',
        'tipo',
        'cliente__nombre',
        'cliente__apellido'
    )

    list_filter = (
        'operadora',
        'tipo'
    )

    ordering = (
        'telefono_id',
    )
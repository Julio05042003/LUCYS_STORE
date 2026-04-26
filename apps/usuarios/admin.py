from django.contrib import admin
from django.contrib.auth.models import User

from .models import *
from .forms import EmpleadoForm, ClienteForm


# =========================
# INLINES
# =========================

class TelefonoClienteInline(admin.TabularInline):
    model = TelefonoCliente
    extra = 1


class ClienteDireccionInline(admin.TabularInline):
    model = ClienteDireccion
    extra = 1


class TelefonoUbicacionInline(admin.TabularInline):
    model = TelefonoUbicacion
    extra = 1


# =========================
# CONFIGURACIONES BÁSICAS
# =========================

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('estado_id', 'nombre')


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('rol_id', 'nombre')


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ('direccion_id', 'pais', 'ciudad')


# =========================
# UBICACION
# =========================

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('ubicacion_id', 'nombre', 'tipo', 'estado')
    inlines = [TelefonoUbicacionInline]


# =========================
# EMPLEADO
# =========================

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    form = EmpleadoForm

    list_display = ('empleado_id', 'get_nombre', 'rol', 'ubicacion', 'estado')

    def get_nombre(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return "-"
    get_nombre.short_description = 'Nombre'

    def save_model(self, request, obj, form, change):

        if not obj.user:
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.is_staff = True
            user.save()

            obj.user = user

        super().save_model(request, obj, form, change)


# =========================
# CLIENTE
# =========================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    form = ClienteForm

    list_display = ('cliente_id', 'get_nombre', 'get_email')

    inlines = [ClienteDireccionInline, TelefonoClienteInline]

    def get_nombre(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return f"{obj.nombre or ''} {obj.apellido or ''}"
    get_nombre.short_description = 'Nombre'

    def get_email(self, obj):
        return obj.user.email if obj.user else "-"
    get_email.short_description = 'Correo'

    def save_model(self, request, obj, form, change):

        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        # 🔵 CASO 1: Cliente con cuenta
        if email and password:
            user = User.objects.create_user(
                username=email,
                password=password
            )

            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = email
            user.save()

            obj.user = user

        # CASO 2: Cliente físico
        else:
            obj.nombre = form.cleaned_data.get('nombre')
            obj.apellido = form.cleaned_data.get('apellido')

        super().save_model(request, obj, form, change)
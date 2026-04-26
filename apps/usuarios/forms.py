from django import forms
from django.contrib.auth.models import User
from .models import Empleado, Cliente


# =========================
# EMPLEADO FORM
# =========================
class EmpleadoForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    email = forms.EmailField(label="Correo")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

    class Meta:
        model = Empleado
        fields = ['estado', 'rol', 'ubicacion']


# =========================
# CLIENTE FORM
# =========================
class ClienteForm(forms.ModelForm):
    # Datos para usuario (opcional)
    first_name = forms.CharField(label="Nombre (usuario)", required=False)
    last_name = forms.CharField(label="Apellido (usuario)", required=False)
    email = forms.EmailField(label="Correo", required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=False)

    # Datos cliente físico
    nombre = forms.CharField(label="Nombre", required=False)
    apellido = forms.CharField(label="Apellido", required=False)

    class Meta:
        model = Cliente
        fields = ['identificacion', 'nombre', 'apellido']
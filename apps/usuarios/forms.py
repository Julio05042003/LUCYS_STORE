from django import forms
from django.contrib.auth.models import User
from .models import Empleado, Cliente, Ubicacion, Direccion


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


class UbicacionForm(forms.ModelForm):
    # 🔥 Campos de Dirección embebidos
    pais = forms.CharField(label="País")
    departamento = forms.CharField(label="Departamento")
    ciudad = forms.CharField(label="Ciudad")
    detalle = forms.CharField(label="Detalle")

    class Meta:
        model = Ubicacion
        fields = ['estado', 'nombre', 'tipo']

    def save(self, commit=True):
        # 🔥 Crear dirección primero
        direccion = Direccion.objects.create(
            pais=self.cleaned_data['pais'],
            departamento=self.cleaned_data['departamento'],
            ciudad=self.cleaned_data['ciudad'],
            detalle=self.cleaned_data['detalle']
        )

        ubicacion = super().save(commit=False)
        ubicacion.direccion = direccion

        if commit:
            ubicacion.save()

        return ubicacion
from django import forms
from django.contrib.auth.models import User

from .models import (
    Empleado,
    Cliente,
    Direccion,
    Sucursal,
    Bodega
)


# =========================
# EMPLEADO FORM
# =========================
class EmpleadoForm(forms.ModelForm):

    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    email = forms.EmailField(label="Correo")

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña",
        required=False
    )

    class Meta:
        model = Empleado

        fields = [
            'estado',
            'rol',
            'sucursal'
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.user:

            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email


# =========================
# CLIENTE FORM
# =========================
class ClienteForm(forms.ModelForm):

    first_name = forms.CharField(
        label="Nombre Usuario",
        required=False
    )

    last_name = forms.CharField(
        label="Apellido Usuario",
        required=False
    )

    email = forms.EmailField(
        label="Correo",
        required=False
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False
    )

    nombre = forms.CharField(
        label="Nombre",
        required=False
    )

    apellido = forms.CharField(
        label="Apellido",
        required=False
    )

    class Meta:
        model = Cliente

        fields = [
            'identificacion',
            'nombre',
            'apellido'
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:

            self.fields['nombre'].initial = self.instance.nombre
            self.fields['apellido'].initial = self.instance.apellido

            if self.instance.user:

                self.fields['first_name'].initial = self.instance.user.first_name
                self.fields['last_name'].initial = self.instance.user.last_name
                self.fields['email'].initial = self.instance.user.email


# =========================
# SUCURSAL FORM
# =========================
class SucursalForm(forms.ModelForm):

    pais = forms.CharField(label="País")
    departamento = forms.CharField(label="Departamento")
    ciudad = forms.CharField(label="Ciudad")
    detalle = forms.CharField(label="Detalle")

    class Meta:
        model = Sucursal

        fields = [
            'estado',
            'nombre',
            'codigo'
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.direccion:

            self.fields['pais'].initial = self.instance.direccion.pais
            self.fields['departamento'].initial = self.instance.direccion.departamento
            self.fields['ciudad'].initial = self.instance.direccion.ciudad
            self.fields['detalle'].initial = self.instance.direccion.detalle

    def save(self, commit=True):

        sucursal = super().save(commit=False)

        # =====================================
        # DIRECCION
        # =====================================

        if not sucursal.direccion_id:

            direccion = Direccion.objects.create(
                pais=self.cleaned_data['pais'],
                departamento=self.cleaned_data['departamento'],
                ciudad=self.cleaned_data['ciudad'],
                detalle=self.cleaned_data['detalle']
            )

            sucursal.direccion = direccion

        else:

            direccion = sucursal.direccion

            direccion.pais = self.cleaned_data['pais']
            direccion.departamento = self.cleaned_data['departamento']
            direccion.ciudad = self.cleaned_data['ciudad']
            direccion.detalle = self.cleaned_data['detalle']

            direccion.save()

        if commit:
            sucursal.save()
            # CREAR BODEGA AUTOMATICAMENTE
            if not hasattr(sucursal, 'bodega'):

                Bodega.objects.create(
                    estado=sucursal.estado,
                    direccion=sucursal.direccion,
                    sucursal=sucursal,
                    nombre=f"Bodega {sucursal.nombre}",
                    codigo=f"BOD-{sucursal.codigo}"
                )

        return sucursal
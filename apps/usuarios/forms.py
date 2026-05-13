from django import forms
from django.contrib.auth.models import User
from .models import (
    Empleado,
    Cliente,
    Ubicacion,
    Direccion
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
            'ubicacion'
        ]

    # =========================
    # CARGAR DATOS EN EDITAR
    # =========================
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

    # USUARIO OPCIONAL
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

    # CLIENTE FISICO
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

    # =========================
    # CARGAR DATOS EN EDITAR
    # =========================
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
# UBICACION FORM
# =========================
class UbicacionForm(forms.ModelForm):

    pais = forms.CharField(label="País")
    departamento = forms.CharField(label="Departamento")
    ciudad = forms.CharField(label="Ciudad")
    detalle = forms.CharField(label="Detalle")

    TIPO_CHOICES = [
        ('BODEGA', 'BODEGA'),
        ('SUCURSAL', 'SUCURSAL'),
    ]

    NIVEL_CHOICES = [
        ('CENTRAL', 'CENTRAL'),
        ('SECUNDARIA', 'SECUNDARIA'),
    ]

    tipo = forms.ChoiceField(choices=TIPO_CHOICES)

    nivel = forms.ChoiceField(choices=NIVEL_CHOICES)

    class Meta:
        model = Ubicacion

        fields = [
            'estado',
            'nombre',
            'codigo',
            'tipo',
            'nivel'
        ]

    # =========================
    # CARGAR DATOS EN EDITAR
    # =========================
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.direccion:

            self.fields['pais'].initial = self.instance.direccion.pais
            self.fields['departamento'].initial = self.instance.direccion.departamento
            self.fields['ciudad'].initial = self.instance.direccion.ciudad
            self.fields['detalle'].initial = self.instance.direccion.detalle

    # =========================
    # SAVE
    # =========================
    def save(self, commit=True):

        ubicacion = super().save(commit=False)

        # NUEVA DIRECCION
        if not ubicacion.direccion_id:

            direccion = Direccion.objects.create(
                pais=self.cleaned_data['pais'],
                departamento=self.cleaned_data['departamento'],
                ciudad=self.cleaned_data['ciudad'],
                detalle=self.cleaned_data['detalle']
            )

            ubicacion.direccion = direccion

        # EDITAR DIRECCION
        else:

            direccion = ubicacion.direccion

            direccion.pais = self.cleaned_data['pais']
            direccion.departamento = self.cleaned_data['departamento']
            direccion.ciudad = self.cleaned_data['ciudad']
            direccion.detalle = self.cleaned_data['detalle']

            direccion.save()

        if commit:
            ubicacion.save()

        return ubicacion
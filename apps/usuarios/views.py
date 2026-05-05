from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from apps.usuarios.models import *
from django.db import transaction
from django.utils import timezone
import re

# VALIDACIONES
# =========================

def validar_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def validar_password(password):
    return len(password) >= 6 and any(char.isdigit() for char in password)

def login_view(request):

    if request.method == 'POST':
        username = request.POST.get('usuario')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, "Todos los campos son obligatorios")
            return render(request, 'login.html')

        # Intentos
        intentos = request.session.get('intentos', 0)

        user = authenticate(request, username=username, password=password)

        # ❌ LOGIN FALLIDO
        if not user:
            intentos += 1
            request.session['intentos'] = intentos

            if intentos >= 3:
                try:
                    user_db = User.objects.get(username=username)
                    user_db.is_active = False
                    user_db.save()
                    messages.error(request, "Cuenta bloqueada. Contacte al gerente")
                except User.DoesNotExist:
                    messages.error(request, "Usuario no existe")
            else:
                messages.error(request, f"Credenciales incorrectas ({intentos}/3)")

            return render(request, 'login.html')

        # 🔒 USUARIO BLOQUEADO
        if not user.is_active:
            messages.error(request, "Usuario bloqueado")
            return render(request, 'login.html')

        # RESET INTENTOS
        request.session['intentos'] = 0

        # 👨‍💼 EMPLEADO
        try:
            empleado = Empleado.objects.select_related('estado', 'rol').get(user=user)

            if empleado.estado.nombre.lower() != "activo":
                messages.error(request, "Empleado inactivo")
                return render(request, 'login.html')

            login(request, user)

            request.session['rol'] = empleado.rol.nombre
            request.session['nombre'] = user.first_name
            request.session['apellido'] = user.last_name

            return redirect('index_empleados')

        except Empleado.DoesNotExist:
            # 🛍️ CLIENTE
            login(request, user)
            return redirect('tienda')

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')


# =========================
# INDEX EMPLEADOS
# =========================
@login_required(login_url='login')
def index_empleados(request):

    try:
        empleado = Empleado.objects.select_related('user', 'rol', 'ubicacion').get(user=request.user)
    except Empleado.DoesNotExist:
        return redirect('tienda')

    return render(request, 'empleados/index.html', {
        'empleado': empleado
    })


# =========================
# REGISTRO CLIENTE
# =========================
def registro_cliente_view(request):

    if request.method == 'POST':
        try:
            with transaction.atomic():

                # =========================
                # DATOS PERSONALES
                # =========================
                email = request.POST.get('email')
                password = request.POST.get('password')
                nombre = request.POST.get('nombre')
                apellido = request.POST.get('apellido')
                identificacion = request.POST.get('identificacion')

                # =========================
                # LISTAS
                # =========================
                paises = request.POST.getlist('pais[]')
                departamentos = request.POST.getlist('departamento[]')
                ciudades = request.POST.getlist('ciudad[]')
                detalles = request.POST.getlist('detalle[]')

                telefonos = request.POST.getlist('telefono[]')
                operadoras = request.POST.getlist('operadora[]')
                tipos_tel = request.POST.getlist('tipo_tel[]')

                # =========================
                # VALIDACIONES
                # =========================

                if not all([email, password, nombre, apellido, identificacion]):
                    messages.error(request, "Todos los campos personales son obligatorios")
                    return redirect('registro_cliente')

                if not validar_email(email):
                    messages.error(request, "Correo inválido")
                    return redirect('registro_cliente')

                if not validar_password(password):
                    messages.error(request, "La contraseña debe tener mínimo 6 caracteres y un número")
                    return redirect('registro_cliente')

                if User.objects.filter(username=email).exists():
                    messages.error(request, "El correo ya está registrado")
                    return redirect('registro_cliente')

                if Cliente.objects.filter(identificacion=identificacion).exists():
                    messages.error(request, "La identificación ya existe")
                    return redirect('registro_cliente')

                # =========================
                # VALIDAR DIRECCIONES
                # =========================
                direcciones_validas = sum(
                    1 for i in range(len(paises))
                    if all([paises[i], departamentos[i], ciudades[i], detalles[i]])
                )

                if direcciones_validas == 0:
                    messages.error(request, "Debes agregar al menos una dirección completa")
                    return redirect('registro_cliente')

                # =========================
                # VALIDAR TELÉFONOS
                # =========================
                telefonos_validos = 0
                for tel in telefonos:
                    if tel:
                        if not tel.isdigit():
                            messages.error(request, "El teléfono debe ser numérico")
                            return redirect('registro_cliente')
                        telefonos_validos += 1

                if telefonos_validos == 0:
                    messages.error(request, "Debes ingresar al menos un teléfono válido")
                    return redirect('registro_cliente')

                # =========================
                # CREAR USER
                # =========================
                user = User.objects.create_user(
                    username=email,
                    password=password,
                    email=email,
                    first_name=nombre,
                    last_name=apellido
                )

                # =========================
                # CREAR CLIENTE COMPLETO
                # =========================
                cliente = Cliente.objects.create(
                    user=user,
                    identificacion=identificacion,
                    nombre=nombre,          
                    apellido=apellido
                    #fecha_registro = timezone.now()     
                )

                # =========================
                # DIRECCIONES
                # =========================
                for i in range(len(paises)):
                    if all([paises[i], departamentos[i], ciudades[i], detalles[i]]):

                        direccion = Direccion.objects.create(
                            pais=paises[i],
                            departamento=departamentos[i],
                            ciudad=ciudades[i],
                            detalle=detalles[i]
                        )

                        ClienteDireccion.objects.create(
                            cliente=cliente,
                            direccion=direccion,
                            tipo="Principal" if i == 0 else "Secundaria"
                        )

                # =========================
                # TELÉFONOS
                # =========================
                for i in range(len(telefonos)):
                    if telefonos[i]:
                        TelefonoCliente.objects.create(
                            cliente=cliente,
                            numero=telefonos[i],
                            operadora=operadoras[i] if i < len(operadoras) else "",
                            tipo=tipos_tel[i] if i < len(tipos_tel) else ""
                        )

                messages.success(request, "Cuenta creada correctamente")
                return redirect('login')

        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            return redirect('registro_cliente')

    return render(request, 'registro_cliente.html')

def clientes_view(request):
    clientes = Cliente.objects.all().order_by('-id')

    return render(request, 'empleados/clientes.html', {
        'clientes': clientes
    })



def clientes_view(request):
    clientes = Cliente.objects.all().order_by('-id')

    return render(request, 'empleados/clientes.html', {
        'clientes': clientes
    })


def crear_cliente(request):

    if request.method == 'POST':
        try:
            with transaction.atomic():

                # =========================
                # DATOS PERSONALES
                # =========================
                nombre = request.POST.get('nombre')
                apellido = request.POST.get('apellido')
                identificacion = request.POST.get('identificacion')

                # =========================
                # LISTAS
                # =========================
                paises = request.POST.getlist('pais[]')
                departamentos = request.POST.getlist('departamento[]')
                ciudades = request.POST.getlist('ciudad[]')
                detalles = request.POST.getlist('detalle[]')

                telefonos = request.POST.getlist('telefono[]')
                operadoras = request.POST.getlist('operadora[]')
                tipos_tel = request.POST.getlist('tipo_tel[]')

                # =========================
                # VALIDACIONES
                # =========================
                if not all([nombre, apellido, identificacion]):
                    messages.error(request, "Campos obligatorios vacíos")
                    return redirect('registro_cliente')

                if Cliente.objects.filter(identificacion=identificacion).exists():
                    messages.error(request, "La identificación ya existe")
                    return redirect('registro_cliente')

                # =========================
                # VALIDAR DIRECCIONES
                # =========================
                direcciones_validas = sum(
                    1 for i in range(len(paises))
                    if all([paises[i], departamentos[i], ciudades[i], detalles[i]])
                )

                if direcciones_validas == 0:
                    messages.error(request, "Agrega al menos una dirección")
                    return redirect('registro_cliente')

                # =========================
                # VALIDAR TELÉFONOS
                # =========================
                telefonos_validos = 0
                for tel in telefonos:
                    if tel:
                        if not tel.isdigit():
                            messages.error(request, "Teléfono inválido")
                            return redirect('registro_cliente')
                        telefonos_validos += 1

                if telefonos_validos == 0:
                    messages.error(request, "Ingresa al menos un teléfono")
                    return redirect('registro_cliente')

                # =========================
                # CREAR CLIENTE (SIN USER)
                # =========================
                cliente = Cliente.objects.create(
                    identificacion=identificacion,
                    nombre=nombre,
                    apellido=apellido,
                )

                # =========================
                # DIRECCIONES
                # =========================
                for i in range(len(paises)):
                    if all([paises[i], departamentos[i], ciudades[i], detalles[i]]):

                        direccion = Direccion.objects.create(
                            pais=paises[i],
                            departamento=departamentos[i],
                            ciudad=ciudades[i],
                            detalle=detalles[i]
                        )

                        ClienteDireccion.objects.create(
                            cliente=cliente,
                            direccion=direccion,
                            tipo="Principal" if i == 0 else "Secundaria"
                        )

                # =========================
                # TELÉFONOS
                # =========================
                for i in range(len(telefonos)):
                    if telefonos[i]:
                        TelefonoCliente.objects.create(
                            cliente=cliente,
                            numero=telefonos[i],
                            operadora=operadoras[i] if i < len(operadoras) else "",
                            tipo=tipos_tel[i] if i < len(tipos_tel) else ""
                        )

                messages.success(request, "Cliente registrado correctamente")
                return redirect('clientes')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('registro_cliente')

    return render(request, 'empleados/clientes.html')

@login_required
def usuarios_view(request):

    empleado_actual = Empleado.objects.get(user=request.user)

    # 🔒 FILTRO POR UBICACIÓN
    if empleado_actual.rol.nombre.lower() == "administrador":
        empleados = Empleado.objects.select_related('user','rol','ubicacion').all()
        ubicaciones = Ubicacion.objects.all()
    else:
        empleados = Empleado.objects.select_related('user','rol','ubicacion').filter(
            ubicacion=empleado_actual.ubicacion
        )
        ubicaciones = Ubicacion.objects.filter(id=empleado_actual.ubicacion.id)

    return render(request, 'empleados/usuarios.html', {
        'empleados': empleados,
        'roles': Rol.objects.all(),
        'estados': Estado.objects.all(),
        'ubicaciones': ubicaciones
    })

@login_required
def crear_usuario(request):

    if request.method == 'POST':
        try:
            with transaction.atomic():

                username = request.POST.get('username')
                email = request.POST.get('email')
                password = request.POST.get('password')
                nombre = request.POST.get('nombre')
                apellido = request.POST.get('apellido')

                rol_id = request.POST.get('rol_id')
                estado_id = request.POST.get('estado_id')
                ubicacion_id = request.POST.get('ubicacion_id')

                if User.objects.filter(username=username).exists():
                    messages.error(request, "Usuario ya existe")
                    return redirect('usuarios')

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=nombre,
                    last_name=apellido
                )

                Empleado.objects.create(
                    user=user,
                    rol_id=rol_id,
                    estado_id=estado_id,
                    ubicacion_id=ubicacion_id
                )

                messages.success(request, "Usuario creado")
                return redirect('usuarios')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('usuarios')
        
@login_required
def desbloquear_usuario(request, user_id):

    user = User.objects.get(id=user_id)
    user.is_active = True
    user.save()

    messages.success(request, "Usuario desbloqueado")
    return redirect('usuarios')
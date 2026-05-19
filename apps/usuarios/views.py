from django.shortcuts import render, redirect
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from apps.usuarios.models import *
from django.db import transaction
from django.utils import timezone
import re, json
from django.http import JsonResponse
from django.db import connection



@login_required
def dashboard_gerente(request):

    empleado = Empleado.objects.select_related(
        'rol',
        'ubicacion',
        'user'
    ).get(user=request.user)

    # =====================================
    # KPIs
    # =====================================
    with connection.cursor() as cursor:

        cursor.execute("EXEC sp_dashboard_kpis")

        row = cursor.fetchone()

        kpis = {

            'ventas_hoy': row[0],
            'ventas_mes': row[1],
            'compras_mes': row[2],
            'clientes_nuevos': row[3],
            'stock_critico': row[4],
            'cajas_abiertas': row[5],
        }

    # =====================================
    # VENTAS 7 DIAS
    # =====================================
    with connection.cursor() as cursor:

        cursor.execute("EXEC sp_dashboard_ventas_7dias")

        rows = cursor.fetchall()

        ventas_labels = []
        ventas_data = []

        for r in rows:

            ventas_labels.append(
                r[0].strftime('%d/%m')
            )

            ventas_data.append(
                float(r[1])
            )

    # =====================================
    # TOP PRODUCTOS
    # =====================================
    with connection.cursor() as cursor:

        cursor.execute("EXEC sp_dashboard_top_productos")

        productos = cursor.fetchall()

    # =====================================
    # TOP EMPLEADOS
    # =====================================
    with connection.cursor() as cursor:

        cursor.execute("EXEC sp_dashboard_top_empleados")

        empleados_top = cursor.fetchall()

    context = {

    'empleado': empleado,
    'rol_usuario': empleado.rol.nombre.lower(),

    'kpis': kpis,

    'ventas_labels': json.dumps(ventas_labels),
    'ventas_data': json.dumps(ventas_data),

    'productos': productos,
    'empleados_top': empleados_top,
}
    return render(
        request,
        'empleados/dashboard_gerente.html',
        context
    )

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
# LISTAR USUARIOS
# =========================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q

@login_required
def usuarios_view(request):

    empleado_actual = Empleado.objects.select_related(
        'rol',
        'ubicacion',
        'user'
    ).get(user=request.user)

    # 🔒 FILTRO POR ROL
    if empleado_actual.rol.nombre.lower() == "administrador":

        empleados = Empleado.objects.select_related(
            'user',
            'rol',
            'ubicacion',
            'estado'
        ).all()

    else:

        empleados = Empleado.objects.select_related(
            'user',
            'rol',
            'ubicacion',
            'estado'
        ).filter(
            Q(ubicacion=empleado_actual.ubicacion) |
            Q(ubicacion__tipo__iexact="Bodega")
        ).distinct()

    # ❌ excluir roles administrativos
    roles = Rol.objects.exclude(
        nombre__icontains="administrador"
    ).exclude(
        nombre__icontains="gerente"
    )

    # ubicaciones completas
    ubicaciones = Ubicacion.objects.all()

    # estados
    estados = Estado.objects.filter(
        nombre__iexact="Activo"
    ) | Estado.objects.filter(
        nombre__iexact="Inactivo"
    )

    return render(request, 'empleados/usuarios.html', {

        'empleados': empleados,
        'roles': roles,
        'ubicaciones': ubicaciones,
        'estados': estados

    })

# =========================
# CREAR USUARIO
# =========================
@login_required
def crear_usuario(request):

    if request.method != "POST":
        return redirect('usuarios')

    email = request.POST.get('email', '').strip()
    username = request.POST.get('username', '').strip()

    # validación duplicados
    if User.objects.filter(email=email).exists():
        messages.error(request, "El email ya existe")
        return redirect('usuarios')

    if User.objects.filter(username=username).exists():
        messages.error(request, "El usuario ya existe")
        return redirect('usuarios')

    user = User.objects.create_user(
        username=username,
        email=email,
        password=request.POST.get('password'),
        first_name=request.POST.get('nombre'),
        last_name=request.POST.get('apellido')
    )

    # estado fijo activo (según tu lógica)
    estado_activo = Estado.objects.get(nombre__iexact="Activo")

    Empleado.objects.create(
        user=user,
        rol_id=request.POST.get('rol_id'),
        ubicacion_id=request.POST.get('ubicacion_id'),
        estado=estado_activo
    )

    messages.success(request, "Usuario creado correctamente")
    return redirect('usuarios')


# =========================
# BLOQUEAR USUARIO
# =========================
@login_required
def bloquear_usuario(request, user_id):

    user = get_object_or_404(User, id=user_id)

    # evitar auto-bloqueo
    if request.user.id == user.id:
        messages.warning(request, "No puedes bloquearte a ti mismo")
        return redirect('usuarios')

    user.is_active = False
    user.save()

    messages.success(request, "Usuario bloqueado")
    return redirect('usuarios')


# =========================
# DESBLOQUEAR USUARIO
# =========================
@login_required
def desbloquear_usuario(request, user_id):

    user = get_object_or_404(User, id=user_id)

    user.is_active = True
    user.save()

    messages.success(request, "Usuario desbloqueado")
    return redirect('usuarios')

# =========================
# EDITAR USUARIO
# =========================
@login_required
def editar_usuario(request):

    if request.method != "POST":
        return redirect('usuarios')

    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)

    email = request.POST.get('email', '').strip()
    username = request.POST.get('username', '').strip()

    # validación duplicados excluyendo actual
    if User.objects.exclude(id=user_id).filter(email=email).exists():
        messages.error(request, "El email ya existe")
        return redirect('usuarios')

    if User.objects.exclude(id=user_id).filter(username=username).exists():
        messages.error(request, "El usuario ya existe")
        return redirect('usuarios')

    # actualizar user
    user.email = email
    user.username = username
    user.first_name = request.POST.get('nombre')
    user.last_name = request.POST.get('apellido')
    user.save()

    # actualizar empleado
    emp = get_object_or_404(Empleado, user=user)

    emp.rol_id = request.POST.get('rol_id')
    emp.ubicacion_id = request.POST.get('ubicacion_id')
    emp.save()

    messages.success(request, "Usuario actualizado correctamente")
    return redirect('usuarios')


# =========================
# REGISTRO CLIENTE ONLINE
# =========================
def registro_cliente_view(request):

    if request.method != 'POST':
        return render(request, 'registro_cliente.html')

    try:

        with transaction.atomic():

            # =========================
            # DATOS PERSONALES
            # =========================
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()

            nombre = request.POST.get('nombre', '').strip()
            apellido = request.POST.get('apellido', '').strip()
            identificacion = request.POST.get('identificacion', '').strip()

            # =========================
            # LISTAS DIRECCIONES
            # =========================
            paises = request.POST.getlist('pais[]')
            departamentos = request.POST.getlist('departamento[]')
            ciudades = request.POST.getlist('ciudad[]')
            detalles = request.POST.getlist('detalle[]')
            tipos_direccion = request.POST.getlist('tipo_direccion[]')

            # =========================
            # LISTAS TELÉFONOS
            # =========================
            telefonos = request.POST.getlist('telefono[]')
            operadoras = request.POST.getlist('operadora[]')
            tipos_tel = request.POST.getlist('tipo_tel[]')

            # =========================
            # VALIDACIONES
            # =========================
            if not all([
                email,
                password,
                nombre,
                apellido,
                identificacion
            ]):

                messages.error(
                    request,
                    "Todos los campos son obligatorios"
                )

                return redirect('registro_cliente')

            if not validar_email(email):

                messages.error(request, "Correo inválido")

                return redirect('registro_cliente')

            if not validar_password(password):

                messages.error(
                    request,
                    "La contraseña debe tener mínimo 6 caracteres y un número"
                )

                return redirect('registro_cliente')

            # username/email únicos
            if User.objects.filter(username=email).exists():

                messages.error(request, "El correo ya existe")

                return redirect('registro_cliente')

            if User.objects.filter(email=email).exists():

                messages.error(request, "El email ya existe")

                return redirect('registro_cliente')

            # identificación única
            if Cliente.objects.filter(
                identificacion=identificacion
            ).exists():

                messages.error(
                    request,
                    "La identificación ya existe"
                )

                return redirect('registro_cliente')

            # =========================
            # VALIDAR DIRECCIONES
            # =========================
            direcciones_validas = 0

            for i in range(len(paises)):

                pais = paises[i].strip()
                depto = departamentos[i].strip()
                ciudad = ciudades[i].strip()
                detalle = detalles[i].strip()

                if pais and depto and ciudad and detalle:
                    direcciones_validas += 1

            if direcciones_validas == 0:

                messages.error(
                    request,
                    "Debes agregar al menos una dirección"
                )

                return redirect('registro_cliente')

            # =========================
            # VALIDAR TELÉFONOS
            # =========================
            telefonos_validos = 0

            for tel in telefonos:

                tel = tel.strip()

                if tel:

                    if not tel.isdigit():

                        messages.error(
                            request,
                            "Todos los teléfonos deben ser numéricos"
                        )

                        return redirect('registro_cliente')

                    telefonos_validos += 1

            if telefonos_validos == 0:

                messages.error(
                    request,
                    "Debes ingresar al menos un teléfono"
                )

                return redirect('registro_cliente')

            # =========================
            # ESTADO ACTIVO
            # =========================
            estado_activo = Estado.objects.get(
                nombre__iexact="Activo"
            )

            # =========================
            # CREAR USER
            # =========================
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=nombre,
                last_name=apellido
            )

            # =========================
            # CREAR CLIENTE
            # =========================
            cliente = Cliente.objects.create(
                user=user,
                identificacion=identificacion,
                nombre=nombre,
                apellido=apellido
            )

            # =========================
            # DIRECCIONES
            # =========================
            for i in range(len(paises)):

                pais = paises[i].strip()
                depto = departamentos[i].strip()
                ciudad = ciudades[i].strip()
                detalle = detalles[i].strip()

                if pais and depto and ciudad and detalle:

                    direccion = Direccion.objects.create(
                        pais=pais,
                        departamento=depto,
                        ciudad=ciudad,
                        detalle=detalle
                    )

                    ClienteDireccion.objects.create(
                        cliente=cliente,
                        direccion=direccion,
                        estado=estado_activo,
                        tipo=tipos_direccion[i]
                        if i < len(tipos_direccion)
                        else "Casa"
                    )

            # =========================
            # TELÉFONOS
            # =========================
            for i in range(len(telefonos)):

                numero = telefonos[i].strip()

                if numero:

                    TelefonoCliente.objects.create(
                        cliente=cliente,
                        estado=estado_activo,
                        numero=numero,
                        operadora=operadoras[i]
                        if i < len(operadoras)
                        else "",
                        tipo=tipos_tel[i]
                        if i < len(tipos_tel)
                        else ""
                    )

            messages.success(
                request,
                "Cuenta creada correctamente"
            )

            return redirect('login')

    except Exception as e:

        messages.error(
            request,
            f"Error inesperado: {str(e)}"
        )

        return redirect('registro_cliente')


# =========================
# LISTAR CLIENTES
# =========================
@login_required
def clientes_view(request):

    clientes = Cliente.objects.select_related(
        'user'
    ).all().order_by('-cliente_id')

    return render(request, 'empleados/clientes.html', {
        'clientes': clientes
    })


# =========================
# CREAR CLIENTE FÍSICO
# =========================
@login_required
def crear_cliente(request):

    origen = request.POST.get('origen', 'clientes')

    def redireccion():

        if origen == 'ventas':
            return redirect('ventas')

        return redirect('clientes')

    if request.method != 'POST':
        return redireccion()

    try:

        with transaction.atomic():

            # =========================
            # DATOS PERSONALES
            # =========================
            nombre = request.POST.get(
                'nombre',
                ''
            ).strip()

            apellido = request.POST.get(
                'apellido',
                ''
            ).strip()

            identificacion = request.POST.get(
                'identificacion',
                ''
            ).strip()

            # =========================
            # LISTAS
            # =========================
            paises = request.POST.getlist('pais[]')
            departamentos = request.POST.getlist('departamento[]')
            ciudades = request.POST.getlist('ciudad[]')
            detalles = request.POST.getlist('detalle[]')
            tipos_direccion = request.POST.getlist('tipo_direccion[]')

            telefonos = request.POST.getlist('telefono[]')
            operadoras = request.POST.getlist('operadora[]')
            tipos_tel = request.POST.getlist('tipo_tel[]')

            # =========================
            # VALIDACIONES
            # =========================
            if not nombre or not apellido or not identificacion:

                messages.error(
                    request,
                    "Todos los campos son obligatorios"
                )

                return redireccion()

            # =========================
            # IDENTIFICACIÓN ÚNICA
            # =========================
            if Cliente.objects.filter(
                identificacion=identificacion
            ).exists():

                messages.error(
                    request,
                    "La identificación ya existe"
                )

                return redireccion()

            # =========================
            # VALIDAR TELÉFONOS
            # =========================
            telefonos_validos = []

            for tel in telefonos:

                tel = tel.strip()

                if tel:

                    telefono_limpio = tel.replace('-', '')

                    if not telefono_limpio.isdigit():

                        messages.error(
                            request,
                            "Los teléfonos deben ser numéricos"
                        )

                        return redireccion()

                    telefonos_validos.append(
                        telefono_limpio
                    )

            if len(telefonos_validos) == 0:

                messages.error(
                    request,
                    "Debes agregar al menos un teléfono"
                )

                return redireccion()

            # =========================
            # ESTADO ACTIVO
            # =========================
            estado_activo = Estado.objects.filter(
                nombre__iexact='Activo'
            ).first()

            if not estado_activo:

                messages.error(
                    request,
                    "No existe el estado ACTIVO"
                )

                return redireccion()

            # =========================
            # CREAR CLIENTE
            # =========================
            cliente = Cliente.objects.create(
                nombre=nombre,
                apellido=apellido,
                identificacion=identificacion
            )

            # =========================
            # GUARDAR DIRECCIONES
            # =========================
            total_direcciones = min(
                len(paises),
                len(departamentos),
                len(ciudades),
                len(detalles)
            )

            for i in range(total_direcciones):

                pais = paises[i].strip()
                depto = departamentos[i].strip()
                ciudad = ciudades[i].strip()
                detalle = detalles[i].strip()

                if not all([
                    pais,
                    depto,
                    ciudad,
                    detalle
                ]):
                    continue

                direccion = Direccion.objects.create(
                    pais=pais,
                    departamento=depto,
                    ciudad=ciudad,
                    detalle=detalle
                )

                ClienteDireccion.objects.create(
                    cliente=cliente,
                    direccion=direccion,
                    estado=estado_activo,
                    tipo=(
                        tipos_direccion[i]
                        if i < len(tipos_direccion)
                        else "Casa"
                    )
                )

            # =========================
            # GUARDAR TELÉFONOS
            # =========================
            for i in range(len(telefonos)):

                numero = telefonos[i].strip()

                if not numero:
                    continue

                numero = numero.replace('-', '')

                operadora = (
                    operadoras[i]
                    if i < len(operadoras)
                    else ""
                )

                tipo = (
                    tipos_tel[i]
                    if i < len(tipos_tel)
                    else "Personal"
                )

                TelefonoCliente.objects.create(
                    cliente=cliente,
                    estado=estado_activo,
                    numero=numero,
                    operadora=operadora,
                    tipo=tipo
                )

            messages.success(
                request,
                "Cliente físico creado correctamente"
            )

            return redireccion()

    except Exception as e:

        print("ERROR CREAR CLIENTE:", str(e))

        messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redireccion()

# =========================
# EDITAR CLIENTE
# =========================
@login_required
def editar_cliente(request):

    if request.method != 'POST':
        return redirect('clientes')

    try:

        with transaction.atomic():

            cliente_id = request.POST.get('cliente_id')

            cliente = get_object_or_404(
                Cliente,
                cliente_id=cliente_id
            )

            nombre = request.POST.get(
                'nombre',
                ''
            ).strip()

            apellido = request.POST.get(
                'apellido',
                ''
            ).strip()

            identificacion = request.POST.get(
                'identificacion',
                ''
            ).strip()

            # =========================
            # VALIDACIONES
            # =========================

            if not all([
                nombre,
                apellido,
                identificacion
            ]):

                messages.error(
                    request,
                    "Todos los campos son obligatorios"
                )

                return redirect('clientes')

            existe = Cliente.objects.exclude(
                cliente_id=cliente.cliente_id
            ).filter(
                identificacion=identificacion
            ).exists()

            if existe:

                messages.error(
                    request,
                    "La identificación ya existe"
                )

                return redirect('clientes')

            # =========================
            # ACTUALIZAR CLIENTE
            # =========================

            cliente.nombre = nombre
            cliente.apellido = apellido
            cliente.identificacion = identificacion

            cliente.save()

            # =========================
            # ACTUALIZAR USER
            # =========================

            if cliente.user:

                cliente.user.first_name = nombre
                cliente.user.last_name = apellido

                cliente.user.save()

            # =========================
            # ESTADOS
            # =========================

            estado_inactivo = Estado.objects.get(
                nombre__iexact='Inactivo'
            )

            estado_activo = Estado.objects.get(
                nombre__iexact='Activo'
            )

            # ==================================================
            # TELÉFONOS
            # ==================================================

            telefono_ids = request.POST.getlist('telefono_id[]')
            telefonos = request.POST.getlist('telefono[]')
            operadoras = request.POST.getlist('operadora[]')
            tipos_tel = request.POST.getlist('tipo_tel[]')
            telefonos_eliminar = request.POST.getlist(
                'telefono_eliminar[]'
            )

            for i in range(len(telefonos)):

                telefono_id = (
                    telefono_ids[i].strip()
                    if i < len(telefono_ids)
                    else ''
                )

                numero = telefonos[i].strip()

                eliminar = (
                    telefonos_eliminar[i]
                    if i < len(telefonos_eliminar)
                    else '0'
                )

                # =========================
                # NUEVO VACÍO
                # =========================

                if not numero:

                    continue

                numero = numero.replace('-', '')

                # =========================
                # VALIDAR
                # =========================

                if not numero.isdigit():

                    messages.error(
                        request,
                        "Los teléfonos deben ser numéricos"
                    )

                    return redirect('clientes')

                operadora = (
                    operadoras[i]
                    if i < len(operadoras)
                    else ''
                )

                tipo = (
                    tipos_tel[i]
                    if i < len(tipos_tel)
                    else 'Personal'
                )

                # =========================
                # ACTUALIZAR EXISTENTE
                # =========================

                if telefono_id:

                    telefono = TelefonoCliente.objects.get(
                        telefono_id=telefono_id
                    )

                    # ELIMINAR
                    if eliminar == '1':

                        telefono.estado = estado_inactivo
                        telefono.save()

                        continue

                    telefono.numero = numero
                    telefono.operadora = operadora
                    telefono.tipo = tipo
                    telefono.estado = estado_activo

                    telefono.save()

                # =========================
                # CREAR NUEVO
                # =========================

                else:

                    TelefonoCliente.objects.create(
                        cliente=cliente,
                        estado=estado_activo,
                        numero=numero,
                        operadora=operadora,
                        tipo=tipo
                    )

            # ==================================================
            # DIRECCIONES
            # ==================================================

            direccion_ids = request.POST.getlist('direccion_id[]')

            paises = request.POST.getlist('pais[]')
            departamentos = request.POST.getlist('departamento[]')
            ciudades = request.POST.getlist('ciudad[]')
            detalles = request.POST.getlist('detalle[]')
            tipos_direccion = request.POST.getlist(
                'tipo_direccion[]'
            )

            direcciones_eliminar = request.POST.getlist(
                'direccion_eliminar[]'
            )

            for i in range(len(paises)):

                direccion_id = (
                    direccion_ids[i].strip()
                    if i < len(direccion_ids)
                    else ''
                )

                pais = paises[i].strip()
                depto = departamentos[i].strip()
                ciudad = ciudades[i].strip()
                detalle = detalles[i].strip()

                eliminar = (
                    direcciones_eliminar[i]
                    if i < len(direcciones_eliminar)
                    else '0'
                )

                # =========================
                # VALIDAR VACÍOS
                # =========================

                if not all([
                    pais,
                    depto,
                    ciudad,
                    detalle
                ]):

                    continue

                tipo = (
                    tipos_direccion[i]
                    if i < len(tipos_direccion)
                    else 'Casa'
                )

                # =========================
                # ACTUALIZAR EXISTENTE
                # =========================

                if direccion_id:

                    cliente_direccion = ClienteDireccion.objects.get(
                        cliente_direccion_id=direccion_id
                    )

                    # ELIMINAR
                    if eliminar == '1':

                        cliente_direccion.estado = estado_inactivo
                        cliente_direccion.save()

                        continue

                    direccion = cliente_direccion.direccion

                    direccion.pais = pais
                    direccion.departamento = depto
                    direccion.ciudad = ciudad
                    direccion.detalle = detalle

                    direccion.save()

                    cliente_direccion.tipo = tipo
                    cliente_direccion.estado = estado_activo

                    cliente_direccion.save()

                # =========================
                # CREAR NUEVA
                # =========================

                else:

                    direccion = Direccion.objects.create(
                        pais=pais,
                        departamento=depto,
                        ciudad=ciudad,
                        detalle=detalle
                    )

                    ClienteDireccion.objects.create(
                        cliente=cliente,
                        direccion=direccion,
                        estado=estado_activo,
                        tipo=tipo
                    )

            # =========================
            # SUCCESS
            # =========================

            messages.success(
                request,
                "Cliente actualizado correctamente"
            )

            return redirect('clientes')

    except Exception as e:

        print("ERROR EDITAR CLIENTE:", str(e))

        messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redirect('clientes')

# =========================
# CREAR USER CLIENTE
# =========================
@login_required
def crear_user_cliente(request):

    if request.method != 'POST':
        return redirect('clientes')

    try:

        cliente_id = request.POST.get('cliente_id')

        cliente = get_object_or_404(
            Cliente,
            cliente_id=cliente_id
        )

        if cliente.user:

            messages.warning(
                request,
                "El cliente ya tiene cuenta"
            )

            return redirect('clientes')

        email = request.POST.get(
            'email',
            ''
        ).strip()

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        ).strip()

        # VALIDACIONES
        if not validar_email(email):

            messages.error(
                request,
                "Correo inválido"
            )

            return redirect('clientes')

        if not validar_password(password):

            messages.error(
                request,
                "Contraseña inválida"
            )

            return redirect('clientes')

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "El username ya existe"
            )

            return redirect('clientes')

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "El email ya existe"
            )

            return redirect('clientes')

        # CREAR USER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=cliente.nombre,
            last_name=cliente.apellido
        )

        cliente.user = user
        cliente.save()

        messages.success(
            request,
            "Cuenta online creada correctamente"
        )

        return redirect('clientes')

    except Exception as e:

        messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redirect('clientes')


# =========================
# PERFIL CLIENTE ONLINE
# =========================
@login_required
def perfil_cliente(request):

    try:

        cliente = get_object_or_404(
            Cliente,
            user=request.user
        )

        return render(
            request,
            'clientes/perfil.html',
            {
                'cliente': cliente
            }
        )

    except Exception as e:

        messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redirect('tienda')


# =========================
# EDITAR PERFIL CLIENTE
# =========================
@login_required
def editar_perfil_cliente(request):

    if request.method != 'POST':
        return redirect('perfil_cliente')

    try:

        with transaction.atomic():

            cliente = get_object_or_404(
                Cliente,
                user=request.user
            )

            nombre = request.POST.get(
                'nombre',
                ''
            ).strip()

            apellido = request.POST.get(
                'apellido',
                ''
            ).strip()

            username = request.POST.get(
                'username',
                ''
            ).strip()

            # validar username
            existe = User.objects.exclude(
                id=request.user.id
            ).filter(
                username=username
            ).exists()

            if existe:

                messages.error(
                    request,
                    "El username ya existe"
                )

                return redirect('perfil_cliente')

            # actualizar user
            request.user.username = username
            request.user.first_name = nombre
            request.user.last_name = apellido

            request.user.save()

            # actualizar cliente
            cliente.nombre = nombre
            cliente.apellido = apellido

            cliente.save()

            messages.success(
                request,
                "Perfil actualizado"
            )

            return redirect('perfil_cliente')

    except Exception as e:

        messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redirect('perfil_cliente')


# =========================
# AUTOCOMPLETE CLIENTES
# =========================
def buscar_clientes(request):

    term = request.GET.get('term', '')

    clientes = Cliente.objects.filter(
        nombre__icontains=term
    )[:10]

    data = [
        {
            'id': c.cliente_id,
            'text': str(c)
        }
        for c in clientes
    ]

    return JsonResponse(data, safe=False)
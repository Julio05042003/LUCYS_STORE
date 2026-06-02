from decimal import Decimal
from datetime import date
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from apps.inventario.models import Producto
from apps.usuarios.models import Empleado, Direccion, Estado, Bodega
from .models import *



# =========================================
# LISTAR COMPRAS
# =========================================
@login_required
def compras_view(request):

    compras = Compra.objects.select_related(
        'proveedor',
        'bodega',
        'empleado'
    ).all().order_by('-id')

    proveedores = Proveedor.objects.all().order_by(
        'nombre'
    )

    bodegas = Bodega.objects.all()

    estados = Estado.objects.all()

    return render(
        request,
        'empleados/compras.html',
        {

            'compras': compras,
            'proveedores': proveedores,
            'bodegas': bodegas,
            'estados': estados,
            'today': date.today(),

        }
    )


# =========================================
# CREAR COMPRA
# =========================================
@login_required
def crear_compra(request):

    if request.method != 'POST':

        return JsonResponse({
            'status': 'error',
            'error': 'Método no permitido'
        })

    try:

        with transaction.atomic():

            data = json.loads(request.body)

            empleado = Empleado.objects.get(empleado_id=data['empleado'])
            proveedor = Proveedor.objects.get(id=data['proveedor'])
            bodega = Bodega.objects.get(bodega_id=data['bodega'])

            # CREAR COMPRA
            compra = Compra.objects.create(

                proveedor=proveedor,
                bodega=bodega,
                empleado=empleado,
                total=0

            )

            total = Decimal('0.00')

            # DETALLES
            for item in data['productos']:
                producto = Producto.objects.get(producto_id=item['producto_id'])

                # VALIDAR SI YA EXISTE EN ALGUNA COMPRA
                existe_compra = DetalleCompra.objects.filter(
                    producto=producto
                ).exists()

                if existe_compra:
                    raise Exception(
                        f'El producto "{producto.nombre}" ya fue comprado anteriormente.'
                    )
                
                cantidad = int(item['cantidad'])
                precio = Decimal(str(item['precio']))
                subtotal = (cantidad * precio)
                total += subtotal

                DetalleCompra.objects.create(
                    compra=compra,
                    producto=producto,
                    cantidad=cantidad,
                    precio=precio

                )

            compra.total = total
            compra.save()

            return JsonResponse({
                'status': 'ok'
            })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)

        })


# =========================================
# PROVEEDORES
# =========================================
@login_required
def proveedores(request):

    busqueda = request.GET.get('q','').strip()

    proveedores = Proveedor.objects.select_related(
        'direccion'
    ).prefetch_related(
        'telefonos__estado'
    ).all().order_by(
        'nombre'
    )

    # FILTRO
    if busqueda:
        proveedores = proveedores.filter(nombre__icontains=busqueda)

    # PRODUCTOS POR PROVEEDOR
    for proveedor in proveedores:
        
        # TELEFONOS ACTIVOS
        proveedor.telefonos_activos = proveedor.telefonos.filter(
            estado__nombre='Activo'
        )

        productos_ids = DetalleCompra.objects.filter(
            compra__proveedor=proveedor
        ).values_list(
            'producto_id',
            flat=True
        ).distinct()

        proveedor.productos_proveedor = Producto.objects.filter(
            producto_id__in=productos_ids
        ).select_related(
            'marca',
            'categoria'
        )

    return render(
        request,
        'empleados/proveedores.html',
        {
            'proveedores': proveedores,
            'busqueda': busqueda
        }
    )


# =========================================
# CREAR PROVEEDOR
# =========================================
@login_required
def crear_proveedor(request):

    origen = request.POST.get(
        'origen',
        'proveedores'
    )

    def redireccion():

        if origen == 'compras':
            return redirect('compras')

        return redirect('proveedores')

    if request.method != 'POST':

        return redireccion()

    try:

        with transaction.atomic():

            nombre = request.POST.get('nombre','').strip()
            contacto = request.POST.get('contacto','').strip()
            correo = request.POST.get('correo','').strip()
            pais = request.POST.get('pais','').strip()
            departamento = request.POST.get('departamento','').strip()
            ciudad = request.POST.get('ciudad','').strip()
            detalle = request.POST.get('detalle','').strip()

            # VALIDACIONES
            if not nombre:
                messages.error(request,'El nombre es obligatorio')
                return redireccion()

            if not all([
                pais,
                departamento,
                ciudad,
                detalle
            ]):

                messages.error(request,'La dirección es obligatoria')
                return redireccion()

            # VALIDAR NOMBRE
            existe = Proveedor.objects.filter(
                nombre__iexact=nombre
            ).exists()

            if existe:
                messages.error(request,'Ya existe un proveedor con ese nombre')
                return redireccion()

            # TELEFONOS
            telefonos = request.POST.getlist('numero[]')
            operadoras = request.POST.getlist('operadora[]')
            tipos = request.POST.getlist('tipo[]')
            telefonos_validos = []

            for tel in telefonos:

                tel = tel.strip()

                if tel:

                    telefono_limpio = tel.replace('-','')

                    if not telefono_limpio.isdigit():
                        messages.error(request,'Los teléfonos deben ser numéricos')
                        return redireccion()

                    telefonos_validos.append(
                        telefono_limpio
                    )

            if len(telefonos_validos) == 0:
                messages.error(request,'Debes agregar al menos un teléfono')
                return redireccion()

            # ESTADO ACTIVO
            estado_activo = Estado.objects.filter(
                nombre__iexact='Activo'
            ).first()

            if not estado_activo:
                messages.error(request,'No existe el estado ACTIVO')
                return redireccion()

            # CREAR DIRECCION
            direccion = Direccion.objects.create(
                pais=pais,
                departamento=departamento,
                ciudad=ciudad,
                detalle=detalle
            )

            # CREAR PROVEEDOR
            proveedor = Proveedor.objects.create(
                direccion=direccion,
                nombre=nombre,
                contacto=contacto,
                correo=correo
            )

            # GUARDAR TELEFONOS
            for i in range(len(telefonos)):

                numero = telefonos[i].strip()

                if not numero:
                    continue

                numero = numero.replace('-','')
                operadora = (operadoras[i] if i < len(operadoras) else '')
                tipo = (tipos[i]if i < len(tipos)else 'Ventas')

                TelefonoProveedor.objects.create(
                    proveedor=proveedor,
                    estado=estado_activo,
                    numero=numero,
                    operadora=operadora,
                    tipo=tipo

                )

            messages.success(request,'Proveedor registrado correctamente')
            return redireccion()

    except Exception as e:
        messages.error(request,f'Error: {str(e)}')
        return redireccion()


# =========================================
# EDITAR PROVEEDOR
# =========================================
@login_required
def editar_proveedor(request):

    origen = request.POST.get(
        'origen',
        'proveedores'
    )

    def redireccion():

        if origen == 'compras':
            return redirect('compras')

        return redirect('proveedores')

    if request.method != 'POST':

        return redireccion()

    try:

        with transaction.atomic():

            proveedor_id = request.POST.get('proveedor_id')
            proveedor = get_object_or_404(Proveedor,id=proveedor_id)
            nombre = request.POST.get('nombre', '').strip()
            contacto = request.POST.get('contacto','').strip()
            correo = request.POST.get('correo','').strip()

            # VALIDAR NOMBRE
            existe = Proveedor.objects.exclude(
                id=proveedor.id
            ).filter(
                nombre__iexact=nombre
            ).exists()

            if existe:
                messages.error(request,'Ya existe un proveedor con ese nombre')
                return redireccion()

            # ACTUALIZAR PROVEEDOR

            proveedor.nombre = nombre
            proveedor.contacto = contacto
            proveedor.correo = correo

            proveedor.save()

            # DIRECCION
            direccion = proveedor.direccion
            direccion.pais = request.POST.get('pais')
            direccion.departamento = request.POST.get('departamento')
            direccion.ciudad = request.POST.get('ciudad')
            direccion.detalle = request.POST.get('detalle')
            direccion.save()

            # ESTADOS
            estado_activo = Estado.objects.get(nombre__iexact='Activo')
            estado_inactivo = Estado.objects.get(nombre__iexact='Inactivo')

            # TELEFONOS
            telefono_ids = request.POST.getlist('telefono_id[]')
            telefonos = request.POST.getlist('numero[]')
            operadoras = request.POST.getlist('operadora[]')
            tipos = request.POST.getlist('tipo[]')
            telefonos_eliminar = request.POST.getlist('telefono_eliminar[]')

            for i in range(len(telefonos)):

                telefono_id = (telefono_ids[i] if i < len(telefono_ids) else '')
                numero = telefonos[i].strip()
                operadora = (operadoras[i] if i < len(operadoras) else '')
                tipo = (tipos[i] if i < len(tipos) else 'Ventas')
                eliminar = (telefonos_eliminar[i] if i < len(telefonos_eliminar) else '0')

                # NUEVO TELEFONO
                if telefono_id == '':

                    if not numero:
                        continue

                    numero = numero.replace('-','')

                    if not numero.isdigit():
                        messages.error(request,'Los teléfonos deben ser numéricos')
                        return redireccion()

                    TelefonoProveedor.objects.create(
                        proveedor=proveedor,
                        estado=estado_activo,
                        numero=numero,
                        operadora=operadora,
                        tipo=tipo
                    )

                    continue

                telefono = TelefonoProveedor.objects.get(id=telefono_id)

                # ELIMINAR
                if eliminar == '1':
                    telefono.estado = estado_inactivo
                    telefono.save()
                    continue

                # VALIDAR
                numero = numero.replace('-','')

                if not numero.isdigit():
                    messages.error(request,'Los teléfonos deben ser numéricos')
                    return redireccion()

                # ACTUALIZAR
                telefono.numero = numero
                telefono.operadora = operadora
                telefono.tipo = tipo
                telefono.estado = estado_activo

                telefono.save()


            messages.success(request,'Proveedor actualizado correctamente')
            return redireccion()

    except Exception as e:
        messages.error(request,f'Error: {str(e)}')
        return redireccion()
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.db import transaction
from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import *
from apps.usuarios.models import Estado, Bodega, Empleado

import json

@login_required
def validar_stock(request):

    producto_id = request.GET.get('producto_id')
    cantidad = int(request.GET.get('cantidad'))

    empleado = request.user.empleado

    inventario = Inventario.objects.filter(
        producto_id=producto_id,
        bodega=empleado.sucursal.bodega
    ).first()

    if not inventario:
        return JsonResponse({
            'ok': False,
            'stock': 0
        })

    if cantidad > inventario.stock:
        return JsonResponse({
            'ok': False,
            'stock': inventario.stock
        })

    return JsonResponse({
        'ok': True
    }) 

def es_admin_o_bodega(user):
    empleado = Empleado.objects.get(user=user)
    return empleado.rol.nombre in ["Administrador", "Gerente", "Bodega"]


# SOLO VISUALIZACIÓN (SIN CRUD PRODUCTO)
@login_required
@login_required
def inventario_view(request):

    empleado = Empleado.objects.select_related(
        'rol',
        'sucursal__bodega'
    ).get(user=request.user)

    categorias = Categoria.objects.all()

    marcas = Marca.objects.all()

    # ABRIR MODAL SI EXISTE ERROR
    abrir_modal = request.session.pop('abrir_modal', '')

    # PRODUCTOS
    productos = Producto.objects.select_related(
        'categoria',
        'marca',
        'estado'
    )

    # =====================================
    # SOLO BODEGA SI NO ES ADMIN
    # =====================================

    if empleado.rol.nombre != "Administrador":

        productos = productos.filter(

            Q(inventario__bodega=empleado.sucursal.bodega) |

            Q(inventario__isnull=True)

        ).distinct()

    # =====================================
    # ARMAR DATA
    # =====================================

    data = []

    for p in productos:

        # =====================================
        # STOCK
        # =====================================

        if empleado.rol.nombre == "Administrador":

            stock = Inventario.objects.filter(
                producto=p
            ).aggregate(
                total=Sum('stock')
            )['total'] or 0

        else:

            stock = Inventario.objects.filter(
                producto=p,
                bodega=empleado.sucursal.bodega
            ).aggregate(
                total=Sum('stock')
            )['total'] or 0

        data.append({

            'id': p.producto_id,

            'codigo': p.codigo,

            'nombre': p.nombre,

            'descripcion': p.descripcion,

            'categoria': (
                p.categoria.nombre
                if p.categoria else ''
            ),

            'categoria_id': p.categoria_id,

            'marca': (
                p.marca.nombre
                if p.marca else ''
            ),

            'marca_id': p.marca_id,

            'stock': stock,

            'precio_venta': p.precio_venta,

            'precio': p.precio_c,

            'estado': (
                p.estado.nombre
                if p.estado else ''
            ),

            'imagen': (
                p.imagen.url
                if p.imagen else None
            )
        })

    return render(
        request,
        'empleados/inventario.html',
        {
            'productos': data,
            'categorias': categorias,
            'marcas': marcas,
            'rol': empleado.rol.nombre,
            'abrir_modal': abrir_modal
        }
    )
    
    
    
# KARDEX
@login_required
def obtener_kardex(request, producto_id):

    empleado = request.user.empleado

    movimientos = Kardex.objects.filter(
        producto_id=producto_id
    )

    # SOLO ADMIN VE TODO
    if empleado.rol.nombre != "Administrador":

        movimientos = movimientos.filter(
            bodega=empleado.sucursal.bodega
        )

    movimientos = movimientos.order_by('-fecha')

    data = []

    for m in movimientos:

        data.append({
            'fecha': m.fecha.strftime('%d/%m/%Y'),
            'tipo': m.tipo,
            'descripcion': m.descripcion,
            'cantidad': m.cantidad,
            'saldo': m.saldo
        })

    return JsonResponse({'kardex': data})


@login_required
def kardex_view(request, id):

    empleado = Empleado.objects.select_related(
        'sucursal',
        'rol'
    ).get(user=request.user)

    producto = get_object_or_404(
        Producto.objects.select_related(
            'categoria',
            'marca',
            'estado'
        ),
        pk=id
    )

    # =========================================
    # FILTRO SEGÚN ROL
    # =========================================

    if empleado.rol.nombre == "Administrador":

        # ADMIN Y GERENTE VEN TODO
        movimientos_qs = Kardex.objects.select_related(
            'bodega'
        ).filter(
            producto_id=id
        ).order_by('fecha')

        stock = Inventario.objects.filter(
            producto_id=id
        ).aggregate(
            total=Sum('stock')
        )['total'] or 0

    else:

        # EMPLEADOS NORMALES SOLO SU BODEGA
        movimientos_qs = Kardex.objects.select_related(
            'bodega'
        ).filter(
            producto_id=id,
            bodega=empleado.sucursal.bodega
        ).order_by('fecha')

        stock = Inventario.objects.filter(
            producto_id=id,
            bodega=empleado.sucursal.bodega
        ).aggregate(
            total=Sum('stock')
        )['total'] or 0

    # =========================================
    # ARMAR RESPUESTA
    # =========================================

    data = []
    ultimo_precio = 0

    for m in movimientos_qs:

        precio = m.Precio or 0
        cantidad = m.cantidad or 0
        saldo = m.saldo or 0

        valor = cantidad * precio
        saldo_valor = saldo * precio

        ultimo_precio = precio

        data.append({
            'fecha': m.fecha,
            'tipo': m.tipo,
            'documento': m.documento,

            'bodega': m.bodega.nombre,

            'cantidad': cantidad,
            'saldo': saldo,

            'precio': precio,
            'valor': valor,
            'saldo_valor': saldo_valor
        })

    return render(
        request,
        'empleados/kardex.html',
        {
            'producto': producto,
            'movimientos': data,
            'stock': stock,
            'precio_c': producto.precio_c
        }
    )

@login_required
def kardex_global_view(request):

    empleado = Empleado.objects.select_related(
        'sucursal',
        'rol',
        'sucursal__bodega'
    ).get(user=request.user)

    # =====================================
    # PRODUCTOS
    # =====================================

    productos = Producto.objects.select_related(
        'categoria',
        'marca',
        'estado'
    )

    # SOLO ADMIN VE TODO
    if empleado.rol.nombre != "Administrador":

        productos = productos.filter(
            inventario__bodega=empleado.sucursal.bodega
        ).distinct()

    # =====================================
    # FILTROS
    # =====================================

    busqueda = request.GET.get('busqueda')
    categoria = request.GET.get('categoria')
    estado = request.GET.get('estado')

    if busqueda:

        productos = productos.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo__icontains=busqueda)
        )

    if categoria and categoria != "TODAS":

        productos = productos.filter(
            categoria_id=categoria
        )

    if estado and estado != "TODOS":

        productos = productos.filter(
            estado__nombre=estado
        )

    # =====================================
    # ARMAR DATOS
    # =====================================

    data = []

    for p in productos:

        # =====================================
        # INVENTARIO SEGÚN ROL
        # =====================================

        inventario_qs = Inventario.objects.filter(
            producto=p
        )

        kardex_qs = Kardex.objects.filter(
            producto=p
        )

        if empleado.rol.nombre != "Administrador":

            inventario_qs = inventario_qs.filter(
                bodega=empleado.sucursal.bodega
            )

            kardex_qs = kardex_qs.filter(
                bodega=empleado.sucursal.bodega
            )

        # =====================================
        # STOCK
        # =====================================

        stock = inventario_qs.aggregate(
            total=Sum('stock')
        )['total'] or 0

        # =====================================
        # ENTRADAS
        # =====================================

        entradas = kardex_qs.filter(
            tipo='ENTRADA'
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0

        # =====================================
        # SALIDAS
        # =====================================

        salidas = kardex_qs.filter(
            tipo='SALIDA'
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0

        # =====================================
        # VALORES
        # =====================================

        valor_stock = stock * p.precio_c

        data.append({

            'id': p.producto_id,

            'codigo': p.codigo,

            'nombre': p.nombre,

            'categoria': p.categoria.nombre,

            'marca': p.marca.nombre,

            'estado': p.estado.nombre,

            'stock': stock,

            'entradas': entradas,

            'salidas': salidas,

            'precio_costo': p.precio_c,

            'precio_venta': p.precio_venta,

            'valor_stock': valor_stock,

            'imagen': p.imagen.url if p.imagen else None
        })

    return render(
        request,
        'empleados/kardex_global.html',
        {
            'productos': data,

            'categorias': Categoria.objects.all(),

            'busqueda': busqueda or "",

            'categoria': categoria or "TODAS",

            'estado': estado or "TODOS"
        }
    )
    
    
@login_required
@transaction.atomic
def crear_ajuste_inventario(request):

    if request.method != "POST":
        return redirect('kardex_global_view')

    empleado = request.user.empleado

    producto_id = request.POST.get('producto_id')
    tipo = request.POST.get('tipo')
    cantidad = request.POST.get('cantidad')
    motivo = request.POST.get('motivo')
    observacion = request.POST.get('observacion')

    # =========================================
    # VALIDACIONES
    # =========================================

    if not producto_id:
        messages.error(request, "Producto inválido")
        return redirect('kardex_global_view')

    if tipo not in ['ENTRADA', 'SALIDA']:
        messages.error(request, "Tipo inválido")
        return redirect('kardex_global_view')

    if not cantidad:
        messages.error(request, "Ingrese cantidad")
        return redirect('kardex_view', id=producto_id)

    try:
        cantidad = int(cantidad)

    except:
        messages.error(request, "Cantidad inválida")
        return redirect('kardex_view', id=producto_id)

    if cantidad <= 0:
        messages.error(request, "La cantidad debe ser mayor a 0")
        return redirect('kardex_view', id=producto_id)

    # VALIDAR MULTIPLO DE 3
    if cantidad % 3 != 0:
        messages.error(
            request,
            "La cantidad debe ser múltiplo de 3"
        )
        return redirect('kardex_view', id=producto_id)

    # =========================================
    # PRODUCTO
    # =========================================

    producto = get_object_or_404(
        Producto,
        pk=producto_id
    )

    bodega = empleado.sucursal.bodega

    # =========================================
    # INVENTARIO
    # =========================================

    inventario = Inventario.objects.filter(
        producto=producto,
        bodega=bodega
    ).first()

    # SI NO EXISTE INVENTARIO
    if not inventario:

        inventario = Inventario.objects.create(
            producto=producto,
            bodega=bodega,
            stock=0
        )

    # =========================================
    # VALIDAR STOCK PARA SALIDAS
    # =========================================

    if tipo == 'SALIDA':

        if cantidad > inventario.stock:

            messages.error(
                request,
                f'Stock insuficiente. Disponible: {inventario.stock}'
            )

            return redirect('kardex_view', id=producto_id)
        
    
    MOTIVOS_VALIDOS = [
    'PRODUCTO_DAÑADO',
    'PERDIDA',
    'REGALIA',
    'AJUSTE_MANUAL',
    'ERROR_INVENTARIO'
    ]

    if motivo not in MOTIVOS_VALIDOS:
        messages.error(request,'Motivo inválido')
        return redirect('kardex_view', id=producto_id)

    # =========================================
    # GENERAR DOCUMENTO
    # =========================================

    ultimo_ajuste = AjusteInventario.objects.order_by(
        '-ajuste_id'
    ).first()

    numero = 1

    if ultimo_ajuste:
        numero = ultimo_ajuste.ajuste_id + 1

    documento = f'AJUSTE-{numero}'

    # =========================================
    # ACTUALIZAR STOCK
    # =========================================

    if tipo == 'ENTRADA':
        inventario.stock += cantidad

    else:
        inventario.stock -= cantidad

    inventario.save()

    # =========================================
    # CREAR AJUSTE
    # =========================================

    ajuste = AjusteInventario.objects.create(
        producto=producto,
        bodega=bodega,
        empleado=empleado,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
        observacion=observacion
    )

    # =========================================
    # CREAR KARDEX
    # =========================================

    Kardex.objects.create(
        producto=producto,
        bodega=bodega,
        tipo=tipo,
        documento=documento,
        cantidad=cantidad,
        saldo=inventario.stock,
        Precio=producto.precio_c,
        descripcion=f'AJUSTE INVENTARIO - {motivo}'
    )

    messages.success(
        request,
        f'Ajuste registrado correctamente ({documento})'
    )

    return redirect('kardex_view', id=producto.producto_id)

# =========================================
# TRANSFERENCIAS
# =========================================
@login_required
def transferencias_view(request):

    empleado = Empleado.objects.select_related(
        'sucursal',
        'rol',
        'sucursal__bodega'
    ).get(user=request.user)

    bodega_actual = empleado.sucursal.bodega

    # TODAS MENOS LA SUYA
    bodegas = Bodega.objects.exclude(
        pk=bodega_actual.pk
    )

    if empleado.rol.nombre.lower() == "administrador":

        transferencias = Transferencia.objects.select_related(
            'estado',
            'origen',
            'destino',
            'empleado'
        ).all().order_by('-id')

    else:

        transferencias = Transferencia.objects.select_related(
            'estado',
            'origen',
            'destino',
            'empleado'
        ).filter(
            Q(origen=bodega_actual) |
            Q(destino=bodega_actual)
        ).order_by('-id')

    productos = Producto.objects.all()

    productos_data = [
        {
            "id": p.producto_id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "stock": (
                Inventario.objects.filter(
                    producto=p,
                    bodega=bodega_actual
                ).first().stock
                if Inventario.objects.filter(
                    producto=p,
                    bodega=bodega_actual
                ).exists()
                else 0
            )
        }
        for p in productos
    ]
    
    detalles_json = request.session.pop('detalles_transferencia','[]')

    return render(
        request,
        'empleados/transferencias.html',
        {
            'bodegas': bodegas,
            'transferencias': transferencias,
            'empleado': empleado,
            'productos_json': json.dumps(productos_data),
            'detalles_json': detalles_json
        }
    )  
    
    
@login_required
def detalle_transferencia(request, id):

    detalles = DetalleTransferencia.objects.select_related(
        'producto'
    ).filter(
        transferencia_id=id
    )

    data = []

    for d in detalles:

        data.append({
            'producto': d.producto.nombre,
            'cantidad': d.cantidad
        })

    return JsonResponse({
        'detalles': data
    })


@login_required
def crear_transferencia(request):

    if request.method == "POST":

        empleado = Empleado.objects.select_related(
            'sucursal'
        ).get(user=request.user)

        origen = Bodega.objects.get(pk=request.POST['origen_id'])
        destino = Bodega.objects.get(pk=request.POST['destino_id'])

        estado = Estado.objects.get(nombre="Aprobado")

        detalles_json = request.POST.get('detalles', '[]')

        # VALIDAR BODEGAS
        if origen.bodega_id == destino.bodega_id:

            request.session['detalles_transferencia'] = detalles_json

            messages.error(
                request,
                "La bodega destino no puede ser la misma bodega origen"
            )
            return redirect('transferencias')

        # VALIDAR DETALLES
        if not detalles_json:

            messages.error(
                request,
                "No se enviaron productos en el traslado"
            )
            return redirect('transferencias')

        try:
            detalles = json.loads(detalles_json)

        except json.JSONDecodeError:

            request.session['detalles_transferencia'] = detalles_json

            messages.error(
                request,
                "Error en formato de productos"
            )
            return redirect('transferencias')

        if len(detalles) == 0:

            request.session['detalles_transferencia'] = detalles_json

            messages.error(
                request,
                "Debe agregar al menos un producto"
            )
            return redirect('transferencias')

        # VALIDAR STOCK Y MÚLTIPLO DE 3
        for d in detalles:

            producto = Producto.objects.get(
                pk=d['producto']
            )

            cantidad = int(d['cantidad'])

            if cantidad % 3 != 0:

                request.session['detalles_transferencia'] = detalles_json

                messages.error(
                    request,
                    f"La cantidad del producto {producto.nombre} debe ser múltiplo de 3"
                )
                return redirect('transferencias')

            inventario = Inventario.objects.filter(
                producto=producto,
                bodega=origen
            ).first()

            if not inventario:

                request.session['detalles_transferencia'] = detalles_json

                messages.error(
                    request,
                    f"No existe inventario para {producto.nombre} en la bodega origen"
                )
                return redirect('transferencias')

            if cantidad > inventario.stock:

                request.session['detalles_transferencia'] = detalles_json

                messages.error(
                    request,
                    f"Stock insuficiente para {producto.nombre}. Disponible: {inventario.stock}"
                )
                return redirect('transferencias')

        # CREAR TRANSFERENCIA
        transferencia = Transferencia.objects.create(
            origen=origen,
            destino=destino,
            empleado=empleado,
            estado=estado
        )

        # GUARDAR DETALLES
        for d in detalles:

            producto = Producto.objects.get(
                pk=d['producto']
            )

            cantidad = int(d['cantidad'])

            DetalleTransferencia.objects.create(
                transferencia=transferencia,
                producto=producto,
                cantidad=cantidad
            )

        # LIMPIAR SESIÓN
        request.session.pop('detalles_transferencia', None)

        messages.success(
            request,
            "Transferencia creada correctamente"
        )

        return redirect('transferencias')

    return redirect('transferencias')
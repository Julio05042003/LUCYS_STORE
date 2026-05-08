from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse

from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import Inventario, Kardex, Transferencia, DetalleTransferencia
from apps.usuarios.models import Estado, Ubicacion, Empleado

import json

def validar_stock(request):
    producto_id = request.GET.get('producto_id')
    cantidad = int(request.GET.get('cantidad'))
    empleado = request.user.empleado

    inventario = Inventario.objects.filter(
        producto_id=producto_id,
        ubicacion=empleado.ubicacion
    ).first()

    if not inventario:
        return JsonResponse({'ok': False, 'stock': 0})

    if cantidad > inventario.stock:
        return JsonResponse({'ok': False, 'stock': inventario.stock})

    return JsonResponse({'ok': True})
    

def es_admin_o_bodega(user):
    empleado = Empleado.objects.get(user=user)
    return empleado.rol.nombre in ["Admin", "Gerente", "Bodega"]


# 🔹 SOLO VISUALIZACIÓN (SIN CRUD PRODUCTO)
def inventario_view(request):

    productos = Producto.objects.select_related('categoria', 'marca', 'estado')
    empleado = Empleado.objects.select_related('rol').get(user=request.user)

    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()
    

    data = []

    for p in productos:
        stock = Inventario.objects.filter(producto=p).aggregate(
            total=Sum('stock')
        )['total'] or 0
        
        data.append({
            'id': p.producto_id,
            'codigo': p.codigo,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'categoria': p.categoria.nombre,
            'categoria_id': p.categoria_id,
            'marca': p.marca.nombre,
            'marca_id': p.marca_id,
            'stock': stock,
            'precio': p.precio_venta,
            'estado': p.estado.nombre,
            'imagen': p.imagen.url if p.imagen else None
        })

    return render(request, 'empleados/inventario.html', {
        'productos': data,
        'categorias': categorias,   
        'marcas': marcas,           
        'rol': empleado.rol.nombre
    })


# 🔹 KARDEX
def obtener_kardex(request, producto_id):

    movimientos = Kardex.objects.filter(
        producto_id=producto_id
    ).order_by('-fecha')

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

    empleado = Empleado.objects.select_related('ubicacion', 'rol').get(user=request.user)

    producto = Producto.objects.select_related(
        'categoria', 'marca', 'estado'
    ).get(pk=id)

    # =========================================
    # 🔥 FILTRO INTELIGENTE POR ROL
    # =========================================
    if empleado.rol.nombre == "Admin":
        # ADMIN VE TODO
        movimientos_qs = Kardex.objects.filter(
            producto_id=id
        ).order_by('fecha')

        stock = Inventario.objects.filter(
            producto_id=id
        ).aggregate(total=Sum('stock'))['total'] or 0

    else:
        # USUARIO NORMAL SOLO SU UBICACIÓN
        movimientos_qs = Kardex.objects.filter(
            producto_id=id,
            ubicacion_id=empleado.ubicacion_id
        ).order_by('fecha')

        stock = Inventario.objects.filter(
            producto_id=id,
            ubicacion_id=empleado.ubicacion_id
        ).aggregate(total=Sum('stock'))['total'] or 0

    # =========================================
    # ARMAR RESPUESTA
    # =========================================
    data = []
    ultimo_precio = 0

    for m in movimientos_qs:

        valor = m.cantidad * m.Precio
        saldo_valor = m.saldo * m.Precio
        ultimo_precio = m.Precio

        data.append({
            'fecha': m.fecha,
            'tipo': m.tipo,
            'documento': m.documento,
            'cantidad': m.cantidad,
            'saldo': m.saldo,
            'precio': m.Precio,
            'valor': valor,
            'saldo_valor': saldo_valor
        })

    return render(request, 'empleados/kardex.html', {
        'producto': producto,
        'movimientos': data,
        'stock': stock,
        'ultimo_precio': ultimo_precio
    })


@login_required
def kardex_global_view(request):

    empleado = Empleado.objects.select_related('ubicacion').get(user=request.user)

    movimientos = Kardex.objects.select_related(
        'producto',
        'ubicacion'
    ).all().order_by('-fecha')

    # 🔐 FILTRO POR UBICACIÓN
    if empleado.rol.nombre not in ["Admin", "Gerente"]:
        movimientos = movimientos.filter(ubicacion=empleado.ubicacion)

    # ==============================
    # 🔎 FILTROS
    # ==============================
    tipo = request.GET.get('tipo')
    busqueda = request.GET.get('busqueda')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

    if tipo and tipo != "TODOS":
        movimientos = movimientos.filter(tipo=tipo)

    # 🔥 BUSCAR POR NOMBRE O CÓDIGO
    if busqueda:
        movimientos = movimientos.filter(
            Q(producto__nombre__icontains=busqueda) |
            Q(producto__codigo__icontains=busqueda)
        )

    if desde:
        movimientos = movimientos.filter(fecha__date__gte=desde)

    if hasta:
        movimientos = movimientos.filter(fecha__date__lte=hasta)

    data = []

    for m in movimientos:
        valor = (m.cantidad or 0) * (m.Precio or 0)

        data.append({
            'fecha': m.fecha,
            'tipo': m.tipo,
            'documento': m.documento,
            'producto': m.producto.nombre,
            'codigo': m.producto.codigo,
            'ubicacion': m.ubicacion.nombre,
            'cantidad': m.cantidad,
            'valor': valor,
            'saldo': m.saldo
        })

    return render(request, 'empleados/kardex_global.html', {
        'movimientos': data,

        # 🔥 mantener filtros
        'tipo': tipo or "TODOS",
        'busqueda': busqueda or "",
        'desde': desde or "",
        'hasta': hasta or ""
    })



# 🔹 TRANSFERENCIAS
@login_required
def transferencias_view(request):

    empleado = Empleado.objects.select_related(
        'ubicacion'
    ).get(user=request.user)

    ubicaciones = Ubicacion.objects.all()

    transferencias = Transferencia.objects.select_related(
        'estado',
        'origen',
        'destino'
    ).filter(
        Q(origen=empleado.ubicacion) |
        Q(destino=empleado.ubicacion)
    ).order_by('-id')

    return render(request, 'empleados/transferencias.html', {
        'ubicaciones': ubicaciones,
        'transferencias': transferencias,
        'empleado': empleado
    })

@login_required
def detalle_transferencia(request, id):

    detalles = DetalleTransferencia.objects.select_related('producto').filter(
        Transferencia_id=id
    )

    data = []

    for d in detalles:
        data.append({
            'producto': d.Producto_id,
            'cantidad': d.Cantidad
        })

    return JsonResponse({'detalles': data})


@login_required
def crear_transferencia(request):

    if request.method == "POST":

        empleado = Empleado.objects.select_related(
            'ubicacion'
        ).get(user=request.user)

        origen = Ubicacion.objects.get(
            pk=request.POST['origen_id']
        )

        destino = Ubicacion.objects.get(
            pk=request.POST['destino_id']
        )

        if origen.tipo == "SUCURSAL" and destino.tipo == "SUCURSAL":
            messages.error(request, "No permitido entre sucursales")
            return redirect('transferencias')

        if empleado.ubicacion.nivel == "CENTRAL":
            estado = Estado.objects.get(nombre="Aprobado")
        else:
            estado = Estado.objects.get(nombre="Pendiente")

        transferencia = Transferencia.objects.create(
            origen=origen,
            destino=destino,
            empleado=empleado,
            estado=estado
        )

        # ======================================
        # 🔴 VALIDACIÓN IMPORTANTE AQUÍ
        # ======================================
        detalles_json = request.POST.get('detalles')

        if not detalles_json:
            messages.error(request, "No se enviaron productos en el traslado")
            return redirect('transferencias')

        try:
            detalles = json.loads(detalles_json)
        except json.JSONDecodeError:
            messages.error(request, "Error en formato de productos")
            return redirect('transferencias')

        if len(detalles) == 0:
            messages.error(request, "Debe agregar al menos un producto")
            return redirect('transferencias')

        # ======================================
        # GUARDAR DETALLES
        # ======================================
        for d in detalles:

            producto = Producto.objects.get(pk=d['producto'])

            DetalleTransferencia.objects.create(
                transferencia=transferencia,
                producto=producto,
                cantidad=d['cantidad']
            )

        messages.success(request, "Transferencia creada")
        return redirect('transferencias')


@login_required
def aprobar_transferencia(request, id):

    empleado = Empleado.objects.select_related('ubicacion').get(user=request.user)

    if empleado.ubicacion.nivel != "CENTRAL":
        return JsonResponse({'error': 'No autorizado'})

    t = Transferencia.objects.get(pk=id)

    estado = Estado.objects.get(nombre="Aprobado")

    t.Estado_id = estado.id
    t.save()

    return JsonResponse({'ok': True})
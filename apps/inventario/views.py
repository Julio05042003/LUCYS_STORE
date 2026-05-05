from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse

from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import Inventario, Kardex, Transferencia, DetalleTransferencia
from apps.usuarios.models import Estado, Ubicacion, Empleado

import json


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


def kardex_view(request, id):

    if not es_admin_o_bodega(request.user):
        return redirect('inventario')

    producto = Producto.objects.select_related('categoria', 'marca', 'estado').get(pk=id)

    stock = Inventario.objects.filter(producto=producto).aggregate(
        total=Sum('stock')
    )['total'] or 0

    movimientos = Kardex.objects.filter(producto_id=id).order_by('fecha')

    data = []
    ultimo_precio = 0

    for m in movimientos:
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


# 🔹 TRANSFERENCIAS
@login_required
def transferencias_view(request):

    empleado = Empleado.objects.select_related('ubicacion').get(user=request.user)

    ubicaciones = Ubicacion.objects.all()

    transferencias = Transferencia.objects.select_related('estado').all()

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

        empleado = Empleado.objects.select_related('ubicacion').get(user=request.user)

        origen = Ubicacion.objects.get(pk=request.POST['origen_id'])
        destino = Ubicacion.objects.get(pk=request.POST['destino_id'])

        if origen.tipo == "SUCURSAL" and destino.tipo == "SUCURSAL":
            messages.error(request, "No permitido entre sucursales")
            return redirect('transferencias')

        if empleado.ubicacion.nivel == "CENTRAL":
            estado = Estado.objects.get(nombre="Aprobado")
        else:
            estado = Estado.objects.get(nombre="Pendiente")

        transferencia = Transferencia.objects.create(
            UbicacionOrigen_id=origen.id,
            UbicacionDestino_id=destino.id,
            Empleado_id=empleado.id,
            Estado_id=estado.id
        )

        detalles = json.loads(request.POST['detalles'])

        for d in detalles:
            DetalleTransferencia.objects.create(
                Transferencia_id=transferencia.id,
                Producto_id=d['producto'],
                Cantidad=d['cantidad']
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
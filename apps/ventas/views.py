from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from apps.ventas.models import *
from apps.productos.models import Producto
from apps.usuarios.models import Cliente, Empleado, Estado
from apps.ventas.models import MetodoPago
from apps.caja.models import AperturaCaja, MovimientoCaja
from django.http import JsonResponse
import json
from django.utils import timezone
from apps.inventario.models import Inventario
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def generar_numero_factura(empleado):
    ubicacion = empleado.ubicacion
    prefijo = ubicacion.codigo  # MAN, LEO, etc

    ultima_venta = Venta.objects.filter(
        empleado__ubicacion=ubicacion
    ).order_by('-venta_id').first()

    if ultima_venta and ultima_venta.numero_factura:
        try:
            ultimo_num = int(ultima_venta.numero_factura.split('-')[-1])
        except:
            ultimo_num = 0
    else:
        ultimo_num = 0

    nuevo_num = ultimo_num + 1

    return f"{prefijo}-{str(nuevo_num).zfill(6)}"


@login_required
def vista_ventas(request):

    empleado = request.user.empleado
    rol = empleado.rol.nombre.lower()

    ventas = Venta.objects.select_related(
        'cliente',
        'empleado',
        'metodo',
        'estado',
        'apertura'
    )

    # =========================
    # GERENTE / ADMINISTRADOR
    # =========================
    if rol in ['gerente', 'administrador']:

        ventas = ventas.filter(
            empleado__ubicacion=empleado.ubicacion
        )

    # =========================
    # CAJERO
    # SOLO FACTURAS PENDIENTES
    # =========================
    elif rol == 'cajero':

        ventas = ventas.filter(
            empleado__ubicacion=empleado.ubicacion,
            estado__nombre='Pendiente'
        )

    # =========================
    # VENDEDOR
    # SOLO SUS FACTURAS
    # =========================
    else:

        ventas = ventas.filter(
            empleado=empleado
        )

    ventas = ventas.order_by('-fecha')

    clientes = Cliente.objects.all()
    metodos = MetodoPago.objects.all()

    return render(request, 'empleados/ventas.html', {
        'ventas': ventas,
        'clientes': clientes,
        'metodos': metodos,
        'numero_factura': generar_numero_factura(empleado)
    })

@login_required
def anular_venta(request, venta_id):

    empleado = request.user.empleado
    rol = empleado.rol.nombre.lower()

    venta = get_object_or_404(
        Venta.objects.select_related(
            'estado',
            'metodo',
            'apertura',
            'empleado'
        ),
        venta_id=venta_id
    )

    # =========================
    # SOLO POST
    # =========================
    if request.method != 'POST':

        return redirect('ventas')

    # =========================
    # VALIDAR ROL
    # =========================
    if rol not in ['gerente', 'administrador']:

        messages.error(
            request,
            'No tienes permisos para anular ventas.'
        )

        return redirect('ventas')

    # =========================
    # VALIDAR SUCURSAL
    # =========================
    if venta.empleado.ubicacion != empleado.ubicacion:

        messages.error(
            request,
            'No puedes anular ventas de otra sucursal.'
        )

        return redirect('ventas')

    # =========================
    # YA ANULADA
    # =========================
    if venta.estado.nombre == 'Anulada':

        messages.error(
            request,
            'La factura ya está anulada.'
        )

        return redirect('ventas')

    # =========================
    # SI ESTÁ PAGADA
    # =========================
    if venta.estado.nombre == 'Pagada':

        # =========================
        # SOLO EFECTIVO AFECTA CAJA
        # =========================
        if venta.metodo.nombre.lower() == 'efectivo':

            apertura = venta.apertura

            # validar apertura
            if not apertura:

                messages.error(
                    request,
                    'La venta no tiene apertura de caja.'
                )

                return redirect('ventas')

            # validar caja abierta
            if apertura.estado.nombre != 'Abierta':

                messages.error(
                    request,
                    'No se puede anular porque la caja está cerrada.'
                )

                return redirect('ventas')

            # =========================
            # MOVIMIENTO CAJA
            # =========================
            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='EGRESO',
                monto=venta.total,
                descripcion=f'ANULACIÓN FACTURA #{venta.numero_factura}'
            )

            # =========================
            # ACTUALIZAR SALDO
            # =========================
            apertura.saldo_final -= venta.total
            apertura.save()

    # =========================
    # CAMBIAR ESTADO
    # =========================
    estado_anulada = Estado.objects.get(
        nombre='Anulada'
    )

    venta.estado = estado_anulada
    venta.save()

    # =========================
    # EL TRIGGER MANEJA:
    # - STOCK
    # - KARDEX
    # =========================

    messages.success(
        request,
        f'Factura #{venta.numero_factura} anulada correctamente.'
    )

    return redirect('ventas')


@csrf_exempt
def crear_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            cliente = Cliente.objects.get(pk=data['cliente'])
            metodo = MetodoPago.objects.get(pk=data['metodo'])
            empleado = Empleado.objects.get(pk=data['empleado'])

            apertura = AperturaCaja.objects.filter(
                caja__ubicacion=empleado.ubicacion,
                estado__nombre__iexact='Abierta'
            ).order_by('-fecha_apertura').first()

            if not apertura:
                return JsonResponse({'error': 'Caja no abierta'})

            if not data.get('productos'):
                return JsonResponse({'error': 'No hay productos'})

            if not data.get('cliente'):
                return JsonResponse({'error': 'Seleccione cliente'})

            # =========================
            # PEDIDO (SI EXISTE)
            # =========================
            pedido_id = data.get('pedido')

            if pedido_id:
                try:
                    pedido = Pedido.objects.get(
                        pk=pedido_id,
                        ubicacion=empleado.ubicacion
                    )

                    estado_confirmado = Estado.objects.get(nombre__iexact="Confirmado")
                    pedido.estado = estado_confirmado
                    pedido.save()

                except Pedido.DoesNotExist:
                    return JsonResponse({'error': 'Pedido no válido'})

            # =========================
            # NUMERO FACTURA
            # =========================
            numero_factura = generar_numero_factura(empleado)

            estado = Estado.objects.get(nombre__iexact="Pendiente")

            venta = Venta.objects.create(
                cliente=cliente,
                metodo=metodo,
                empleado=empleado,
                apertura=apertura,
                estado=estado,
                numero_factura=numero_factura,
                total=0
            )

            total = 0

            for item in data['productos']:
                producto = Producto.objects.get(pk=item['producto_id'])

                inventario = Inventario.objects.get(
                    producto=producto,
                    ubicacion=empleado.ubicacion
                )

                if item['cantidad'] <= 0:
                    return JsonResponse({'error': 'Cantidad inválida'})

                if item['cantidad'] > inventario.stock:
                    return JsonResponse({
                        'error': f'Stock insuficiente para {producto.nombre}'
                    })

                subtotal = (item['precio'] * item['cantidad']) - item['descuento']
                total += subtotal

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item['cantidad'],
                    precio=item['precio'],
                    descuento=item['descuento']
                )

                inventario.stock -= item['cantidad']
                inventario.save()

            venta.total = total
            venta.save()

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Método no permitido'})

@login_required
def cobrar_venta(request):

    if request.method == 'POST':

        venta_id = request.POST.get('venta_id')

        venta = get_object_or_404(
            Venta,
            pk=venta_id
        )

        estado_pagada = Estado.objects.get(
            nombre='Pagada'
        )

        venta.estado = estado_pagada
        venta.save()

        messages.success(
            request,
            'Venta cobrada correctamente.'
        )

    return redirect('ventas')


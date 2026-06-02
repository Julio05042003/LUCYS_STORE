from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from apps.ventas.models import *
from apps.productos.models import Producto
from apps.usuarios.models import Cliente, Empleado, Estado
from apps.ventas.models import MetodoPago
from apps.caja.models import AperturaCaja, MovimientoCaja
from django.http import JsonResponse
import json
from django.db.models import CharField
from django.utils import timezone
from apps.inventario.models import Inventario
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.pedidos.models import Pedido, DetallePedido
from django.db.models.functions import Cast


# ======================================================
# BUSCAR PEDIDOS TERMINADOS
# ======================================================

from django.http import JsonResponse
from django.db.models import Q

def buscar_pedidos(request):

    try:

        term = request.GET.get('term', '').strip()

        pedidos = (
            Pedido.objects
            .annotate(
                id_string=Cast('id', CharField())
            )
            .select_related('cliente')
            .prefetch_related('detallepedido_set__producto')
            .filter(
                Q(id_string__icontains=term)
            )[:10]
        )

        data = []

        for p in pedidos:

            productos = []

            for d in p.detallepedido_set.all():

                productos.append({
                    "producto_id": d.producto.producto_id,
                    "producto": d.producto.nombre,
                    "precio": float(d.precio),
                    "cantidad": d.cantidad
                })

            data.append({

                "id": p.id,

                "text": f"Pedido #{p.id} - {p.cliente}",

                "cliente": str(p.cliente),

                "cliente_id": p.cliente.cliente_id,

                "productos": productos
            })

        return JsonResponse(data, safe=False)

    except Exception as e:

        return JsonResponse({
            "error": str(e)
        }, status=500)

def generar_numero_factura(empleado):
    sucursal = empleado.sucursal
    prefijo = sucursal.codigo  # MAN, LEO, etc

    ultima_venta = Venta.objects.filter(
        empleado__sucursal=sucursal
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
            empleado__sucursal=empleado.sucursal
        )

    # CAJERO SOLO FACTURAS PENDIENTES
    elif rol == 'cajero':
        ventas = ventas.filter(
            empleado__sucursal=empleado.sucursal,
            estado__nombre='Pendiente'
        )

    # VENDEDOR SOLO SUS FACTURAS
    else:
        ventas = ventas.filter(
            empleado=empleado
        )

    ventas = ventas.order_by('-fecha')

    clientes = Cliente.objects.all()
    metodos = MetodoPago.objects.all()
    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre='Abierta'
    ).select_related(
        'tipocambio'
    ).first()
    
    tasa = apertura.tipocambio.valor if apertura else 36.62
    
    return render(request, 'empleados/ventas.html', {
        'ventas': ventas,
        'clientes': clientes,
        'metodos': metodos,
        'numero_factura': generar_numero_factura(empleado),
        'tasa': tasa
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

    # SOLO POST
    if request.method != 'POST':

        return redirect('ventas')

    # VALIDAR ROL
    if rol not in ['gerente', 'administrador']:

        messages.error(request,'No tienes permisos para anular ventas.')
        return redirect('ventas')

    # VALIDAR SUCURSAL
    if venta.empleado.sucursal != empleado.sucursal:

        messages.error(request,'No puedes anular ventas de otra sucursal.')
        return redirect('ventas')

    # YA ANULADA
    if venta.estado.nombre == 'Anulada':

        messages.error(request,'La factura ya está anulada.')
        return redirect('ventas')

    # SI ESTÁ PAGADA
    if venta.estado.nombre == 'Pagada':
        # SOLO EFECTIVO AFECTA CAJA
        if venta.metodo.nombre.lower() == 'efectivo':
            apertura = venta.apertura

            # validar apertura
            if not apertura:
                messages.error(request,'La venta no tiene apertura de caja.')
                return redirect('ventas')

            # validar caja abierta
            if apertura.estado.nombre != 'Abierta':
                messages.error(request,'No se puede anular porque la caja está cerrada.')
                return redirect('ventas')

            # MOVIMIENTO CAJA
            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='EGRESO',
                monto=venta.total,
                descripcion=f'ANULACIÓN FACTURA #{venta.numero_factura}'
            )

            # ACTUALIZAR SALDO
            if apertura.saldo_final is None:
                apertura.saldo_final = 0

            apertura.saldo_final -= venta.total
            apertura.save()
            
    # CAMBIAR ESTADO PEDIDO
    if venta.pedido:
        estado_cancelado = Estado.objects.get(nombre='Cancelado')
        venta.pedido.estado = estado_cancelado
        venta.pedido.save()
    

    # CAMBIAR ESTADO FACTURA
    estado_anulada = Estado.objects.get(
        nombre='Anulada'
    )

    venta.estado = estado_anulada
    venta.save()

    messages.success(request,f'Factura #{venta.numero_factura} anulada correctamente.')
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
                caja__sucursal=empleado.sucursal,
                estado__nombre__iexact='Abierta'
            ).order_by('-fecha_apertura').first()

            if not apertura:
                return JsonResponse({'error': 'Caja no abierta'})

            if not data.get('productos'):
                return JsonResponse({'error': 'No hay productos'})

            if not data.get('cliente'):
                return JsonResponse({'error': 'Seleccione cliente'})

            # PEDIDO (SI EXISTE)
            pedido_id = data.get('pedido')

            if pedido_id:
                try:
                    pedido = Pedido.objects.get(
                        pk=pedido_id,
                        sucursal=empleado.sucursal
                    )

                    estado_confirmado = Estado.objects.get(nombre__iexact="Confirmado")
                    pedido.estado = estado_confirmado
                    pedido.save()

                except Pedido.DoesNotExist:
                    return JsonResponse({'error': 'Pedido no válido'})

            # NUMERO FACTURA
            numero_factura = generar_numero_factura(empleado)
            estado = Estado.objects.get(nombre__iexact="Pendiente")

            venta = Venta.objects.create(
                cliente=cliente,
                metodo=metodo,
                empleado=empleado,
                apertura=apertura,
                estado=estado,
                numero_factura=numero_factura,
                pedido_id=pedido_id if pedido_id else None,
                total=0
            )

            total = 0

            for item in data['productos']:
                producto = Producto.objects.get(pk=item['producto_id'])

                inventario = Inventario.objects.filter(
                    producto=producto,
                    bodega=empleado.sucursal.bodega
                ). first()
                
                if not inventario:
                    return JsonResponse({'error': f'No existe inventario para {producto.nombre}'})

                if item['cantidad'] <= 0:
                    return JsonResponse({'error': 'Cantidad inválida'})

                if item['cantidad'] > inventario.stock:
                    return JsonResponse({
                        'error': f'Stock insuficiente para {producto.nombre}'
                    })
                
                descuento_total = (Decimal(str(item.get('descuento', 0)))) * Decimal(str(item['cantidad']))
                subtotal = ( Decimal(str(item['precio'])) *  Decimal(str(item['cantidad']))) - descuento_total
                total += subtotal

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item['cantidad'],
                    precio=item['precio'],
                    descuento=descuento_total
                )
                """ verificar el trigger
                inventario.stock -= item['cantidad']
                inventario.save()"""

            venta.total = total
            venta.save()

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Método no permitido'})

from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def cobrar_venta(request):

    if request.method == 'POST':

        venta_id = request.POST.get('venta_id')

        venta = get_object_or_404(
            Venta,
            pk=venta_id
        )

        empleado = request.user.empleado

        # VALIDAR APERTURA
        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='Abierta'
        ).select_related(
            'tipocambio',
            'caja'
        ).first()

        if not apertura:
            messages.error(request,'No tiene una caja abierta.')
            return redirect('ventas')

        # ESTADO PAGADA
        estado_pagada = Estado.objects.get(nombre='Pagada')

        # TIPO CAMBIO
        tasa = Decimal(str(apertura.tipocambio.valor))

        # EFECTIVO
        efectivo_cordoba = Decimal(request.POST.get('efectivo_cordoba',0))

        efectivo_dolar = Decimal(request.POST.get('efectivo_dolar',0))

        # TRANSFERENCIA
        transferencia_cordoba = Decimal(request.POST.get('transferencia_cordoba',0))

        transferencia_dolar = Decimal(request.POST.get('transferencia_dolar',0))

        # TARJETA
        tarjeta_cordoba = Decimal(request.POST.get('tarjeta_cordoba',0))

        tarjeta_dolar = Decimal(request.POST.get('tarjeta_dolar',0))

        # TOTALES CONVERTIDOS

        total_efectivo = (efectivo_cordoba + (efectivo_dolar * tasa))

        total_transferencia = (
            transferencia_cordoba +
            (transferencia_dolar * tasa)
        )

        total_tarjeta = (
            tarjeta_cordoba +
            (tarjeta_dolar * tasa)
        )

        total_pagado = (
            total_efectivo +
            total_transferencia +
            total_tarjeta
        )

        # =========================================
        # VALIDAR TOTAL
        # =========================================

        if total_pagado < venta.total:

            messages.error(
                request,
                'El monto pagado es menor al total.'
            )

            return redirect('ventas')

        # ACTUALIZAR VENTA

        venta.estado = estado_pagada
        venta.save()

        # MOVIMIENTOS AUTOMATICOS
        # SOLO EFECTIVO ENTRA A CAJA

        tipo_ingreso = 'INGRESO'
        

        # EFECTIVO CORDOBA
        if efectivo_cordoba > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='INGRESO',
                moneda='CORDOBA',
                monto=efectivo_cordoba,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Efectivo C$'
            )

        # EFECTIVO DOLAR
        if efectivo_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=efectivo_dolar,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Efectivo USD'

            )

        # TRANSFERENCIA CORDOBA
        # NO ENTRA A CAJA

        if transferencia_cordoba > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='CORDOBA',
                monto=transferencia_cordoba,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Transferencia C$',

            )

        # TRANSFERENCIA DOLAR
        if transferencia_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=transferencia_dolar,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Transferencia USD',

            )

        # TARJETA CORDOBA
        if tarjeta_cordoba > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='CORDOBA',
                monto=tarjeta_cordoba,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Tarjeta C$',

            )

        # TARJETA DOLAR
        if tarjeta_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=tarjeta_dolar,
                descripcion=
                f'Cobro factura #{venta.venta_id} - Tarjeta USD',

            )

        # MENSAJE
        messages.success(request,'Venta cobrada correctamente.')

    return redirect('ventas')


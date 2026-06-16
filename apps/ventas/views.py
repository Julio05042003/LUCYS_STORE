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
                Q(id_string__icontains=term),
                estado__nombre='Preparado'
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

                "text": f"Pedido #{p.codigo} - {p.cliente}",

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

    # GERENTE / ADMINISTRADOR
    if rol in ['gerente', 'administrador']:

        ventas = ventas.filter(
            empleado__sucursal=empleado.sucursal
        )
        

    # CAJERO SOLO FACTURAS PENDIENTES
    elif rol == 'cajero':
        ventas = ventas.filter(
            empleado__sucursal=empleado.sucursal,
            estado__nombre__in=['Pendiente', 'Pagada']
        )

    # VENDEDOR SOLO SUS FACTURAS
    else:
        ventas = ventas.filter(
            empleado=empleado
        )

    ventas = ventas.order_by('-fecha')
    
    cliente = request.GET.get('cliente')
    vendedor = request.GET.get('vendedor')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

    if cliente:
        ventas = ventas.filter(cliente__nombre__icontains=cliente)

    if vendedor:
        ventas = ventas.filter(empleado__user__first_name__icontains=vendedor)

    if desde:
        ventas = ventas.filter(fecha__date__gte=desde)

    if hasta:
        ventas = ventas.filter(fecha__date__lte=hasta)

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



from django.db.models import Sum
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required


@login_required
def anular_venta(request, venta_id):

    empleado = request.user.empleado
    rol = empleado.rol.nombre.lower()

    venta = get_object_or_404(
        Venta.objects.select_related(
            'estado',
            'apertura',
            'empleado',
            'pedido'
        ),
        venta_id=venta_id
    )

    # SOLO POST
    if request.method != 'POST':
        return redirect('ventas')

    # VALIDACIONES DE PERMISOS
    if rol not in ['gerente', 'administrador']:
        messages.error(request, 'No tienes permisos para anular ventas.')
        return redirect('ventas')

    if venta.empleado.sucursal != empleado.sucursal:
        messages.error(request, 'No puedes anular ventas de otra sucursal.')
        return redirect('ventas')

    if venta.estado.nombre == 'Anulada':
        messages.error(request, 'La factura ya está anulada.')
        return redirect('ventas')

    # SOLO SI ESTÁ PAGADA AFECTA CAJA
    if venta.estado.nombre == 'Pagada':

        apertura = venta.apertura

        if not apertura:
            messages.error(request, 'La venta no tiene apertura de caja.')
            return redirect('ventas')

        if apertura.estado.nombre != 'Abierta':
            messages.error(request, 'La caja está cerrada.')
            return redirect('ventas')

        # SALDO REAL DE CAJA (INGRESOS - EGRESOS)
        ingresos_cordoba = MovimientoCaja.objects.filter(
            apertura=apertura,
            moneda='CORDOBA',
            tipo='INGRESO'
        ).exclude(
            descripcion__icontains='Transferencia'
        ).exclude(
            descripcion__icontains='Tarjeta'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        egresos_cordoba = MovimientoCaja.objects.filter(
            apertura=apertura,
            moneda='CORDOBA',
            tipo='EGRESO'
        ).exclude(
            descripcion__icontains='Transferencia'
        ).exclude(
            descripcion__icontains='Tarjeta'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        saldo_cordoba = ingresos_cordoba - egresos_cordoba

        ingresos_dolar = MovimientoCaja.objects.filter(
            apertura=apertura,
            moneda='DOLAR',
            tipo='INGRESO'
        ).exclude(
            descripcion__icontains='Transferencia'
        ).exclude(
            descripcion__icontains='Tarjeta'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        egresos_dolar = MovimientoCaja.objects.filter(
            apertura=apertura,
            moneda='DOLAR',
            tipo='EGRESO'
        ).exclude(
            descripcion__icontains='Transferencia'
        ).exclude(
            descripcion__icontains='Tarjeta'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        saldo_dolar = ingresos_dolar - egresos_dolar

        # =========================================================
        # INGRESOS DE ESTA FACTURA (SOLO EFECTIVO)
        # =========================================================
        movimientos_factura = MovimientoCaja.objects.filter(
            apertura=apertura,
            tipo='INGRESO',
            descripcion__icontains=f'Cobro factura {venta.numero_factura}'
        ).exclude(
            descripcion__icontains='Transferencia'
        ).exclude(
            descripcion__icontains='Tarjeta'
        )

        total_factura_cordoba = sum(
            m.monto for m in movimientos_factura if m.moneda == 'CORDOBA'
        )

        total_factura_dolar = sum(
            m.monto for m in movimientos_factura if m.moneda == 'DOLAR'
        )

        # VALIDACIÓN DE CAJA
        if total_factura_cordoba > saldo_cordoba:
            messages.error(request, 'No hay suficiente efectivo en córdobas para anular esta factura.')
            return redirect('ventas')

        if total_factura_dolar > saldo_dolar:
            messages.error(request, 'No hay suficiente efectivo en dólares para anular esta factura.')
            return redirect('ventas')

        # REVERSA (EGRESO)
        if total_factura_cordoba > 0:
            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='EGRESO',
                moneda='CORDOBA',
                monto=total_factura_cordoba,
                descripcion=f'ANULACIÓN FACTURA #{venta.numero_factura}'
            )

        if total_factura_dolar > 0:
            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='EGRESO',
                moneda='DOLAR',
                monto=total_factura_dolar,
                descripcion=f'ANULACIÓN FACTURA #{venta.numero_factura}'
            )

    # CANCELAR PEDIDO
    if venta.pedido:
        estado_cancelado = Estado.objects.get(nombre='Cancelado')
        venta.pedido.estado = estado_cancelado
        venta.pedido.save()

    # ANULAR FACTURA
    estado_anulada = Estado.objects.get(nombre='Anulada')
    venta.estado = estado_anulada
    venta.save()

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

                    estado_confirmado = Estado.objects.get(nombre__iexact="Facturado")
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

        # VALIDAR TOTAL
        if total_pagado < venta.total:

            messages.error(
                request,
                'El monto pagado es menor al total.'
            )

            return redirect('ventas')
        
        # CALCULAR VUELTO
        vuelto = total_pagado - venta.total

        if vuelto > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo='EGRESO',
                moneda='CORDOBA',
                monto=Decimal(vuelto),
                descripcion=f'Vuelto factura {venta.numero_factura}'
            )

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
                f'Cobro factura {venta.numero_factura}'
            )

        # EFECTIVO DOLAR
        if efectivo_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=efectivo_dolar,
                descripcion=
                f'Cobro factura {venta.numero_factura}'

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
                f'Cobro factura {venta.numero_factura} - Transferencia C$',

            )

        # TRANSFERENCIA DOLAR
        if transferencia_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=transferencia_dolar,
                descripcion=
                f'Cobro factura {venta.numero_factura} - Transferencia USD',

            )

        # TARJETA CORDOBA
        if tarjeta_cordoba > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='CORDOBA',
                monto=tarjeta_cordoba,
                descripcion=
                f'Cobro factura {venta.numero_factura} - Tarjeta C$',

            )

        # TARJETA DOLAR
        if tarjeta_dolar > 0:

            MovimientoCaja.objects.create(
                apertura=apertura,
                tipo=tipo_ingreso,
                moneda='DOLAR',
                monto=tarjeta_dolar,
                descripcion=
                f'Cobro factura {venta.numero_factura} - Tarjeta USD',

            )

        # MENSAJE
        messages.success(request,'Venta cobrada correctamente.')

    return redirect('ventas')



def detalle_venta(request, venta_id):

    venta = get_object_or_404(
        Venta.objects.select_related(
            'cliente',
            'empleado__user',
            'empleado__sucursal__direccion',
            'metodo'
        ),
        pk=venta_id
    )

    sucursal = venta.empleado.sucursal
    direccion = sucursal.direccion

    items = []
    subtotal = Decimal('0')
    total_descuento = Decimal('0')

    for d in venta.detalleventa_set.select_related('producto').all():

        precio = Decimal(str(d.precio or 0))
        cantidad = Decimal(str(d.cantidad or 0))
        descuento = Decimal(str(d.descuento or 0))

        item_total = precio * cantidad
        item_descuento = descuento

        subtotal += item_total
        total_descuento += item_descuento

        items.append({
            "producto": d.producto.nombre,
            "cantidad": int(cantidad),
            "precio": float(precio),
            "descuento": float(item_descuento),
            "total": float(item_total - item_descuento)
        })

    user = venta.empleado.user
    telefono = venta.cliente.telefonocliente_set.filter(estado__nombre="Activo").first()

    data = {
        "numero": venta.numero_factura or "",
        "fecha": venta.fecha.strftime("%d/%m/%Y %H:%M") if venta.fecha else "",
        "cliente": str(venta.cliente) if venta.cliente else "Sin cliente",
        "telefono_cliente": telefono.numero if telefono else "",
        "vendedor": (
            f"{user.first_name} {user.last_name}".strip()
            if user and (user.first_name or user.last_name)
            else user.username if user else "Sin nombre"
        ),

        "metodo": venta.metodo.nombre if venta.metodo else "",

        # 🔥 EVITA ERRORES DE JS
        "subtotal": float(subtotal or 0),
        "descuento": float(total_descuento or 0),
        "total": float(venta.total or 0),

        "direccion_sucursal": (
            f"{direccion.detalle}, {direccion.ciudad}, "
            f"{direccion.departamento}, {direccion.pais}"
            if direccion else ""
        ),

        "items": items
    }

    return JsonResponse(data, safe=True)


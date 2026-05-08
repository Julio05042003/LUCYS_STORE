from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from apps.ventas.models import *
from apps.productos.models import Producto
from apps.usuarios.models import Cliente, Empleado, Estado
from apps.ventas.models import MetodoPago
from apps.caja.models import AperturaCaja
from django.http import JsonResponse
import json
from django.utils import timezone
from apps.inventario.models import Inventario

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


def vista_ventas(request):
    empleado = request.user.empleado

    # 🔒 FILTRO POR ROL
    if empleado.rol.nombre.lower() in ["gerente", "administrador"]:
        ventas = Venta.objects.select_related(
            'cliente', 'empleado', 'metodo'
        ).filter(
            empleado__ubicacion=empleado.ubicacion
        )
    elif empleado.rol.nombre.lower() == "cajero":
        ventas = Venta.objects.filter(
            apertura__caja__ubicacion=empleado.ubicacion,
            estado__nombre="Pendiente"
)
    else:
        # 👨‍💼 vendedor solo ve sus ventas
        ventas = Venta.objects.select_related(
            'cliente', 'empleado', 'metodo'
        ).filter(
            empleado=empleado
        )

    clientes = Cliente.objects.all()
    metodos = MetodoPago.objects.all()

    return render(request, 'empleados/ventas.html', {
        'ventas': ventas,
        'clientes': clientes,
        'metodos': metodos,
        'numero_factura': generar_numero_factura(request.user.empleado)
    })


@csrf_exempt
def crear_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            cliente = Cliente.objects.get(pk=data['cliente'])
            metodo = MetodoPago.objects.get(pk=data['metodo'])
            empleado = Empleado.objects.get(pk=data['empleado'])

            apertura = AperturaCaja.objects.filter(
                empleado=empleado,
                estado__nombre__iexact='ABIERTA'
            ).last()

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
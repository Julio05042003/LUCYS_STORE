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


def vista_ventas(request):
    ventas = Venta.objects.select_related('cliente', 'empleado', 'metodo').all()
    clientes = Cliente.objects.all()
    metodos = MetodoPago.objects.all()

    return render(request, 'empleados/ventas.html', {
        'ventas': ventas,
        'clientes': clientes,
        'metodos': metodos,
        'numero_factura': Venta.objects.count() + 1
    })


@csrf_exempt
def crear_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            cliente = Cliente.objects.get(pk=data['cliente'])
            metodo = MetodoPago.objects.get(pk=data['metodo'])
            empleado = Empleado.objects.get(pk=data['empleado'])
            apertura = AperturaCaja.objects.get(pk=data['apertura'])
            estado = Estado.objects.get(nombre__iexact="activo")

            # Crear venta
            venta = Venta.objects.create(
                cliente=cliente,
                metodo=metodo,
                empleado=empleado,
                apertura=apertura,
                estado=estado,
                numero_factura=Venta.objects.count() + 1,
                total=0,
                fecha=timezone.now()
            )

            total = 0

            # Crear detalles
            for item in data['productos']:
                producto = Producto.objects.get(pk=item['producto_id'])

                subtotal = (item['precio'] * item['cantidad']) - item['descuento']
                total += subtotal

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item['cantidad'],
                    precio=item['precio'],
                    descuento=item['descuento']
                )

            venta.total = total
            venta.save()

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Método no permitido'})
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Compra, DetalleCompra, Proveedor, Ubicacion
from apps.inventario.models import Producto
from apps.usuarios.models import Empleado


# 📌 LISTAR COMPRAS
def compras_view(request):
    compras = Compra.objects.select_related('proveedor', 'ubicacion', 'empleado').all().order_by('-id')
    proveedores = Proveedor.objects.all()
    ubicaciones = Ubicacion.objects.all()
    empleados = Empleado.objects.all()
    productos = Producto.objects.all()

    return render(request, 'empleados/compras.html', {
        'compras': compras,
        'proveedores': proveedores,
        'ubicaciones': ubicaciones,
        'empleados': empleados,
        'productos': productos
    })


# 📌 CREAR COMPRA (SOLO TOTAL)
@csrf_exempt
def crear_compra(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            proveedor = Proveedor.objects.get(id=data['proveedor'])
            ubicacion = Ubicacion.objects.get(id=data['ubicacion'])
            empleado = Empleado.objects.get(id=data['empleado'])

            compra = Compra.objects.create(
                proveedor=proveedor,
                ubicacion=ubicacion,
                empleado=empleado
            )

            total = 0

            for item in data['productos']:
                producto = Producto.objects.get(id=item['producto_id'])
                cantidad = int(item['cantidad'])
                precio = float(item['precio'])

                total += cantidad * precio

                DetalleCompra.objects.create(
                    compra=compra,
                    producto=producto,
                    cantidad=cantidad,
                    precio=precio
                )

            compra.total = total
            compra.save()

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)})
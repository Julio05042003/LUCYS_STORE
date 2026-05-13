from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import date

from .models import *
from apps.inventario.models import Producto
from apps.usuarios.models import Empleado, Direccion, Estado


# 📌 LISTAR COMPRAS
def compras_view(request):

    compras = Compra.objects.select_related(
        'proveedor',
        'ubicacion',
        'empleado'
    ).all().order_by('-id')

    proveedores = Proveedor.objects.all()

    ubicaciones = Ubicacion.objects.all()

    estados = Estado.objects.all()

    return render(request, 'empleados/compras.html', {

        'compras': compras,
        'proveedores': proveedores,
        'ubicaciones': ubicaciones,
        'estados': estados,
        'today': date.today(),

    })


# 📌 CREAR COMPRA (SOLO TOTAL)
# 📌 CREAR COMPRA (SOLO UNA COMPRA POR PRODUCTO)
@csrf_exempt
def crear_compra(request):

    if request.method == 'POST':

        try:

            data = json.loads(request.body)

            empleado = Empleado.objects.get(
                empleado_id=data['empleado']
            )

            proveedor = Proveedor.objects.get(
                id=data['proveedor']
            )

            ubicacion = Ubicacion.objects.get(
                ubicacion_id=data['ubicacion']
            )

            # ====================================
            # VALIDAR PRODUCTOS YA COMPRADOS
            # ====================================

            for item in data['productos']:

                producto = Producto.objects.get(
                    producto_id=item['producto_id']
                )

                existe = DetalleCompra.objects.filter(
                    producto=producto
                ).exists()

                if existe:

                    return JsonResponse({

                        'status': 'error',
                        'error': f'El producto "{producto.nombre}" ya fue comprado anteriormente'

                    })

            # ====================================
            # CREAR COMPRA
            # ====================================

            compra = Compra.objects.create(

                proveedor=proveedor,
                ubicacion=ubicacion,
                empleado=empleado,
                total=0

            )

            total = 0

            for item in data['productos']:

                producto = Producto.objects.get(
                    producto_id=item['producto_id']
                )

                cantidad = int(item['cantidad'])

                precio = float(item['precio'])

                subtotal = cantidad * precio

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

    return JsonResponse({
        'status': 'error'
    })


# 📌 CREAR PROVEEDOR
def crear_proveedor(request):

    if request.method == 'POST':

        try:

            nombre = request.POST.get('nombre', '').strip()

            # =========================
            # VALIDAR NOMBRE ÚNICO
            # =========================
            existe = Proveedor.objects.filter(
                nombre__iexact=nombre
            ).exists()

            if existe:

                return HttpResponse(
                    'Error: Ya existe un proveedor con ese nombre'
                )

            # =========================
            # CREAR DIRECCIÓN
            # =========================
            direccion = Direccion.objects.create(

                pais=request.POST.get('pais'),
                departamento=request.POST.get('departamento'),
                ciudad=request.POST.get('ciudad'),
                detalle=request.POST.get('detalle')

            )

            # =========================
            # CREAR PROVEEDOR
            # =========================
            proveedor = Proveedor.objects.create(

                direccion=direccion,
                nombre=nombre,
                contacto=request.POST.get('contacto'),
                correo=request.POST.get('correo')

            )

            # =========================
            # DATOS TELÉFONO
            # =========================
            numero = request.POST.get('numero')
            operadora = request.POST.get('operadora')
            tipo = request.POST.get('tipo')

            # =========================
            # CREAR TELÉFONO
            # =========================
            if numero and numero.strip() != '':

                estado = Estado.objects.get(
                    nombre__iexact='Activo'
                )

                TelefonoProveedor.objects.create(

                    proveedor=proveedor,
                    estado=estado,
                    numero=numero,
                    operadora=operadora,
                    tipo=tipo

                )

            return redirect('compras')

        except Exception as e:

            return HttpResponse(
                f'Error: {str(e)}'
            )

    return HttpResponse(
        'Método no permitido'
    )
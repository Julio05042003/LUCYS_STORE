import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.pedidos.models import *
from apps.productos.models import Producto
from apps.usuarios.models import Cliente, Estado


def buscar_pedidos(request):
    term = request.GET.get('term', '')
    empleado = request.user.empleado

    pedidos = Pedido.objects.filter(
        estado__nombre__iexact="En bodega",
        ubicacion=empleado.ubicacion
    )

    if term:
        pedidos = pedidos.filter(id__icontains=term)

    data = []

    for p in pedidos:
        data.append({
            'id': p.id,
            'text': f"Pedido #{p.id} - {p.cliente}"
        })

    return JsonResponse(data, safe=False)



@csrf_exempt
def crear_pedido(request):
    
    if request.method == "POST":
        data = json.loads(request.body)

        carrito = data.get("carrito", [])
        nombre = data.get("nombre")

        total = 0

        estado = Estado.objects.get(nombre__iexact="Pendiente")

        # Crear pedido
        pedido = Pedido.objects.create(
            estado=estado,
            cliente=Cliente.objects.first(),
            ubicacion=request.user.empleado.ubicacion,
            tipo_entrega=TipoEntrega.objects.first(),
            metodo_envio=MetodoEnvio.objects.first(),
            total=0
        )

        # Guardar detalles
        for item in carrito:
            producto = Producto.objects.get(producto_id=item["id"])

            precio = float(producto.precio_venta)
            cantidad = int(item["cantidad"])

            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad,
                precio=precio
            )

            total += precio * cantidad

        return JsonResponse({
            "success": True,
            "total": round(total, 2)
        })

    return JsonResponse({"success": False})


def detalle_pedido(request, id):
    empleado = request.user.empleado
    pedido = Pedido.objects.get(pk=id, ubicacion=empleado.ubicacion)
    
    detalles = DetallePedido.objects.filter(pedido=pedido)

    productos = []

    for d in detalles:
        productos.append({
            "producto_id": d.producto.producto_id,
            "nombre": d.producto.nombre,
            "precio": float(d.precio),
            "cantidad": d.cantidad
        })

    return JsonResponse({
        "cliente": pedido.cliente.cliente_id,
        "productos": productos
    })
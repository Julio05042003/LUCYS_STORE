import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.pedidos.models import Pedido, DetallePedido
from apps.productos.models import Producto
from apps.usuarios.models import Cliente

@csrf_exempt
def crear_pedido(request):
    if request.method == "POST":
        data = json.loads(request.body)

        carrito = data.get("carrito", [])
        nombre = data.get("nombre")

        total = 0

        # Crear pedido
        pedido = Pedido.objects.create(
            estado="PENDIENTE"
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
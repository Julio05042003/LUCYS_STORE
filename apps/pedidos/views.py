from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q

import json

from .models import *
from apps.productos.models import Producto
from apps.inventario.models import Inventario, Bodega
from apps.usuarios.models import Cliente, ClienteDireccion


# ======================================================
# VISTA PRINCIPAL PEDIDOS
# ======================================================

@login_required
def pedidos(request):

    pedidos = Pedido.objects.select_related(
        'cliente',
        'sucursal',
        'estado',
        'tipo_entrega',
        'metodo_envio',
        'direccion_envio',
        'vendedor'
    )

    modo = 'cliente'

    cliente_actual = None

    sucursales = Sucursal.objects.all()

    # ==================================================
    # EMPLEADOS
    # ==================================================

    if hasattr(request.user, 'empleado'):

        modo = 'empleado'

        empleado = request.user.empleado

        # ==============================================
        # FILTRAR POR SUCURSAL
        # ==============================================

        pedidos = pedidos.filter(
            sucursal=empleado.sucursal
        )

    # ==================================================
    # CLIENTES
    # ==================================================

    elif hasattr(request.user, 'cliente'):

        cliente_actual = request.user.cliente

        pedidos = pedidos.filter(
            cliente=cliente_actual
        )

    pedidos = pedidos.order_by('-fecha')

    context = {

        'pedidos': pedidos,
        'modo': modo,
        'cliente_actual': cliente_actual,
        'sucursales': sucursales,
        'tipos_entrega': TipoEntrega.objects.all(),
        'metodos_envio': MetodoEnvio.objects.all(),
    }

    return render(
        request,
        'empleados/pedidos.html',
        context
    )


# ======================================================
# BUSCAR CLIENTES
# ======================================================

@login_required
def buscar_clientes(request):

    term = request.GET.get('term', '')

    clientes = Cliente.objects.filter(
        Q(nombre__icontains=term)
    )[:10]

    data = []

    for c in clientes:

        data.append({

            'id': c.cliente_id,

            'text': f'{c.nombre} {c.apellido}'

        })

    return JsonResponse(data, safe=False)


# ======================================================
# BUSCAR PRODUCTOS PEDIDOS
# ======================================================

@login_required
def buscar_productos_pedidos(request):

    try:

        term = request.GET.get('term', '')

        sucursal_id = request.GET.get('sucursal')

        if not sucursal_id:

            return JsonResponse([], safe=False)

        sucursal = Sucursal.objects.get(
            pk=sucursal_id
        )

        bodega = Bodega.objects.filter(
            sucursal=sucursal
        ).first()

        if not bodega:

            return JsonResponse([], safe=False)

        inventarios = Inventario.objects.select_related(
            'producto'
        ).filter(

            producto__nombre__icontains=term,
            bodega=bodega,
            stock__gt=0

        )[:10]

        data = []

        for inv in inventarios:

            producto = inv.producto

            data.append({

                'id': producto.id,

                'nombre': producto.nombre,

                'precio': float(producto.precio_venta),

                'stock': inv.stock,

                'text': f'''
                    {producto.nombre}
                    | Stock: {inv.stock}
                    | C$ {producto.precio_venta}
                '''
            })

        return JsonResponse(data, safe=False)

    except Exception as e:

        return JsonResponse({

            'success': False,
            'message': str(e)

        })


# ======================================================
# CREAR PEDIDO
# ======================================================

@require_POST
@login_required
def crear_pedido(request):

    try:

        data = json.loads(request.body)

        with transaction.atomic():

            # ==========================================
            # VALIDAR PRODUCTOS
            # ==========================================

            if not data.get('productos'):

                raise Exception(
                    'Debe agregar al menos un producto'
                )

            # ==========================================
            # CLIENTE / EMPLEADO
            # ==========================================

            empleado = None

            if hasattr(request.user, 'empleado'):

                empleado = request.user.empleado

                cliente = Cliente.objects.get(
                    pk=data['cliente']
                )

                # SUCURSAL EMPLEADO
                sucursal = empleado.sucursal

            else:

                cliente = request.user.cliente

                sucursal = Sucursal.objects.get(
                    pk=data['sucursal']
                )

            # ==========================================
            # ENTREGA
            # ==========================================

            tipo_entrega = TipoEntrega.objects.get(
                pk=data['tipo_entrega']
            )

            metodo_envio = None
            direccion_envio = None

            # ==========================================
            # VALIDAR DELIVERY
            # ==========================================

            if tipo_entrega.nombre.lower() == 'delivery':

                # ==============================
                # MÉTODO ENVÍO
                # ==============================

                if not data.get('metodo_envio'):

                    raise Exception(
                        'Debe seleccionar método de envío'
                    )

                metodo_envio = MetodoEnvio.objects.get(
                    pk=data['metodo_envio']
                )

                # ==============================
                # DIRECCIÓN
                # ==============================

                if not data.get('direccion_envio'):

                    raise Exception(
                        'Debe seleccionar dirección de envío'
                    )

                direccion_envio = ClienteDireccion.objects.get(
                    pk=data['direccion_envio']
                )

                # ==============================
                # VALIDAR DIRECCIÓN CLIENTE
                # ==============================

                if direccion_envio.cliente != cliente:

                    raise Exception(
                        'La dirección no pertenece al cliente'
                    )

                # ==============================
                # VALIDAR MÉTODO PAGO
                # ==============================

                metodo_pago = data.get('metodo_pago_nombre', '').lower()

                if metodo_pago != 'transferencia':

                    raise Exception(
                        'Delivery solo permite pago por transferencia'
                    )

            # ==========================================
            # ESTADO PENDIENTE
            # ==========================================

            estado = Estado.objects.get(
                nombre__iexact='Pendiente'
            )

            pedido = Pedido.objects.create(

                cliente=cliente,
                sucursal=sucursal,
                vendedor=empleado,
                tipo_entrega=tipo_entrega,
                metodo_envio=metodo_envio,
                direccion_envio=direccion_envio,
                estado=estado,
                total=0
            )

            total = 0

            # ==========================================
            # BODEGA
            # ==========================================

            bodega = Bodega.objects.filter(
                sucursal=sucursal
            ).first()

            if not bodega:

                raise Exception(
                    'La sucursal no tiene bodega asignada'
                )

            # ==========================================
            # TIPO VENTA
            # ==========================================

            tipo_venta = data.get(
                'tipo_venta',
                ''
            ).lower()

            # ==========================================
            # PRODUCTOS
            # ==========================================

            for item in data['productos']:

                producto = Producto.objects.get(
                    pk=item['producto']
                )

                cantidad = int(item['cantidad'])

                # ======================================
                # VALIDAR CANTIDAD
                # ======================================

                if cantidad <= 0:

                    raise Exception(
                        f'Cantidad inválida en {producto.nombre}'
                    )

                # ======================================
                # MAYORISTA
                # ======================================

                if tipo_venta == 'mayorista':

                    if cantidad % 3 != 0:

                        raise Exception(

                            f'''
                            {producto.nombre}
                            solo permite cantidades
                            múltiplos de 3
                            '''
                        )

                # ======================================
                # INVENTARIO
                # ======================================

                inventario = Inventario.objects.filter(

                    producto=producto,
                    bodega=bodega

                ).first()

                if not inventario:

                    raise Exception(

                        f'''
                        El producto
                        {producto.nombre}
                        no existe en inventario
                        '''
                    )

                # ======================================
                # STOCK
                # ======================================

                if inventario.stock < cantidad:

                    raise Exception(

                        f'''
                        Stock insuficiente:
                        {producto.nombre}
                        '''
                    )

                # ======================================
                # NO DESCONTAR STOCK
                # ======================================

                precio = producto.precio_venta

                subtotal = precio * cantidad

                total += subtotal

                DetallePedido.objects.create(

                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    precio=precio
                )

            pedido.total = total
            pedido.save()

        return JsonResponse({

            'success': True,
            'message': 'Pedido creado correctamente'

        })

    except Exception as e:

        return JsonResponse({

            'success': False,
            'message': str(e)
        })


# ======================================================
# CAMBIAR ESTADO PEDIDO
# ======================================================

@require_POST
@login_required
def cambiar_estado_pedido(request, pedido_id):

    try:

        if not hasattr(request.user, 'empleado'):

            return JsonResponse({

                'success': False,
                'message': 'No tiene permisos'

            })

        empleado = request.user.empleado

        rol = empleado.rol.nombre.lower()

        data = json.loads(request.body)

        pedido = Pedido.objects.get(
            pk=pedido_id
        )

        nuevo_estado = Estado.objects.get(
            nombre=data['estado']
        )

        estado_actual = pedido.estado.nombre.lower()

        nuevo_estado_nombre = nuevo_estado.nombre.lower()

        # ==========================================
        # YA CONFIRMADO
        # ==========================================

        if estado_actual == 'confirmado':

            return JsonResponse({

                'success': False,

                'message':
                'El pedido ya fue confirmado'
            })

        # ==========================================
        # GERENTE SOLO LECTURA
        # ==========================================

        if rol == 'gerente':

            return JsonResponse({

                'success': False,
                'message': 'El gerente no puede modificar estados'

            })

        # ==========================================
        # VENDEDOR
        # ==========================================

        if rol == 'vendedor':

            # PENDIENTE -> EN BODEGA
            if (

                estado_actual == 'pendiente'
                and
                nuevo_estado_nombre == 'en bodega'

            ):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({

                    'success': True,
                    'message': 'Pedido enviado a bodega'

                })

            # PENDIENTE -> CANCELADO
            if (

                estado_actual == 'pendiente'
                and
                nuevo_estado_nombre == 'cancelado'

            ):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({

                    'success': True,
                    'message': 'Pedido cancelado'

                })

            return JsonResponse({

                'success': False,

                'message':
                'El vendedor no puede realizar esta acción'
            })

        # ==========================================
        # BODEGA
        # ==========================================

        if rol == 'bodega':

            # EN BODEGA -> TERMINADO
            if (

                estado_actual == 'en bodega'
                and
                nuevo_estado_nombre == 'terminado'

            ):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({

                    'success': True,
                    'message': 'Pedido terminado correctamente'

                })

            # EN BODEGA -> CANCELADO
            if (

                estado_actual == 'en bodega'
                and
                nuevo_estado_nombre == 'cancelado'

            ):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({

                    'success': True,
                    'message': 'Pedido cancelado correctamente'

                })

            return JsonResponse({

                'success': False,

                'message':
                'Bodega no puede realizar esta acción'
            })

        return JsonResponse({

            'success': False,

            'message':
            'No tiene permisos válidos'
        })

    except Pedido.DoesNotExist:

        return JsonResponse({

            'success': False,
            'message': 'Pedido no encontrado'

        })

    except Estado.DoesNotExist:

        return JsonResponse({

            'success': False,
            'message': 'Estado inválido'

        })

    except Exception as e:

        return JsonResponse({

            'success': False,
            'message': str(e)
        })
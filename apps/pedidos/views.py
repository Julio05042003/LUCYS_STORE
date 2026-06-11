from django.utils import timezone

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
import re
import json
from .models import *
from apps.productos.models import Producto
from apps.inventario.models import Inventario, Bodega
from apps.usuarios.models import Cliente, ClienteDireccion

def generar_codigo_pedido(pedido):
    """
    Genera un código limpio usando el código de la sucursal 
    y el ID del pedido rellenado a 6 dígitos.
    Ejemplo de resultado: SUC01-PED-000042
    """
    # :06d transforma el ID 42 en "000042"
    return f'{pedido.sucursal.codigo}-PED-{pedido.id:06d}'



# BUSCAR CLIENTES
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


# BUSCAR PRODUCTOS PEDIDOS
@login_required
def buscar_productos_pedidos(request):
    try:
        # Sanitizamos los parámetros recibidos por el script (Select2)
        term = request.GET.get('term', '').strip()
        sucursal_id = request.GET.get('sucursal')

        # 1. VALIDACIÓN E IDENTIFICACIÓN DE LA SUCURSAL
        if not sucursal_id or sucursal_id == "":
            # Respaldo: si el frontend no envió la sucursal, la tomamos del empleado logueado
            if hasattr(request.user, 'empleado') and request.user.empleado:
                sucursal = request.user.empleado.sucursal
            else:
                return JsonResponse([], safe=False)
        else:
            try:
                sucursal = Sucursal.objects.get(pk=sucursal_id)
            except Sucursal.DoesNotExist:
                return JsonResponse([], safe=False)

        # 2. LOCALIZACIÓN DE LA BODEGA
        bodega = Bodega.objects.filter(sucursal=sucursal).first()
        if not bodega:
            return JsonResponse([], safe=False)

        # 3. CONSULTA AL INVENTARIO
        # Filtramos por el nombre del producto (parcial/insensible a mayúsculas), la bodega y stock disponible
        inventarios = Inventario.objects.select_related('producto').filter(
            producto__nombre__icontains=term,
            bodega=bodega,
            stock__gt=0
        )[:10]

        data = []
        for inv in inventarios:
            producto = inv.producto
            
            # Al ser '@property', accedemos directamente a ella. 
            # La convertimos a float de forma segura ya que tu propiedad devuelve un Decimal
            precio_final = float(producto.precio_venta)

            data.append({
                'id': producto.producto_id, # CORREGIDO: Usamos el nombre real de tu Primary Key
                'nombre': producto.nombre,
                'precio': precio_final,
                'stock': inv.stock,
                'text': f"{producto.nombre} | Stock: {inv.stock} | C$ {precio_final:.2f}"
            })

        return JsonResponse(data, safe=False)

    except Exception as e:
        # Mandamos un error 500 para que si algo más ocurre, JS te lo muestre en consola de inmediato
        return JsonResponse({
            'success': False,
            'message': f"Error interno en el servidor: {str(e)}"
        }, status=500)
        

@login_required
def obtener_direcciones_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse([], safe=False)
    
    # Buscamos todas las direcciones activas asociadas al cliente
    direcciones_qs = ClienteDireccion.objects.filter(
        cliente_id=cliente_id
    ).select_related('direccion')
    
    data = []
    for cd in direcciones_qs:
        d = cd.direccion
        data.append({
            'id': d.direccion_id,
            # Concatenamos los campos para armar la dirección legible
            'text': f"{cd.tipo}: {d.detalle}, {d.ciudad} - {d.departamento}"
        })
        
    return JsonResponse(data, safe=False)

# VISTA PRINCIPAL PEDIDOS
@login_required
def pedidos(request):

    pedidos = Pedido.objects.select_related(
        'cliente',
        'sucursal',
        'estado',
        'tipo_entrega',
        'metodo_envio',
        'direccion_envio',
        'vendedor__user'
    )

    modo = 'cliente'
    cliente_actual = None
    sucursales = Sucursal.objects.all()

    # EMPLEADOS
    if hasattr(request.user, 'empleado'):

        modo = 'empleado'
        empleado = request.user.empleado
        rol = empleado.rol.nombre.lower()

        # 👑 ADMINISTRADOR
        if rol == 'administrador':
            # El administrador ve absolutamente todos los pedidos de todas las sucursales
            pass

        # 👔 GERENTE
        elif rol == 'gerente':
            # El gerente solo puede ver todos los pedidos que pertenecen a su propia sucursal
            pedidos = pedidos.filter(sucursal=empleado.sucursal)

        # 💼 VENDEDOR
        elif rol == 'vendedor':
            # Todos los vendedores pueden ver los pedidos si están 'Pendiente'.
            # Al tomarse (Borrador, etc.), solo el vendedor asignado puede seguir viéndolo.
            pedidos = pedidos.filter(
                Q(estado__nombre__iexact='Pendiente') | Q(vendedor=empleado)
            )

        # 📦 BODEGA
        elif rol == 'bodega':
            # Bodega solo puede ver los pedidos cuyo estado sea estrictamente 'En Bodega'
            pedidos = pedidos.filter(estado__nombre__iexact='En Bodega')

    # CLIENTES
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
# CREAR PEDIDO
# ======================================================

@require_POST
@login_required
def crear_pedido(request):
    try:
        data = json.loads(request.body)

        with transaction.atomic():

            # ==========================================
            # 1. VALIDAR PRODUCTOS
            # ==========================================
            if not data.get('productos'):
                raise Exception('Debe agregar al menos un producto al carrito.')

            # ==========================================
            # 2. DEFINIR CLIENTE, EMPLEADO Y SUCURSAL
            # ==========================================
            empleado = None
            
            # Caso A: El usuario logueado es un Empleado o Administrador/Staff
            if hasattr(request.user, 'empleado') or request.user.is_staff:
                if hasattr(request.user, 'empleado'):
                    empleado = request.user.empleado
                    sucursal = empleado.sucursal
                else:
                    # Fallback para administradores puros sin perfil de empleado asignado
                    empleado = None
                    if not data.get('sucursal'):
                        raise Exception('Debe especificar una sucursal para este pedido.')
                    sucursal = Sucursal.objects.get(pk=data['sucursal'])

                # Obligatorio obtener el cliente seleccionado desde el formulario Select2
                if not data.get('cliente'):
                    raise Exception('Debe seleccionar un cliente para registrar el pedido.')
                cliente = Cliente.objects.get(pk=data['cliente'])

            # Caso B: Es un cliente real interactuando en la web pública
            else:
                empleado = None
                if not hasattr(request.user, 'cliente'):
                    raise Exception('Tu usuario no cuenta con un perfil de cliente asignado.')
                cliente = request.user.cliente
                
                if not data.get('sucursal'):
                    raise Exception('Debe seleccionar una sucursal de retiro.')
                sucursal = Sucursal.objects.get(pk=data['sucursal'])

            # ==========================================
            # 3. GESTIÓN Y VALIDACIÓN DE ENTREGA
            # ==========================================
            if not data.get('tipo_entrega'):
                raise Exception('Debe seleccionar un tipo de entrega.')
                
            tipo_entrega = TipoEntrega.objects.get(pk=data['tipo_entrega'])

            metodo_envio = None
            direccion_envio = None

            # Validar campos específicos si el tipo de entrega es Delivery
            if tipo_entrega.nombre.lower() == 'delivery':

                # Método de Envío
                if not data.get('metodo_envio'):
                    raise Exception('Debe seleccionar un método de envío para la entrega a domicilio.')
                metodo_envio = MetodoEnvio.objects.get(pk=data['metodo_envio'])

                # Dirección de Envío
                if not data.get('direccion_envio'):
                    raise Exception('Debe seleccionar una dirección de envío.')

                # --- VALIDACIÓN DE TU TABLA INTERMEDIA (Clientes_Direcciones) ---
                # Buscamos el registro intermedio que verifique la propiedad legítima de esa dirección
                try:
                    # Intentamos buscar asumiendo que mandaste la PK de ClienteDireccion
                    relacion_direccion = ClienteDireccion.objects.get(pk=data['direccion_envio'])
                except ClienteDireccion.DoesNotExist:
                    # Si no lo encuentra, asumimos que el selector mandó la PK de la tabla 'Direcciones' pura,
                    # por lo que filtramos cruzando el cliente activo con esa ID de dirección física
                    relacion_direccion = ClienteDireccion.objects.filter(
                        cliente=cliente,
                        direccion_id=data['direccion_envio']
                    ).first()

                # Si no encontramos ningún puente en Clientes_Direcciones para este usuario, bloqueamos
                if not relacion_direccion:
                    raise Exception('La dirección seleccionada no está asociada a este cliente en la base de datos.')

                # Asignamos al pedido el objeto final requerido. 
                # (Nota: Si tu modelo 'Pedido.direccion_envio' es un FK directo a 'ClienteDireccion' 
                # en vez de a 'Direccion', cambia la línea de abajo por: direccion_envio = relacion_direccion)
                direccion_envio = relacion_direccion

            # ==========================================
            # 4. CONFIGURAR ESTADO INICIAL DEL PEDIDO
            # ==========================================
            if empleado is None:
                estado = Estado.objects.get(nombre__iexact='Pendiente')  # Pedido desde la web
            else:
                estado = Estado.objects.get(nombre__iexact='Borrador')   # Creado por un vendedor

            # ==========================================
            # 5. INSTANCIAR EL PEDIDO MAESTRO
            # ==========================================
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

            pedido.codigo = generar_codigo_pedido(pedido)
            pedido.save(update_fields=['codigo'])

            # ==========================================
            # 6. ASIGNACIÓN DE BODEGA Y LOGÍSTICA
            # ==========================================
            bodega = Bodega.objects.filter(sucursal=sucursal).first()
            if not bodega:
                raise Exception('La sucursal de destino no tiene una bodega activa configurada.')

            tipo_venta = data.get('tipo_venta', '').lower()
            total = 0

            # ==========================================
            # 7. PROCESAR EL DETALLE DE PRODUCTOS
            # ==========================================
            for item in data['productos']:
                producto = Producto.objects.get(pk=item['producto'])
                amount = int(item['cantidad'])

                if amount <= 0:
                    raise Exception(f'Cantidad inválida para el producto: {producto.nombre}')

                if tipo_venta == 'mayorista' and amount % 3 != 0:
                    raise Exception(f'El producto {producto.nombre} solo permite compras en múltiplos de 3.')

                # Verificación física contra las existencias en inventario
                inventario = Inventario.objects.filter(producto=producto, bodega=bodega).first()
                if not inventario:
                    raise Exception(f'El producto {producto.nombre} no se encuentra en el inventario de esta bodega.')

                if inventario.stock < amount:
                    raise Exception(f'Stock insuficiente para {producto.nombre}. Disponibles: {inventario.stock} unidades.')

                precio = producto.precio_venta
                subtotal = precio * amount
                total += subtotal

                # Registrar fila de detalle
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=amount,
                    precio=precio
                )

            # Actualización final del valor total del pedido
            pedido.total = total
            pedido.save()
            
            telefonos_disponibles = pedido.sucursal.telefonos.filter(tipo__iexact='vendedor', estado__nombre='Activo').values('numero', 'operadora')


        return JsonResponse({
            'success': True,
            'message': 'Pedido creado y guardado correctamente.',
            'codigo_pedido': pedido.codigo,
            'telefono_sucursal': list(telefonos_disponibles)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })   


# ======================================================
# ACTUALIZAR PEDIDO
# ======================================================

@login_required
def editar_y_actualizar_pedido(request, pedido_id):
    try:
        # ==========================================================
        # 1. ACCIÓN GET: EXTRAER DATOS EXACTOS CON TUS MODELOS
        # ==========================================================
        if request.method == 'GET':
            pedido = Pedido.objects.select_related(
                'cliente', 'vendedor', 'sucursal', 'estado', 'tipo_entrega', 'metodo_envio', 'direccion_envio'
            ).get(pk=pedido_id)
            
            # VALIDACIONES DE SEGURIDAD
            if hasattr(request.user, 'empleado'):

                empleado = request.user.empleado
                rol = empleado.rol.nombre.lower()

                if rol == 'vendedor':

                    if pedido.vendedor != empleado:

                            return JsonResponse({
                            'success': False,
                            'message': 'No posee permisos para visualizar este pedido.'
                        })

            if pedido.estado.nombre.lower() != 'borrador':

                return JsonResponse({
                    'success': False,
                    'message': 'Este pedido ya no puede modificarse.'
                })

            direcciones_query = ClienteDireccion.objects.filter(
                cliente=pedido.cliente
            ).select_related('direccion')
            
            direcciones = []
            for cd in direcciones_query:
                texto_completo = f"{cd.direccion.ciudad}, {cd.direccion.departamento} - {cd.direccion.detalle}"
                dir_pk = cd.direccion.direccion_id if hasattr(cd.direccion, 'direccion_id') else getattr(cd.direccion, 'id', None)
                
                direcciones.append({
                    'id': int(cd.cliente_direccion_id),      
                    'direccion_id': int(dir_pk) if dir_pk else '',
                    'direccion': texto_completo
                })
                
            metodos_query = MetodoEnvio.objects.all() 
            metodos_lista = []
            for m in metodos_query:
                metodos_lista.append({
                    'id': int(m.id),
                    'nombre': m.nombre
                })

            detalles = []
            bodega = Bodega.objects.filter(sucursal=pedido.sucursal).first()
            if not bodega:
                raise Exception(f'La sucursal {pedido.sucursal.nombre} no tiene una bodega asignada.')
            
            detalles_query = DetallePedido.objects.filter(pedido=pedido).select_related('producto')
            for d in detalles_query:
                inventario = Inventario.objects.filter(
                    producto=d.producto,
                    bodega=bodega
                ).first()
                
                stock_disponible = 0
                
                if inventario:
                    stock_disponible = inventario.stock
                
                
                detalles.append({
                    'id': d.producto_id,  
                    'producto': d.producto.nombre,
                    'precio': float(d.precio),
                    'cantidad': d.cantidad,
                    'stock': stock_disponible,
                    'subtotal': float(d.cantidad * d.precio)
                })

            direccion_base_id = pedido.direccion_envio.direccion_id if (pedido.direccion_envio and hasattr(pedido.direccion_envio, 'direccion_id')) else ''

            return JsonResponse({
                'success': True,
                'id': pedido.id,
                'codigo': pedido.codigo if hasattr(pedido, 'codigo') else f"PED-{pedido.pedido_id}",
                'cliente_id': pedido.cliente_id,
                'cliente': str(pedido.cliente),
                'id_sucursal': pedido.sucursal_id,
                'sucursal': pedido.sucursal.nombre,
                'entrega': pedido.tipo_entrega.nombre if pedido.tipo_entrega else '',
                'metodo_envio_id': pedido.metodo_envio_id if pedido.metodo_envio_id else '',
                'direccion_envio_id': pedido.direccion_envio_id if pedido.direccion_envio_id else '',
                'direccion_base_id': direccion_base_id,
                'direcciones_cliente': direcciones,
                'metodos_envio': metodos_lista,
                'total': float(pedido.total),
                'productos': detalles
            })

        # ==========================================================
        # 2. ACCIÓN POST: GUARDAR CAMBIOS INTERACTIVOS DEL CARRITO
        # ==========================================================
        elif request.method == 'POST':
            if not hasattr(request.user, 'empleado'):
                return JsonResponse({
                    'success': False, 
                    'message': 'No tiene permisos de empleado asignados.'
                })

            empleado = request.user.empleado
            pedido = Pedido.objects.select_related('estado', 'sucursal', 'vendedor').get(pk=pedido_id)

            if pedido.estado.nombre.lower() != 'borrador':
                return JsonResponse({
                    'success': False, 
                    'message': 'Solo se pueden editar pedidos en estado Borrador.'
                })

            if pedido.vendedor != empleado:
                return JsonResponse({
                    'success': False, 
                    'message': 'No posee permisos para modificar este pedido.'
                })

            data = json.loads(request.body)

            with transaction.atomic():
                # --- Guardado del tipo de entrega ---
                tipo_entrega = TipoEntrega.objects.get(pk=data['tipo_entrega'])
                metodo_envio = None
                direccion_envio = None

                if tipo_entrega.nombre.lower() == 'delivery':
                    if not data.get('metodo_envio'):
                        raise Exception('Debe seleccionar un método de envío para Delivery.')
                    if not data.get('direccion_envio'):
                        raise Exception('Debe asignar una dirección para el envío.')

                    metodo_envio = MetodoEnvio.objects.get(pk=data['metodo_envio'])
                    direccion_envio = ClienteDireccion.objects.get(pk=data['direccion_envio'])

                    if direccion_envio.cliente_id != pedido.cliente_id:
                        raise Exception('La dirección no coincide con el cliente asignado.')

                pedido.tipo_entrega = tipo_entrega
                pedido.metodo_envio = metodo_envio
                pedido.direccion_envio = direccion_envio

                # --- Procesamiento Inteligente de Productos ---
                productos = data.get('productos', [])
                if not productos:
                    raise Exception('El carrito está vacío. Inserte al menos un artículo.')

                bodega = Bodega.objects.filter(sucursal=pedido.sucursal).first()
                if not bodega:
                    raise Exception(f"No existe bodega asociada a la sucursal {pedido.sucursal.nombre}.")

                # 1. Mapeamos los IDs de productos enviados desde el Front
                productos_recibidos_ids = [int(item['producto']) for item in productos]

                # 2. Eliminamos ÚNICAMENTE los productos que el usuario quitó del modal
                DetallePedido.objects.filter(pedido=pedido).exclude(producto_id__in=productos_recibidos_ids).delete()

                total_acumulado = 0

                # 3. Iteramos para Actualizar o Crear conservando IDs
                for item in productos:
                    producto = Producto.objects.get(pk=item['producto'])
                    cantidad = int(item['cantidad'])

                    if cantidad <= 0:
                        raise Exception(f"Cantidad no permitida para el producto {producto.nombre}.")

                    inventario = Inventario.objects.filter(producto=producto, bodega=bodega).first()
                    if not inventario:
                        raise Exception(f"{producto.nombre} no se encuentra registrado en esta bodega.")
                    
                    if inventario.stock < cantidad:
                        raise Exception(f"Stock insuficiente para {producto.nombre}. Disponibles: {inventario.stock}")

                    precio_venta = producto.precio_venta
                    total_acumulado += (precio_venta * cantidad)

                    # 🔥 EL CAMBIO CLAVE: update_or_create busca por (pedido y producto)
                    # Si existe, actualiza cantidad y precio manteniendo el ID. Si no existe, lo crea.
                    DetallePedido.objects.update_or_create(
                        pedido=pedido,
                        producto=producto,
                        defaults={
                            'cantidad': cantidad,
                            'precio': precio_venta
                        }
                    )

                pedido.total = total_acumulado
                pedido.save()

            return JsonResponse({
                'success': True, 
                'message': 'Pedido guardado y recalculado con éxito.'
            })

    except Pedido.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'El pedido no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
 
        
        
@login_required
def detalle_pedido(request, pedido_id):
    # Traemos el pedido optimizando la relación con el usuario del vendedor
    pedido = Pedido.objects.select_related(
        'cliente',
        'vendedor__user',  # Optimizado para traer los nombres auth_user
        'sucursal',
        'estado',
        'tipo_entrega'
    ).get(pk=pedido_id)

    detalles = []
    for d in DetallePedido.objects.filter(pedido=pedido).select_related('producto'):
        detalles.append({
            'producto': d.producto.nombre,
            'cantidad': d.cantidad,
            'precio': float(d.precio),
            'subtotal': float(d.cantidad * d.precio)
        })

    return JsonResponse({
        'id': pedido.id,
        'codigo': pedido.codigo, # Agregado para mapear con tu input "detalleCodigo"
        'cliente': str(pedido.cliente),
        'vendedor': (
            f'{pedido.vendedor.user.first_name} {pedido.vendedor.user.last_name}'
        ) if pedido.vendedor and pedido.vendedor.user else 'Sin asignar',
        'sucursal': pedido.sucursal.nombre,
        'estado': pedido.estado.nombre,
        'entrega': pedido.tipo_entrega.nombre,
        'fecha': pedido.fecha.strftime('%d/%m/%Y %H:%M'),
        'total': float(pedido.total),
        'productos': detalles
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

        # GERENTE
        if rol == 'gerente':

            return JsonResponse({
                'success': False,
                'message': 'El gerente no puede modificar pedidos'
            })

        # VENDEDOR
        if rol == 'vendedor':

            # PENDIENTE -> BORRADOR (Tomar pedido)
            if (estado_actual == 'pendiente' and nuevo_estado_nombre == 'borrador'):

                if pedido.vendedor:

                    return JsonResponse({
                        'success': False,
                        'message': 'El pedido ya fue tomado por otro vendedor.'
                    })

                pedido.vendedor = empleado
                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Pedido tomado correctamente. Ahora puedes editarlo'
                })
                
            # VALIDACIÓN DE SEGURIDAD: Para cualquier otro cambio en Borrador, debe ser el dueño del pedido
            if estado_actual == 'borrador' and pedido.vendedor != empleado:
                return JsonResponse({
                    'success': False,
                    'message': 'No tienes permisos para modificar este pedido porque está asignado a otro vendedor.'
                })

            # BORRADOR -> EN BODEGA
            if (estado_actual == 'borrador' and nuevo_estado_nombre == 'en bodega'):
                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Pedido enviado a bodega con éxito.'
                })

            # PENDIENTE -> CANCELADO
            if (estado_actual in ['pendiente', 'borrador', 'en bodega'] and nuevo_estado_nombre == 'cancelado'):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Pedido cancelado correctamnete.'
                })


            return JsonResponse({
                'success': False,
                'message': 'Transición de estado no permitida para tu rol.'
            })
            
        # BODEGA
        if rol == 'bodega':

            if (
                estado_actual == 'en bodega'
                and
                nuevo_estado_nombre == 'preparado'
            ):

                pedido.estado = nuevo_estado
                pedido.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Pedido preparado correctamente'
                })

            return JsonResponse({
                'success': False,
                'message': 'Acción no permitida'
            })

        # ADMINISTRADOR
        if rol == 'administrador':

            pedido.estado = nuevo_estado
            pedido.save()

            return JsonResponse({
                'success': True,
                'message': 'Estado actualizado'
            })

        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos válidos'
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
        
        
@login_required
def obtener_pedido(request, pedido_id):

    pedido = get_object_or_404(
        Pedido,
        pk=pedido_id
    )

    bodega = Bodega.objects.filter(
        sucursal=pedido.sucursal
    ).first()

    productos = []

    for detalle in DetallePedido.objects.filter(
        pedido=pedido
    ).select_related('producto'):

        inventario = Inventario.objects.filter(
            producto=detalle.producto,
            bodega=bodega
        ).first()

        stock = 0

        if inventario:
            stock = inventario.stock + detalle.cantidad

        productos.append({

            'producto_id': detalle.producto.producto_id,
            'producto': detalle.producto.nombre,
            'cantidad': detalle.cantidad,
            'precio': float(detalle.precio),
            'stock': stock

        })

    return JsonResponse({

        'success': True,
        'productos': productos

    })
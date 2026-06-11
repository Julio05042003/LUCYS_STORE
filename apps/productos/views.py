from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q

from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import Inventario
from apps.usuarios.models import *
from apps.pedidos.models import *


# 🔐 función simple de role
def es_admin_o_bodega(user):
    try:
        empleado = Empleado.objects.select_related('rol').get(user=user)
        return empleado.rol.nombre.lower() in ['admin', 'gerente', 'bodega']
    except Empleado.DoesNotExist:
        return False




def tienda(request):
    # 1. Capturar la sucursal seleccionada (Prioriza parámetros GET, si no, recurre a la Sesión)
    sucursal_id = request.GET.get('sucursal')
    if sucursal_id:
        request.session['sucursal_id'] = sucursal_id
    else:
        sucursal_id = request.session.get('sucursal_id')

    # 2. Obtener las sucursales activas filtrando por su relación con el modelo Estado
    sucursales = Sucursal.objects.filter(estado__nombre='Activo').select_related('direccion')
    
    # NUEVO: Obtener la instancia completa de la sucursal para poder acceder a .telefonos
    sucursal_obj = Sucursal.objects.filter(pk=sucursal_id).first()
    
    telefonos_vendedor = []
    if sucursal_obj:
        # Filtramos aquí mismo los números de tipo vendedor activos
        telefonos_vendedor = sucursal_obj.telefonos.filter(
            tipo__iexact='vendedor', 
            estado__nombre='Activo'
        )
    
    # Inicializamos el contenedor de productos en vacío
    productos = []

    # 3. Si hay una sucursal seleccionada por el cliente, extraemos su inventario de bodega
    if sucursal_id:
        inventarios = Inventario.objects.select_related(
            'producto',
            'producto__categoria',
            'producto__marca',
            'producto__estado',
            'bodega__sucursal'
        ).filter(
            bodega__sucursal_id=sucursal_id,
            producto__estado__nombre='Activo', 
            stock__gt=0                        
        )

        # 4. Aplicar el filtro del select de categorías si el cliente seleccionó una
        categoria_id = request.GET.get('categoria')
        if categoria_id:
            inventarios = inventarios.filter(producto__categoria_id=categoria_id)

        # 5. Construir la lista de objetos Producto inyectando el stock real de la bodega
        for inv in inventarios:
            prod = inv.producto
            prod.stock = inv.stock  
            productos.append(prod)

    categorias = Categoria.objects.all()

    # =========================================================================
    # NUEVA LOGÍSTICA PARA EL CHECKOUT DE LA TIENDA
    # =========================================================================
    tipos_entrega = TipoEntrega.objects.all()
    metodos_envio = MetodoEnvio.objects.all()
    direcciones_cliente = None

    # Si el usuario inició sesión y tiene un perfil de cliente asociado, traemos sus direcciones
    if request.user.is_authenticated and hasattr(request.user, 'cliente'):
        direcciones_cliente = ClienteDireccion.objects.filter(
            cliente=request.user.cliente,
            estado__nombre='Activo' # Trae solo las direcciones que no estén deshabilitadas
        ).select_related('direccion')

    return render(request, 'tienda/index.html', {
        'productos': productos,
        'categorias': categorias,
        'sucursales': sucursales,
        'sucursal_seleccionada': int(sucursal_id) if sucursal_id else None,
        'telefonos_vendedor': telefonos_vendedor,
        
        # Nuevas variables añadidas al contexto para alimentar el modal
        'tipos_entrega': tipos_entrega,
        'metodos_envio': metodos_envio,
        'direcciones_cliente': direcciones_cliente,
    })
    
    
# 🔹 CREAR PRODUCTO
@login_required
def crear_producto(request):

    if request.method == 'POST':

        # =====================================
        # GUARDAR DATOS EN SESSION
        # =====================================

        request.session['modal_producto_data'] = {
            'codigo': request.POST.get('codigo', ''),
            'nombre': request.POST.get('nombre', ''),
            'descripcion': request.POST.get('descripcion', ''),
            'categoria': request.POST.get('categoria', ''),
            'marca': request.POST.get('marca', ''),
        }

        # ABRIR MODAL SI HAY ERROR
        request.session['abrir_modal'] = 'modalProducto'

        try:

            codigo = request.POST.get('codigo')
            nombre = request.POST.get('nombre')

            # VALIDACIONES
            if not codigo:
                raise Exception("El código es obligatorio")

            if not nombre:
                raise Exception("El nombre es obligatorio")

            # VALIDAR CODIGO DUPLICADO
            if Producto.objects.filter(codigo=codigo).exists():
                raise Exception("Ya existe un producto con ese código")

            estado_activo = Estado.objects.get(
                nombre__iexact='Activo'
            )

            # =====================================
            # CREAR PRODUCTO
            # =====================================

            producto = Producto.objects.create(

                codigo=codigo,

                nombre=nombre,

                descripcion=request.POST.get(
                    'descripcion',
                    ''
                ),

                categoria_id=request.POST.get('categoria'),

                marca_id=request.POST.get('marca'),

                estado=estado_activo,

                imagen=request.FILES.get('imagen')

            )

            # =====================================
            # LIMPIAR SESSION
            # =====================================

            if 'modal_producto_data' in request.session:
                del request.session['modal_producto_data']

            if 'abrir_modal' in request.session:
                del request.session['abrir_modal']

            messages.success(
                request,
                f"Producto '{producto.nombre}' creado correctamente"
            )

        except Estado.DoesNotExist:

            messages.error(
                request,
                "No existe un estado llamado 'Activo'"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return redirect('inventario')

# 🔹 EDITAR PRODUCTO
@login_required
def editar_producto(request, id):

    if not es_admin_o_bodega(request.user):
        return redirect('inventario')

    producto = get_object_or_404(
        Producto,
        pk=id
    )

    if request.method == 'POST':

        codigo = request.POST.get('codigo')

        # =========================
        # VALIDAR CÓDIGO DUPLICADO
        # =========================

        existe = Producto.objects.filter(
            codigo=codigo
        ).exclude(
            pk=producto.producto_id
        ).exists()

        if existe:

            messages.error(
                request,
                f"El código '{codigo}' ya existe"
            )

            # GUARDAR DATOS DEL MODAL
            request.session['modal_editar_data'] = {

                'id': producto.producto_id,
                'codigo': request.POST.get('codigo'),
                'nombre': request.POST.get('nombre'),
                'descripcion': request.POST.get('descripcion'),
                'categoria': request.POST.get('categoria'),
                'marca': request.POST.get('marca'),

                # imagen actual
                'imagen_actual': (
                    producto.imagen.url
                    if producto.imagen else ''
                )
            }

            request.session['abrir_modal'] = 'modalProductoEditar'

            return redirect('inventario')

        # =========================
        # ACTUALIZAR
        # =========================

        producto.codigo = codigo
        producto.nombre = request.POST.get('nombre')
        producto.descripcion = request.POST.get(
            'descripcion',
            ''
        )

        producto.categoria_id = request.POST.get(
            'categoria'
        )

        producto.marca_id = request.POST.get(
            'marca'
        )

        if request.FILES.get('imagen'):

            producto.imagen = request.FILES.get(
                'imagen'
            )

        producto.save()

        # LIMPIAR SESSION
        request.session.pop(
            'modal_editar_data',
            None
        )

        request.session.pop(
            'abrir_modal',
            None
        )

        messages.success(
            request,
            "Producto actualizado correctamente"
        )

    return redirect('inventario')

# 🔹 CATEGORIA
@login_required
def crear_categoria(request):

    if request.method == 'POST':

        nombre = request.POST.get(
            'nombre',
            ''
        ).strip()

        if not nombre:

            messages.error(
                request,
                'Debe ingresar un nombre para la categoría.'
            )

            request.session['abrir_modal'] = 'modalCategoriaCrear'

            return redirect('inventario')

        existe = Categoria.objects.filter(
            nombre__iexact=nombre
        ).exists()

        if existe:

            messages.error(
                request,
                'La categoría ya existe.'
            )

            request.session['abrir_modal'] = 'modalCategoriaCrear'

            return redirect('inventario')

        Categoria.objects.create(
            nombre=nombre
        )

        messages.success(
            request,
            'Categoría creada correctamente.'
        )

    return redirect('inventario')


@login_required
def editar_categoria(request, id):

    try:

        categoria = get_object_or_404(
            Categoria,
            pk=id
        )

        nombre = request.POST.get(
            'nombre',
            ''
        ).strip()

        if not nombre:

            return JsonResponse({

                'success': False,
                'message': 'Debe ingresar un nombre.'

            })

        existe = Categoria.objects.filter(
            nombre__iexact=nombre
        ).exclude(
            pk=id
        ).exists()

        if existe:

            return JsonResponse({

                'success': False,
                'message': 'Ya existe una categoría con ese nombre.'

            })

        categoria.nombre = nombre
        categoria.save()

        return JsonResponse({

            'success': True,
            'message': 'Categoría actualizada correctamente.'

        })

    except Exception as e:

        return JsonResponse({

            'success': False,
            'message': str(e)

        })

# 🔹 MARCA
@login_required
def crear_marca(request):

    if request.method == 'POST':

        nombre = request.POST.get(
            'nombre',
            ''
        ).strip()

        if not nombre:

            messages.error(
                request,
                'Debe ingresar un nombre para la marca.'
            )

            request.session['abrir_modal'] = 'modalMarcaCrear'

            return redirect('inventario')

        existe = Marca.objects.filter(
            nombre__iexact=nombre
        ).exists()

        if existe:

            messages.error(
                request,
                'La marca ya existe.'
            )

            request.session['abrir_modal'] = 'modalMarcaCrear'

            return redirect('inventario')

        Marca.objects.create(
            nombre=nombre
        )

        messages.success(
            request,
            'Marca creada correctamente.'
        )

    return redirect('inventario')

@login_required
def editar_marca(request, id):

    try:

        marca = get_object_or_404(
            Marca,
            pk=id
        )

        nombre = request.POST.get(
            'nombre',
            ''
        ).strip()

        if not nombre:

            return JsonResponse({

                'success': False,
                'message': 'Debe ingresar un nombre.'

            })

        existe = Marca.objects.filter(
            nombre__iexact=nombre
        ).exclude(
            pk=id
        ).exists()

        if existe:

            return JsonResponse({

                'success': False,
                'message': 'Ya existe una marca con ese nombre.'

            })

        marca.nombre = nombre
        marca.save()

        return JsonResponse({

            'success': True,
            'message': 'Marca actualizada correctamente.'

        })

    except Exception as e:

        return JsonResponse({

            'success': False,
            'message': str(e)

        })

@login_required
def producto_detalle_json(request, id):

    # =========================================
    # PRODUCTO
    # =========================================
    producto = Producto.objects.select_related(
        'categoria',
        'marca',
        'estado'
    ).get(pk=id)

    # =========================================
    # INVENTARIOS
    # =========================================
    inventarios = Inventario.objects.select_related(
        'bodega',
        'bodega__sucursal'
    ).filter(
        producto=producto
    )

    # =========================================
    # EMPLEADO
    # =========================================
    empleado = Empleado.objects.select_related(
        'rol'
    ).get(user=request.user)

    # =========================================
    # STOCK TOTAL
    # =========================================
    stock_total = inventarios.aggregate(
        total=Sum('stock')
    )['total'] or 0

    # =========================================
    # ARMAR INVENTARIOS
    # =========================================
    inventarios_data = []

    for i in inventarios:

        nombre_bodega = "Sin bodega"
        nombre_sucursal = "Sin sucursal"

        if i.bodega:
            nombre_bodega = i.bodega.nombre

            if i.bodega.sucursal:
                nombre_sucursal = i.bodega.sucursal.nombre

        inventarios_data.append({
            'bodega': nombre_bodega,
            'sucursal': nombre_sucursal,
            'stock': i.stock
        })

    # =========================================
    # RESPONSE
    # =========================================
    data = {

        'codigo': producto.codigo,

        'nombre': producto.nombre,

        'categoria': (
            producto.categoria.nombre
            if producto.categoria else ""
        ),

        'marca': (
            producto.marca.nombre
            if producto.marca else ""
        ),

        'descripcion': producto.descripcion or "",

        'imagen': (
            producto.imagen.url
            if producto.imagen else ""
        ),

        'precio_costo': float(
            producto.precio_c or 0
        ),

        'precio_venta': float(
            producto.precio_venta or 0
        ),

        'rol': empleado.rol.nombre,

        'stock': stock_total,

        'inventarios': inventarios_data
    }

    return JsonResponse(data)


def detalle_producto_tienda_json(request, id):
    """
    Vista pública para que los clientes consulten los detalles 
    de un producto desde el catálogo de la tienda.
    """
    try:
        # 1. Obtenemos el producto con su categoría de forma eficiente
        producto = Producto.objects.select_related('categoria').get(pk=id)

        # 2. Sumamos el stock total disponible en todas las bodegas/sucursales
        stock_total = Inventario.objects.filter(producto=producto).aggregate(
            total=Sum('stock')
        )['total'] or 0

        # 3. Estructuramos la respuesta JSON limpia
        data = {
            'producto_id': producto.producto_id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'categoria': producto.categoria.nombre if producto.categoria else "General",
            'marca': producto.marca.nombre if producto.marca else "Lucy's",
            'descripcion': producto.descripcion or "Sin descripción disponible.",
            'imagen': producto.imagen.url if producto.imagen else "",
            'precio_venta': float(producto.precio_venta or 0),
            'stock': stock_total
        }
        return JsonResponse(data)

    except Producto.DoesNotExist:
        return JsonResponse({'error': 'El artículo ya no está disponible.'}, status=404)



# 🔹 CAMBIAR ESTADO
@require_POST
@login_required
def cambiar_estado_producto(request, id):

    if not es_admin_o_bodega(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    producto = get_object_or_404(Producto, pk=id)

    if producto.estado.nombre.strip().lower() == "activo":
        nuevo_estado = Estado.objects.get(nombre__iexact="Inactivo")
    else:
        nuevo_estado = Estado.objects.get(nombre__iexact="Activo")

    producto.estado = nuevo_estado
    producto.save()

    return JsonResponse({'ok': True})


def buscar_productos(request):

    term = request.GET.get('term', '')

    productos = Producto.objects.filter(
        nombre__icontains=term,
        estado__nombre__iexact='Activo'
    )[:10]

    data = []

    for p in productos:

        data.append({
            'id': p.producto_id,
            'text': f"{p.nombre} - ${p.precio_venta}",
            'precio': float(p.precio_venta),
            'nombre': p.nombre
        })

    return JsonResponse(data, safe=False)

def buscar_productos_compra(request):

    term = request.GET.get('term', '')

    productos = Producto.objects.filter(

        Q(nombre__icontains=term) |
        Q(codigo__icontains=term)

    )[:10]

    data = []

    for p in productos:

        data.append({

            'id': p.producto_id,

            'text': f"{p.codigo} - {p.nombre}",

            'nombre': p.nombre

        })

    return JsonResponse(data, safe=False)
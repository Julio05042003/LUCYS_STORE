from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q

from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import Inventario
from apps.usuarios.models import Estado, Empleado

# 🔐 función simple de role
def es_admin_o_bodega(user):
    try:
        empleado = Empleado.objects.select_related('rol').get(user=user)
        return empleado.rol.nombre.lower() in ['admin', 'gerente', 'bodega']
    except Empleado.DoesNotExist:
        return False


def tienda(request):

    categoria_id = request.GET.get('categoria')

    productos = Producto.objects.select_related(
        'categoria',
        'marca',
        'estado'
    ).filter(
        estado__nombre='Activo'
    )

    if categoria_id:
        productos = productos.filter(
            categoria_id=categoria_id
        )

    # STOCK TOTAL
    for p in productos:

        p.stock = Inventario.objects.filter(
            producto=p
        ).aggregate(
            total=Sum('stock')
        )['total'] or 0

    categorias = Categoria.objects.all()

    return render(request, 'tienda/index.html', {
        'productos': productos,
        'categorias': categorias
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
        Categoria.objects.create(nombre=request.POST['nombre'])
        messages.success(request, "Categoría creada")

    return redirect('inventario')


@login_required
def editar_categoria(request, id):

    c = get_object_or_404(Categoria, pk=id)

    if request.method == 'POST':
        c.nombre = request.POST['nombre']
        c.save()

    return redirect('inventario')


# 🔹 MARCA
@login_required
def crear_marca(request):

    if request.method == 'POST':
        nombre = request.POST.get('nombre')

        if nombre:
            Marca.objects.create(nombre=nombre)
            messages.success(request, "Marca creada correctamente")
        else:
            messages.error(request, "El nombre es obligatorio")

    return redirect('inventario')


@login_required
def editar_marca(request, id):

    m = get_object_or_404(Marca, pk=id)

    if request.method == 'POST':
        m.nombre = request.POST['nombre']
        m.save()

    return redirect('inventario')



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
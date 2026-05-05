from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from apps.productos.models import Producto, Categoria, Marca
from apps.inventario.models import Inventario
from apps.usuarios.models import Estado, Empleado

# 🔐 función simple de roles (ajústala a tu lógica real)
def es_admin_o_bodega(user):
    return hasattr(user, 'empleado') and user.empleado.rol in ['ADMIN', 'GERENTE', 'BODEGA']


def catalogo(request):
    productos = Producto.objects.all()
    return render(request, 'tienda/index.html', {'productos': productos})


# 🔹 CREAR PRODUCTO
@login_required
def crear_producto(request):

    if request.method == 'POST':
        Producto.objects.create(
            codigo=request.POST['codigo'],
            nombre=request.POST['nombre'],
            categoria_id=request.POST['categoria'],
            marca_id=request.POST['marca'],
            estado=Estado.objects.get(pk=1),
            imagen=request.FILES.get('imagen')
        )

        messages.success(request, "Producto creado")

    return redirect('inventario')


# 🔹 EDITAR PRODUCTO
@login_required
def editar_producto(request, id):

    if not es_admin_o_bodega(request.user):
        return redirect('inventario')

    producto = get_object_or_404(Producto, pk=id)

    if request.method == 'POST':
        producto.codigo = request.POST['codigo']
        producto.nombre = request.POST['nombre']
        producto.descripcion = request.POST.get('descripcion', '')
        producto.categoria_id = request.POST['categoria']
        producto.marca_id = request.POST['marca']

        if request.FILES.get('imagen'):
            producto.imagen = request.FILES.get('imagen')

        producto.save()

        messages.success(request, "Producto actualizado")

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
        Marca.objects.create(nombre=request.POST['nombre'])
        messages.success(request, "Marca creada")

    return redirect('inventario')


@login_required
def editar_marca(request, id):

    m = get_object_or_404(Marca, pk=id)

    if request.method == 'POST':
        m.nombre = request.POST['nombre']
        m.save()

    return redirect('inventario')


# 🔹 DETALLE JSON
def producto_detalle_json(request, id):

    producto = Producto.objects.select_related('categoria','marca','estado').get(pk=id)

    inventarios = Inventario.objects.select_related('ubicacion').filter(producto=producto)

    data = {
        'codigo': producto.codigo,
        'nombre': producto.nombre,
        'categoria': producto.categoria.nombre,
        'marca': producto.marca.nombre,
        'estado': producto.estado.nombre,
        'stock': inventarios.aggregate(total=Sum('stock'))['total'] or 0,
        'inventarios': [
            {
                'ubicacion': i.ubicacion.nombre,
                'stock': i.stock
            } for i in inventarios
        ]
    }

    return JsonResponse(data)


# 🔹 CAMBIAR ESTADO
@require_POST
@login_required
def cambiar_estado_producto(request, id):

    if not es_admin_o_bodega(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    producto = get_object_or_404(Producto, pk=id)

    if producto.estado.nombre == "Activo":
        producto.estado = Estado.objects.get(nombre="Inactivo")
    else:
        producto.estado = Estado.objects.get(nombre="Activo")

    producto.save()

    return JsonResponse({'ok': True})
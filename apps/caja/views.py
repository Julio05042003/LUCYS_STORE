from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone

from .models import *
from apps.usuarios.models import Estado, Empleado


# ============================================
# CREAR CAJA
# ============================================

def crear_caja(request):

    empleado = request.user.empleado

    if empleado.rol.nombre != "Gerente":
        return redirect('caja')

    if request.method == "POST":

        nombre = request.POST.get('nombre').strip()

        # VALIDAR SI YA EXISTE EN ESA SUCURSAL
        existe = Caja.objects.filter(
            nombre__iexact=nombre,
            ubicacion=empleado.ubicacion
        ).exists()

        if existe:
            request.session['abrir_modal_caja'] = True

            messages.error(
                request,
                f"Ya existe una caja con el nombre '{nombre}' en esta sucursal."
            )
            return redirect('caja')

        Caja.objects.create(
            nombre=nombre,
            ubicacion=empleado.ubicacion
        )

        messages.success(request, "Caja creada correctamente")

    return redirect('caja')


# ============================================
# VISTA PRINCIPAL
# ============================================

def caja_view(request):

    empleado = request.user.empleado
    user = request.user

    cajas = Caja.objects.filter(
        ubicacion=empleado.ubicacion
    )

    total_ingresos = Decimal('0')
    total_egresos = Decimal('0')

    # RECORRER CADA CAJA
    for caja in cajas:

        apertura = AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre__in=['Abierta', 'En arqueo']
        ).select_related(
            'empleado',
            'estado'
        ).order_by('-id').first()

        caja.apertura_actual = apertura

        ingresos = Decimal('0')
        egresos = Decimal('0')

        if apertura:

            movimientos = MovimientoCaja.objects.filter(
                apertura=apertura
            )

            ingresos = movimientos.filter(
                tipo='INGRESO'
            ).aggregate(
                total=Sum('monto')
            )['total'] or Decimal('0')

            egresos = movimientos.filter(
                tipo='EGRESO'
            ).aggregate(
                total=Sum('monto')
            )['total'] or Decimal('0')

            caja.ingresos = ingresos
            caja.egresos = egresos
            caja.total = apertura.saldo_inicial + ingresos - egresos

            total_ingresos += ingresos
            total_egresos += egresos

        else:

            caja.ingresos = Decimal('0')
            caja.egresos = Decimal('0')
            caja.total = Decimal('0')

    abrir_modal_caja = request.session.pop(
        'abrir_modal_caja',
        False
    )

    abrir_modal_apertura = request.session.pop(
        'abrir_modal_apertura',
        False
    )
    
    abrir_modal_movimiento = request.session.pop(
        'abrir_modal_movimiento',
        False
    )

    abrir_modal_arqueo = request.session.pop(
        'abrir_modal_arqueo',
        False
    )

    abrir_modal_cierre = request.session.pop(
        'abrir_modal_cierre',
        False
    )

    contexto = {
        'empleado': empleado,
        'user': user,
        'cajas': cajas,
        'total_cajas': cajas.count(),
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'total_general': total_ingresos - total_egresos,
        'abrir_modal_caja': abrir_modal_caja,
        'abrir_modal_apertura': abrir_modal_apertura,
        'abrir_modal_movimiento': abrir_modal_movimiento,
        'abrir_modal_arqueo': abrir_modal_arqueo,
        'abrir_modal_cierre': abrir_modal_cierre,
    }

    # =========================
    # GERENTE
    # =========================
    if empleado.rol.nombre == "Gerente":
        return render(
            request,
            'empleados/caja_gerente.html',
            contexto
        )

    # =========================
    # CAJERO
    # =========================
    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).order_by('-id').first()

    movimientos = []
    ingresos = Decimal('0')
    egresos = Decimal('0')

    if apertura:

        movimientos = MovimientoCaja.objects.filter(
            apertura=apertura
        )

        ingresos = movimientos.filter(
            tipo='INGRESO'
        ).aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        egresos = movimientos.filter(
            tipo='EGRESO'
        ).aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

    total = (
        apertura.saldo_inicial if apertura else 0
    ) + ingresos - egresos

    contexto.update({
        'apertura': apertura,
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'total': total
    })

    return render(
        request,
        'empleados/caja.html',
        contexto
    )


# ============================================
# ABRIR CAJA
# ============================================

def abrir_caja(request):

    empleado = request.user.empleado

    if empleado.rol.nombre.lower() != "cajero":

        messages.error(
            request,
            "No tienes permisos para abrir caja."
        )

        request.session['abrir_modal_apertura'] = True

        return redirect('caja')

    if request.method == "POST":

        caja_id = request.POST.get("caja_id")

        saldo_inicial = Decimal(
            request.POST.get("saldo_inicial") or 0
        )

        caja = Caja.objects.filter(
            id=caja_id,
            ubicacion=empleado.ubicacion
        ).first()

        if not caja:

            messages.error(
                request,
                "La caja seleccionada no existe."
            )

            request.session['abrir_modal_apertura'] = True

            return redirect('caja')

        # VALIDAR SI YA ESTÁ ABIERTA
        caja_abierta = AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre='Abierta'
        ).exists()

        if caja_abierta:

            messages.error(
                request,
                f"La caja {caja.nombre} ya está abierta."
            )

            request.session['abrir_modal_apertura'] = True

            return redirect('caja')

        estado = Estado.objects.get(nombre='Abierta')

        AperturaCaja.objects.create(
            caja=caja,
            empleado=empleado,
            estado=estado,
            saldo_inicial=saldo_inicial
        )

        messages.success(
            request,
            f"La caja {caja.nombre} fue abierta correctamente."
        )

    return redirect('caja')


# ============================================
# MOVIMIENTO
# ============================================
# ============================================
# MOVIMIENTO
# ============================================
def crear_movimiento(request):

    empleado = request.user.empleado

    if empleado.rol.nombre != "Cajero":

        request.session['abrir_modal_movimiento'] = True

        messages.error(
            request,
            "No tienes permisos para realizar movimientos."
        )

        return redirect('caja')

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).order_by('-id').first()

    if not apertura:

        request.session['abrir_modal_movimiento'] = True

        messages.error(
            request,
            "No hay una caja abierta."
        )

        return redirect('caja')

    tipo = request.POST.get('tipo')

    monto = Decimal(
        request.POST.get('monto') or 0
    )

    descripcion = request.POST.get('descripcion')

    # VALIDAR MONTO
    if monto <= 0:

        request.session['abrir_modal_movimiento'] = True

        messages.error(
            request,
            "Ingrese un monto válido."
        )

        return redirect('caja')

    # CALCULAR TOTAL ACTUAL EN CAJA
    ingresos = MovimientoCaja.objects.filter(
        apertura=apertura,
        tipo='INGRESO'
    ).aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0')

    egresos = MovimientoCaja.objects.filter(
        apertura=apertura,
        tipo='EGRESO'
    ).aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0')

    total_caja = (
        apertura.saldo_inicial +
        ingresos -
        egresos
    )

    # VALIDAR EGRESO
    if tipo == "EGRESO" and monto > total_caja:

        request.session['abrir_modal_movimiento'] = True

        messages.error(
            request,
            f"No hay suficiente efectivo en caja. Disponible: C${total_caja}"
        )

        return redirect('caja')

    # CREAR MOVIMIENTO
    MovimientoCaja.objects.create(
        apertura=apertura,
        tipo=tipo,
        monto=monto,
        descripcion=descripcion
    )

    request.session['abrir_modal_movimiento'] = True

    messages.success(
        request,
        "Movimiento registrado correctamente."
    )

    return redirect('caja')

# ============================================
# INICIAR ARQUEO
# ============================================
@require_POST
def iniciar_arqueo(request):

    empleado = request.user.empleado

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre='Abierta'
    ).order_by('-id').first()

    if not apertura:
        return JsonResponse({"status": "error"})

    estado = Estado.objects.get(nombre='En arqueo')

    apertura.estado = estado
    apertura.save()

    return JsonResponse({"status": "ok"})


# ============================================
# CREAR ARQUEO (CORREGIDO)
# ============================================
def crear_arqueo(request):

    if request.method == "POST":

        apertura = get_object_or_404(
            AperturaCaja,
            id=request.POST.get("apertura_id")
        )

        efectivo_real = Decimal(request.POST.get("efectivo_real") or 0)
        
        if efectivo_real <= 0:
            request.session['abrir_modal_arqueo'] = True
            messages.error(request, "Debe ingresar efectivo válido.")
            return redirect('caja')

        ingresos = MovimientoCaja.objects.filter(
            apertura=apertura,
            tipo="INGRESO"
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        egresos = MovimientoCaja.objects.filter(
            apertura=apertura,
            tipo="EGRESO"
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        monto_sistema = apertura.saldo_inicial + ingresos - egresos

        ArqueoCaja.objects.create(
            apertura=apertura,
            empleado=request.user.empleado,
            monto_sistema=monto_sistema,
            monto_fisico=efectivo_real,
            observacion=request.POST.get("observacion"),
            justificacion=request.POST.get("justificacion")
        )

        # después de generar arqueo → vuelve a ABIERTO
        apertura.estado = Estado.objects.get(nombre='Abierta')
        apertura.save()

        messages.success(request, "Arqueo registrado correctamente")

        return redirect("caja")


# ============================================
# CERRAR CAJA
# ============================================
def cerrar_caja(request):

    empleado = request.user.empleado

    if request.method == "POST":

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre__in=['Abierta', 'En arqueo']
        ).order_by('-id').first()

        if not apertura:
            request.session['abrir_modal_cierre'] = True
            messages.error(request, "No hay caja activa")
            return redirect('caja')

        arqueo = ArqueoCaja.objects.filter(
            apertura=apertura
        ).order_by('-id').last()

        if not arqueo:
            request.session['abrir_modal_cierre'] = True
            messages.error(request, "Debe realizar arqueo antes de cerrar")
            return redirect('caja')

        estado_cerrada = Estado.objects.get(nombre='Cerrada')

        apertura.estado = estado_cerrada
        apertura.saldo_final = arqueo.monto_fisico
        apertura.fecha_cierre = timezone.now()
        apertura.save()

        messages.success(request, "Caja cerrada correctamente")

    return redirect('caja')
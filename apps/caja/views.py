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
        nombre = request.POST.get('nombre')

        if nombre:
            Caja.objects.create(
                nombre=nombre,
                ubicacion=empleado.ubicacion
            )

    return redirect('caja')


# ============================================
# VISTA PRINCIPAL
# ============================================
def caja_view(request):

    empleado = request.user.empleado
    user = request.user

    cajas = Caja.objects.filter(ubicacion=empleado.ubicacion)

    aperturas = AperturaCaja.objects.filter(
        caja__ubicacion=empleado.ubicacion,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).select_related('caja', 'empleado', 'estado')

    total_ingresos = Decimal('0')
    total_egresos = Decimal('0')

    for apertura in aperturas:

        movimientos = MovimientoCaja.objects.filter(apertura=apertura)

        ingresos = movimientos.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        egresos = movimientos.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        apertura.ingresos = ingresos
        apertura.egresos = egresos
        apertura.total = apertura.saldo_inicial + ingresos - egresos

        total_ingresos += ingresos
        total_egresos += egresos

    contexto = {
        'empleado': empleado,
        'user': user,
        'cajas': cajas,
        'aperturas': aperturas,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'total_general': total_ingresos - total_egresos,
    }

    if empleado.rol.nombre == "Gerente":
        return render(request, 'empleados/caja_gerente.html', contexto)

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).order_by('-id').first()

    movimientos = []
    ingresos = Decimal('0')
    egresos = Decimal('0')

    if apertura:
        movimientos = MovimientoCaja.objects.filter(apertura=apertura)

        ingresos = movimientos.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        egresos = movimientos.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

    total = (apertura.saldo_inicial if apertura else 0) + ingresos - egresos

    contexto.update({
        'apertura': apertura,
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'total': total
    })

    return render(request, 'empleados/caja.html', contexto)


# ============================================
# ABRIR CAJA
# ============================================
def abrir_caja(request):

    empleado = request.user.empleado

    if empleado.rol.nombre != "Cajero":
        return redirect('caja')

    if request.method == "POST":

        caja_id = request.POST.get("caja_id")
        saldo_inicial = Decimal(request.POST.get("saldo_inicial") or 0)

        caja = Caja.objects.filter(
            id=caja_id,
            ubicacion=empleado.ubicacion
        ).first()

        if not caja:
            return redirect('caja')

        if AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre='Abierta'
        ).exists():
            return redirect('caja')

        estado = Estado.objects.get(nombre='Abierta')

        AperturaCaja.objects.create(
            caja=caja,
            empleado=empleado,
            estado=estado,
            saldo_inicial=saldo_inicial
        )

    return redirect('caja')


# ============================================
# MOVIMIENTO
# ============================================
def crear_movimiento(request):

    empleado = request.user.empleado

    if empleado.rol.nombre != "Cajero":
        return JsonResponse({'status': 'error'})

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).order_by('-id').first()

    if not apertura:
        return JsonResponse({'status': 'error'})

    MovimientoCaja.objects.create(
        apertura=apertura,
        tipo=request.POST.get('tipo'),
        monto=Decimal(request.POST.get('monto') or 0),
        descripcion=request.POST.get('descripcion')
    )

    return JsonResponse({'status': 'success'})


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

        # 🔥 AQUÍ ESTABA TU ERROR
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
            messages.error(request, "No hay caja activa")
            return redirect('caja')

        arqueo = ArqueoCaja.objects.filter(
            apertura=apertura
        ).order_by('-id').last()

        if not arqueo:
            messages.error(request, "Debe realizar arqueo antes de cerrar")
            return redirect('caja')

        estado_cerrada = Estado.objects.get(nombre='Cerrada')

        apertura.estado = estado_cerrada
        apertura.saldo_final = arqueo.monto_fisico
        apertura.fecha_cierre = timezone.now()
        apertura.save()

        messages.success(request, "Caja cerrada correctamente")

    return redirect('caja')
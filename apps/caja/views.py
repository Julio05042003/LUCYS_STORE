from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Caja, AperturaCaja, MovimientoCaja, ArqueoCaja
from apps.usuarios.models import Estado


# ============================================
# 🧩 VISTA PRINCIPAL DE CAJA
# ============================================
def caja_view(request):
    empleado = request.user.empleado

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        caja__ubicacion=empleado.ubicacion,
        estado__nombre='ABIERTA'
    ).last()

    movimientos = []
    ingresos = 0
    egresos = 0

    if apertura:
        movimientos = MovimientoCaja.objects.filter(apertura=apertura)

        ingresos = movimientos.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
        egresos = movimientos.filter(tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0

    total = (apertura.saldo_inicial if apertura else 0) + ingresos - egresos

    return render(request, 'empleados/caja.html', {
        'empleado': empleado,
        'apertura': apertura,
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'total': total
    })


# ============================================
# 🧩 CREAR CAJA (SOLO GERENTE)
# ============================================
def crear_caja(request):
    empleado = request.user.empleado

    if empleado.rol.nombre != "Gerente":
        return redirect('index_empleados')

    if Caja.objects.filter(ubicacion=empleado.ubicacion).exists():
        return redirect('caja')

    Caja.objects.create(
        nombre=f"Caja {empleado.ubicacion.nombre}",
        ubicacion=empleado.ubicacion
    )

    return redirect('caja')


# ============================================
# 🧩 ABRIR CAJA
# ============================================
def abrir_caja(request):
    if request.method == "POST":
        empleado = request.user.empleado

        caja = Caja.objects.filter(
            ubicacion=empleado.ubicacion
        ).first()

        if not caja:
            return redirect('caja')

        if AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).exists():
            return redirect('caja')

        estado = Estado.objects.get(nombre='ABIERTA')

        AperturaCaja.objects.create(
            caja=caja,
            empleado=empleado,
            estado=estado,
            saldo_inicial=request.POST['saldo_inicial']
        )

    return redirect('caja')


# ============================================
# 🧩 CREAR MOVIMIENTO (MANUAL)
# ============================================
def crear_movimiento(request):
    if request.method == "POST":
        empleado = request.user.empleado

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        monto = float(request.POST['monto'])

        if monto <= 0:
            return redirect('caja')

        MovimientoCaja.objects.create(
            apertura=apertura,
            tipo=request.POST['tipo'],  # INGRESO / EGRESO
            monto=monto,
            descripcion=request.POST['descripcion']
        )

    return redirect('caja')


# ============================================
# 🧩 CREAR ARQUEO
# ============================================
def crear_arqueo(request):
    if request.method == "POST":
        empleado = request.user.empleado

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        efectivo_real = float(request.POST['efectivo_real'])

        movimientos = MovimientoCaja.objects.filter(apertura=apertura)

        ingresos = movimientos.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
        egresos = movimientos.filter(tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0

        esperado = apertura.saldo_inicial + ingresos - egresos
        diferencia = efectivo_real - esperado

        ArqueoCaja.objects.create(
            apertura=apertura,
            efectivo_sistema=esperado,
            efectivo_real=efectivo_real,
            diferencia=diferencia,
            observacion=request.POST.get('observacion', ''),
            empleado=empleado
        )

    return redirect('caja')


# ============================================
# 🧩 CERRAR CAJA
# ============================================
def cerrar_caja(request):
    if request.method == "POST":
        empleado = request.user.empleado

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        arqueo = ArqueoCaja.objects.filter(apertura=apertura).last()

        if not arqueo:
            return redirect('caja')  # obligatorio arqueo antes de cerrar

        estado = Estado.objects.get(nombre='CERRADA')

        apertura.estado = estado
        apertura.saldo_final = arqueo.efectivo_real
        apertura.save()

    return redirect('caja')


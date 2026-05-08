from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Caja, AperturaCaja, MovimientoCaja, ArqueoCaja
from apps.usuarios.models import Estado, Empleado


# ============================================
# 🧩 VISTA PRINCIPAL DE CAJA
# ============================================
def caja_view(request):
    empleado = request.user.empleado
    user = request.user

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        caja__ubicacion=empleado.ubicacion,
        estado__nombre='ABIERTA'
    ).last()

    cajas = Caja.objects.filter(ubicacion=empleado.ubicacion)

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
        'user': user,
        'apertura': apertura,
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'total': total,
        'cajas': cajas
    })

# ============================================
# 🧩 CREAR CAJA (SOLO GERENTE)
# ============================================
def crear_caja(request):
    empleado = request.user.empleado

    if empleado.rol.nombre != "Gerente":
        return redirect('caja')

    if request.method == "POST":

        cajero_id = request.POST.get("cajero_id")

        cajero = Empleado.objects.filter(pk=cajero_id).first()

        if not cajero:
            return redirect('caja')

        if cajero.rol.nombre != "Caja":
            return redirect('caja')

        # SOLO UNA CAJA POR UBICACIÓN
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
    empleado = request.user.empleado

    # ✔️ rol correcto
    if empleado.rol.nombre != "Cajero":
        return redirect('caja')

    if request.method == "POST":

        caja_id = request.POST.get("caja_id")
        saldo_inicial = request.POST.get("saldo_inicial")

        # 🔴 VALIDACIÓN 1: caja obligatoria
        if not caja_id:
            return redirect('caja')

        caja = Caja.objects.filter(
            id=caja_id,
            ubicacion=empleado.ubicacion
        ).first()

        if not caja:
            return redirect('caja')

        # 🔴 VALIDACIÓN 2: evitar doble apertura de la misma caja
        if AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre='ABIERTA'
        ).exists():
            return redirect('caja')

        # 🔴 VALIDACIÓN 3: el cajero solo puede tener 1 caja abierta
        if AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).exists():
            return redirect('caja')

        estado = Estado.objects.get(nombre='Abierta')

        AperturaCaja.objects.create(
            caja=caja,
            empleado=empleado,
            estado=estado,
            saldo_inicial=float(saldo_inicial or 0)
        )

    return redirect('caja')

# ============================================
# 🧩 CREAR MOVIMIENTO (MANUAL)
# ============================================
def crear_movimiento(request):
    empleado = request.user.empleado

    if empleado.rol.nombre != "Caja":
        return redirect('caja')

    if request.method == "POST":

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        monto = float(request.POST.get('monto', 0))

        if monto <= 0:
            return redirect('caja')

        MovimientoCaja.objects.create(
            apertura=apertura,
            tipo=request.POST['tipo'],
            monto=monto,
            descripcion=request.POST['descripcion']
        )

    return redirect('caja')

# ============================================
# 🧩 CREAR ARQUEO
# ============================================
def crear_arqueo(request):
    empleado = request.user.empleado

    if empleado.rol.nombre != "Caja":
        return redirect('caja')

    if request.method == "POST":

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        efectivo_real = float(request.POST.get('efectivo_real', 0))

        movimientos = MovimientoCaja.objects.filter(apertura=apertura)

        ingresos = movimientos.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
        egresos = movimientos.filter(tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0

        esperado = float(apertura.saldo_inicial) + ingresos - egresos
        diferencia = efectivo_real - esperado

        ArqueoCaja.objects.create(
            apertura=apertura,
            empleado=empleado,
            saldo_sistema=esperado,
            saldo_real=efectivo_real,
            diferencia=diferencia,
            justificacion=request.POST.get('justificacion', ''),
            estado=Estado.objects.get(nombre='REGISTRADO')
        )

    return redirect('caja')

# ============================================
# 🧩 CERRAR CAJA
# ============================================
def cerrar_caja(request):
    empleado = request.user.empleado

    if request.method == "POST":

        apertura = AperturaCaja.objects.filter(
            empleado=empleado,
            estado__nombre='ABIERTA'
        ).last()

        if not apertura:
            return redirect('caja')

        arqueo = ArqueoCaja.objects.filter(apertura=apertura).last()

        if not arqueo:
            return redirect('caja')

        estado = Estado.objects.get(nombre='CERRADA')

        apertura.estado = estado
        apertura.saldo_final = arqueo.saldo_real
        apertura.save()

    return redirect('caja')


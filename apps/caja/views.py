from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
from .models import *
from apps.usuarios.models import Estado
from apps.ventas.models import Venta
from decimal import Decimal
from django.db.models.functions import Coalesce

CONCEPTOS_VALIDOS = {

    'INGRESO': {

        'CORDOBA': [

            'Fondo adicional',
            'Ajuste positivo',
            'Depósito bancario retirado',
            'Cambio de sencillo recibido',
            'Recuperación de faltante',
            'Ingreso administrativo',

        ],

        'DOLAR': [

            'Ingreso administrativo USD',
            'Reposición USD',
            'Depósito bancario retirado',

        ]
    },

    'EGRESO': {

        'CORDOBA': [

            'Pago de servicios',
            'Compra menor',
            'Compra de papelería',
            'Viáticos',
            'Transporte',
            'Ajuste negativo',
            'Retiro gerencial',
            'Depósito bancario C$',

        ],

        'DOLAR': [

            'Deposito bancario USD',

        ]
    }
}


# ============================================
# CREAR CAJA
# ============================================

def crear_caja(request):

    if request.method != "POST":
        return redirect('caja')

    try:
        empleado = request.user.empleado
    except:
        messages.error(request, "Usuario sin empleado asociado.")
        return redirect('caja')

    if empleado.rol.nombre.lower().strip() != "gerente":
        messages.error(request, "No tienes permisos.")
        return redirect('caja')

    nombre = request.POST.get('nombre', '').strip()

    if not nombre:
        messages.error(request, "Ingrese un nombre.")
        request.session['abrir_modal_caja'] = True
        return redirect('caja')

    if Caja.objects.filter(nombre__iexact=nombre, sucursal=empleado.sucursal).exists():
        messages.error(request, "Ya existe una caja con ese nombre.")
        request.session['abrir_modal_caja'] = True
        return redirect('caja')

    Caja.objects.create(
        nombre=nombre,
        sucursal=empleado.sucursal
    )

    messages.success(request, "Caja creada correctamente.")
    return redirect('caja')


# ============================================
# CALCULAR TOTALES
# ============================================

def calcular_totales_apertura(apertura):

    movimientos = MovimientoCaja.objects.filter(
        apertura=apertura
    )

    tasa = apertura.tipocambio.valor

    # =========================================
    # CORDOBAS
    # =========================================

    ingresos_cordoba = movimientos.filter(
        tipo='INGRESO',
        moneda='CORDOBA'
    ).exclude(
        Q(descripcion__icontains='Transferencia') |
        Q(descripcion__icontains='Tarjeta')
        
    ).aggregate(
        total=Coalesce(
            Sum('monto'),
            Decimal('0')
        )
    )['total']

    egresos_cordoba = movimientos.filter(
        tipo='EGRESO',
        moneda='CORDOBA'
    ).aggregate(
        total=Coalesce(
            Sum('monto'),
            Decimal('0')
        )
    )['total']

    subtotal_cordoba = (
        apertura.saldo_inicial +
        ingresos_cordoba -
        egresos_cordoba
    )

    # =========================================
    # DOLARES
    # =========================================

    ingresos_dolar = movimientos.filter(
        tipo='INGRESO',
        moneda='DOLAR'
    ).exclude(
        Q(descripcion__icontains='Transferencia') |
        Q(descripcion__icontains='Tarjeta')
    ).aggregate(
        total=Coalesce(
            Sum('monto'),
            Decimal('0')
        )
    )['total']

    egresos_dolar = movimientos.filter(
        tipo='EGRESO',
        moneda='DOLAR'
    ).aggregate(
        total=Coalesce(
            Sum('monto'),
            Decimal('0')
        )
    )['total']

    subtotal_dolar = (
        ingresos_dolar -
        egresos_dolar
    )

    # =========================================
    # CONVERSION
    # =========================================

    conversion_dolar = (
        subtotal_dolar * tasa
    )

    # =========================================
    # TOTAL GENERAL
    # =========================================

    total_general = (
        subtotal_cordoba +
        conversion_dolar
    )

    return {

        # CORDOBAS
        'ingresos_cordoba': ingresos_cordoba,
        'egresos_cordoba': egresos_cordoba,
        'subtotal_cordoba': subtotal_cordoba,

        # DOLARES
        'ingresos_dolar': ingresos_dolar,
        'egresos_dolar': egresos_dolar,
        'subtotal_dolar': subtotal_dolar,

        # CONVERSION
        'conversion_dolar': conversion_dolar,

        # TOTALES
        'total_cordoba': subtotal_cordoba,
        'total_dolar': subtotal_dolar,
        'total_general': total_general,
    }


# ============================================
# VISTA PRINCIPAL
# ============================================

from decimal import Decimal
from django.shortcuts import render
from .models import (
    Caja,
    AperturaCaja,
    MovimientoCaja,
    ArqueoCaja
)

def caja_view(request):

    empleado = request.user.empleado

    cajas = Caja.objects.filter(
        sucursal=empleado.sucursal
    ).prefetch_related(
        'aperturacaja_set',
        'aperturacaja_set__arqueocaja_set'
    )

    # RECORRER CAJAS
    for caja in cajas:

        # APERTURA ACTUAL
        apertura_actual = AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre__in=[
                'Abierta',
                'En arqueo'
            ]
        ).select_related(
            'empleado',
            'estado',
            'tipocambio'
        ).order_by(
            '-apertura_id'
        ).first()

        caja.apertura_actual = apertura_actual

        # =========================================
        # HISTORIAL APERTURAS
        # =========================================

        caja.historial_aperturas = AperturaCaja.objects.filter(
            caja=caja
        ).select_related(
            'empleado',
            'estado',
            'tipocambio'
        ).prefetch_related(
            'arqueocaja_set'
        ).order_by(
            '-apertura_id'
        )

        # =========================================
        # VALORES DEFAULT
        # =========================================

        caja.saldo_inicial = Decimal('0.00')

        caja.ingresos_cordoba = Decimal('0.00')
        caja.egresos_cordoba = Decimal('0.00')
        caja.total_cordoba = Decimal('0.00')

        caja.ingresos_dolar = Decimal('0.00')
        caja.egresos_dolar = Decimal('0.00')
        caja.total_dolar = Decimal('0.00')

        caja.total_general = Decimal('0.00')

        # =========================================
        # SI EXISTE APERTURA
        # =========================================

        if apertura_actual:

            totales = calcular_totales_apertura(
                apertura_actual
            )

            caja.saldo_inicial = (
                apertura_actual.saldo_inicial
            )

            caja.ingresos_cordoba = (
                totales['ingresos_cordoba']
            )

            caja.egresos_cordoba = (
                totales['egresos_cordoba']
            )

            caja.total_cordoba = (
                totales['total_cordoba']
            )

            caja.ingresos_dolar = (
                totales['ingresos_dolar']
            )

            caja.egresos_dolar = (
                totales['egresos_dolar']
            )

            caja.total_dolar = (
                totales['total_dolar']
            )

            caja.total_general = (
                totales['total_general']
            )

        # =========================================
        # HISTORIAL ARQUEOS
        # =========================================

        for apertura in caja.historial_aperturas:

            apertura.historial_arqueos = ArqueoCaja.objects.filter(
                apertura=apertura
            ).select_related(
                'empleado'
            ).order_by(
                '-arqueo_id'
            )

    # CONTEXTO BASE
    contexto = {

        'empleado': empleado,

        'cajas': cajas,

        'abrir_modal_caja':
            request.session.pop(
                'abrir_modal_caja',
                False
            ),
    }

    # GERENTE
    if empleado.rol.nombre in ["Gerente", "Administrador"]:

        total_cajas = cajas.count()

        saldo_inicial_cordoba = Decimal('0.00')

        ingresos_cordoba = Decimal('0.00')
        egresos_cordoba = Decimal('0.00')
        total_cordoba = Decimal('0.00')

        ingresos_dolar = Decimal('0.00')
        egresos_dolar = Decimal('0.00')
        total_dolar = Decimal('0.00')

        total_general = Decimal('0.00')

        tipo_cambio = Decimal('0.00')

        # RECORRER CAJAS
        for caja in cajas:

            if caja.apertura_actual:

                apertura = caja.apertura_actual

                tipo_cambio = (
                    apertura.tipocambio.valor
                )

                saldo_inicial_cordoba += (
                    caja.saldo_inicial
                )

                ingresos_cordoba += (
                    caja.ingresos_cordoba
                )

                egresos_cordoba += (
                    caja.egresos_cordoba
                )

                ingresos_dolar += (
                    caja.ingresos_dolar
                )

                egresos_dolar += (
                    caja.egresos_dolar
                )

                total_cordoba += (
                    caja.total_cordoba
                )

                total_dolar += (
                    caja.total_dolar
                )

                total_general += (
                    caja.total_general
                )

        contexto.update({

            'total_cajas':
                total_cajas,

            'saldo_inicial_cordoba':
                saldo_inicial_cordoba,

            'ingresos_cordoba':
                ingresos_cordoba,

            'egresos_cordoba':
                egresos_cordoba,

            'total_cordoba':
                total_cordoba,

            'ingresos_dolar':
                ingresos_dolar,

            'egresos_dolar':
                egresos_dolar,

            'total_dolar':
                total_dolar,

            'total_general':
                total_general,

            'tipo_cambio':
                tipo_cambio,
        })

        return render(
            request,
            'empleados/caja_gerente.html',
            contexto
        )

    # =====================================================
    # CAJERO
    # =====================================================

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=[
            'Abierta',
            'En arqueo'
        ]
    ).select_related(
        'tipocambio'
    ).order_by(
        '-apertura_id'
    ).first()

    movimientos = []

    if apertura:

        movimientos = MovimientoCaja.objects.filter(
            apertura=apertura
        ).order_by(
            '-fecha'
        )

        totales = calcular_totales_apertura(
            apertura
        )

        contexto.update({

            'apertura': apertura,

            'movimientos': movimientos,

            'saldo_inicial':
                apertura.saldo_inicial,

            **totales
        })

    return render(request,'empleados/caja.html',contexto)
    
# ============================================
# ABRIR CAJA
# ============================================

def abrir_caja(request):

    empleado = request.user.empleado

    if empleado.rol.nombre != "Cajero":

        messages.error(request, "No tienes permisos.")

        return redirect('caja')

    if request.method == "POST":

        caja_id = request.POST.get('caja_id')

        caja = Caja.objects.filter(
            caja_id=caja_id,
            sucursal=empleado.sucursal
        ).first()

        if not caja:
            request.session['abrir_modal_apertura'] = True
            messages.error(request, "La caja no existe.")
            return redirect('caja')

        caja_abierta = AperturaCaja.objects.filter(
            caja=caja,
            estado__nombre__in=['Abierta', 'En arqueo']
        ).exists()

        if caja_abierta:
            request.session['abrir_modal_apertura'] = True
            messages.error(request,"La caja ya está abierta.")
            return redirect('caja')

        tipocambio = HistorialTipoCambio.objects.order_by('-fecha').first()

        if not tipocambio:

            request.session['abrir_modal_apertura'] = True

            messages.error(
                request,
                "No existe tipo de cambio registrado."
            )

            return redirect('caja')

        # VALIDAR EFECTIVO
        denominaciones = Denominacion.objects.filter(
            moneda='CORDOBA'
        ).order_by('-valor')

        total_temporal = Decimal('0')

        for denominacion in denominaciones:
            cantidad = int(request.POST.get(f'denominacion_{denominacion.denominacion_id}', 0))

            if cantidad > 0:

                total_temporal += (Decimal(cantidad) * denominacion.valor)

        if total_temporal <= 0:
            request.session['abrir_modal_apertura'] = True
            messages.error(request,"Debe ingresar efectivo inicial.")
            return redirect('caja')

        estado = Estado.objects.get(nombre='Abierta')

        apertura = AperturaCaja.objects.create(
            caja=caja,
            empleado=empleado,
            estado=estado,
            tipocambio=tipocambio,
            saldo_inicial=Decimal('0')
        )

        # GUARDAR DETALLE APERTURA
        total_cordoba = Decimal('0')

        for denominacion in denominaciones:

            cantidad = int(request.POST.get(f'denominacion_{denominacion.denominacion_id}',0))

            if cantidad > 0:

                subtotal = (
                    Decimal(cantidad) *
                    denominacion.valor
                )

                DetalleAperturaCaja.objects.create(
                    apertura=apertura,
                    denominacion=denominacion,
                    cantidad=cantidad,
                    subtotal=subtotal
                )

                total_cordoba += subtotal

        apertura.saldo_inicial = total_cordoba
        apertura.save()
        messages.success(request,"Caja abierta correctamente.")

    return redirect('caja')

# ============================================
# CREAR MOVIMIENTO
# ============================================

def crear_movimiento(request):
    empleado = request.user.empleado

    if empleado.rol.nombre != "Cajero":
        request.session['abrir_modal_movimiento'] = True
        messages.error(request,"No tienes permisos.")
        return redirect('caja')

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre__in=['Abierta', 'En arqueo']
    ).select_related(
        'tipocambio'
    ).order_by('-apertura_id').first()

    if not apertura:
        request.session['abrir_modal_movimiento'] = True
        messages.error(request,"No hay caja abierta.")
        return redirect('caja')

    tipo = request.POST.get('tipo')
    moneda = request.POST.get('moneda')
    descripcion = request.POST.get('descripcion')
    monto = Decimal(request.POST.get('monto') or 0)

    if monto <= 0:
        request.session['abrir_modal_movimiento'] = True
        messages.error(request,"Ingrese un monto válido.")
        return redirect('caja')

    totales = calcular_totales_apertura(apertura)

    disponible = (totales['total_cordoba'] if moneda == 'CORDOBA' else totales['total_dolar'])

    if tipo == 'EGRESO' and monto > disponible:
        request.session['abrir_modal_movimiento'] = True
        messages.error(request,f"No hay suficiente saldo en {moneda}.")
        return redirect('caja')
    

    MovimientoCaja.objects.create(
        apertura=apertura,
        tipo=tipo,
        moneda=moneda,
        descripcion=descripcion,
        monto=monto
    )

    messages.success(
        request,
        "Movimiento registrado correctamente."
    )

    return redirect('caja')


# ============================================
# INICIAR ARQUEO
# ============================================
"""
@require_POST
def iniciar_arqueo(request):

    empleado = request.user.empleado

    apertura = AperturaCaja.objects.filter(
        empleado=empleado,
        estado__nombre='Abierta'
    ).first()

    if not apertura:
        return JsonResponse({
            'status': 'error'
        })

    estado = Estado.objects.get(
        nombre='En arqueo'
    )

    apertura.estado = estado
    apertura.save()

    return JsonResponse({
        'status': 'ok'
    })

"""

# =========================================================
# CREAR ARQUEO
# =========================================================

from decimal import Decimal
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

def crear_arqueo(request):
    empleado = request.user.empleado

    if request.method == "POST":
        apertura = AperturaCaja.objects.filter(
            apertura_id=request.POST.get('apertura_id')
        ).select_related(
            'tipocambio'
        ).first()

        # VALIDAR APERTURA
        if not apertura:
            request.session['abrir_modal_arqueo'] = True
            messages.error(request, "La apertura no existe.")
            return redirect('caja')

        # TOTALES DEL SISTEMA
        totales = calcular_totales_apertura(apertura)
        monto_sistema = Decimal(totales['total_general'])
        total_cordoba_sistema = Decimal(totales['total_cordoba'])
        total_dolar_sistema = Decimal(totales['total_dolar'])

        # RECORRER DENOMINACIONES
        total_cordoba = Decimal('0')
        total_dolar = Decimal('0')

        detalles_guardar = []

        denominaciones = Denominacion.objects.all()

        for denominacion in denominaciones:
            cantidad = int(request.POST.get(f'denominacion_{denominacion.denominacion_id}', 0))

            # SOLO SI HAY CANTIDAD
            if cantidad > 0:

                subtotal = (
                    Decimal(cantidad)
                    * denominacion.valor
                )

                detalles_guardar.append({
                    'denominacion': denominacion,
                    'cantidad': cantidad,
                    'subtotal': subtotal
                })

                # SUMAR SEGUN MONEDA
                if denominacion.moneda == 'CORDOBA':
                    total_cordoba += subtotal
                else:
                    total_dolar += subtotal

        # VALIDAR CORDOBAS
        if (total_cordoba_sistema <= 0 and total_cordoba > 0):
            request.session['abrir_modal_arqueo'] = True
            messages.error(request, "El sistema no tiene saldo en córdobas.")
            return redirect('caja')

        # VALIDAR DOLARES
        if (total_dolar_sistema <= 0 and total_dolar > 0):
            request.session['abrir_modal_arqueo'] = True
            messages.error(request,"El sistema no tiene saldo en dólares.")
            return redirect('caja')

        # SI HAY USD DEBE COINCIDIR
        if (total_dolar_sistema > 0 and total_dolar != total_dolar_sistema):
            request.session['abrir_modal_arqueo'] = True
            messages.error(request,"El efectivo en dólares no coincide con el sistema.")
            return redirect('caja')

        # CONVERTIR DOLARES
        conversion_dolar = (total_dolar * apertura.tipocambio.valor)
        
        # TOTAL FISICO
        total_fisico = (total_cordoba + conversion_dolar)

        # OBSERVACION AUTOMATICA
        observacion = request.POST.get('observacion')
        
        # VALIDAR JUSTIFICACION
        justificacion = request.POST.get('justificacion')

        if not justificacion:
            request.session['abrir_modal_arqueo'] = True
            messages.error(request,"Debe ingresar una justificación.")
            return redirect('caja')

        # CREAR ARQUEO
        arqueo = ArqueoCaja.objects.create(

            apertura=apertura,
            empleado=empleado,
            tipocambio=apertura.tipocambio,

            tipo=request.POST.get('tipo'),

            monto_sistema=monto_sistema,
            monto_fisico=total_fisico,

            observacion=observacion,
            justificacion=justificacion

        )

        # CREAR DETALLES
        for detalle in detalles_guardar:

            DetalleArqueo.objects.create(
                arqueo=arqueo,
                denominacion=detalle['denominacion'],
                cantidad=detalle['cantidad'],
                subtotal=detalle['subtotal']

            )

        # SI ES CIERRE FINAL
        if arqueo.tipo == 'FINAL':
            estado_cerrada = Estado.objects.get(nombre='Cerrada')
            apertura.estado = estado_cerrada
            apertura.fecha_cierre = timezone.now()
            apertura.saldo_final = total_fisico
            apertura.save()

        # MENSAJE
        messages.success(request,"Arqueo realizado correctamente.")
        return redirect('caja')

    return redirect('caja')


from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus.flowables import HRFlowable
from decimal import Decimal



# =====================================================
# REPORTE PDF ARQUEO
# =====================================================

from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from decimal import Decimal, ROUND_HALF_UP

def fmt(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def reporte_arqueo_pdf(request, arqueo_id):

    arqueo = get_object_or_404(
        ArqueoCaja.objects.select_related(
            'apertura',
            'empleado',
            'apertura__caja',
            'apertura__caja__sucursal',
            'tipocambio'
        ),
        pk=arqueo_id
    )

    apertura = arqueo.apertura
    caja = apertura.caja
    sucursal = caja.sucursal
    empleado = arqueo.empleado
    tasa = Decimal(arqueo.tipocambio.valor)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="arqueo_{arqueo.arqueo_id}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    elementos = []

    # =====================================================
    # TITULO
    # =====================================================
    titulo = "ARQUEO DE CIERRE" if arqueo.tipo == "FINAL" else "ARQUEO PARCIAL"
    elementos.append(Paragraph(f"<b>{titulo}</b>", styles['Title']))
    elementos.append(Spacer(1, 10))

    # =====================================================
    # INFO
    # =====================================================
    info = [
        ["Sucursal:", sucursal.nombre],
        ["Caja:", caja.nombre],
        ["Empleado:", f"{empleado.user.first_name} {empleado.user.last_name}"],
        ["Fecha:", arqueo.fecha.strftime("%d/%m/%Y")],
        ["Hora:", arqueo.fecha.strftime("%I:%M %p")],
        ["Tipo Cambio:", f"C${tasa}"]
    ]

    tabla_info = Table(info, colWidths=[150, 300])
    tabla_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#eeeeee')),
    ]))

    elementos.append(tabla_info)
    elementos.append(Spacer(1, 15))

    # =====================================================
    # DENOMINACIONES
    # =====================================================
    apertura_detalles = DetalleAperturaCaja.objects.filter(apertura=apertura)
    arqueo_detalles = DetalleArqueo.objects.filter(arqueo=arqueo)

    apertura_dict = {d.denominacion_id: d for d in apertura_detalles}
    arqueo_dict = {d.denominacion_id: d for d in arqueo_detalles}

    denominaciones = Denominacion.objects.all().order_by('moneda', 'valor')

    data = [[
        'Denominación',
        'Inicio',
        'Cierre',
        'Dif.'
    ]]

    total_cordoba_inicio = Decimal('0')
    total_cordoba_cierre = Decimal('0')

    total_dolar_inicio = Decimal('0')
    total_dolar_cierre = Decimal('0')

    for denom in denominaciones:

        ap = apertura_dict.get(denom.denominacion_id)
        ar = arqueo_dict.get(denom.denominacion_id)

        inicio = ap.cantidad if ap else 0
        cierre = ar.cantidad if ar else 0

        inicio_sub = ap.subtotal if ap else Decimal('0')
        cierre_sub = ar.subtotal if ar else Decimal('0')

        diferencia = cierre - inicio

        data.append([
            f"{denom.moneda} {denom.valor}",
            str(inicio),
            str(cierre),
            str(diferencia)
        ])

        # =====================================================
        # SUMAS POR MONEDA
        # =====================================================
        if denom.moneda == 'CORDOBA':
            total_cordoba_inicio += inicio_sub
            total_cordoba_cierre += cierre_sub

        elif denom.moneda == 'DOLAR':
            total_dolar_inicio += inicio_sub
            total_dolar_cierre += cierre_sub

    tabla = Table(data, colWidths=[200, 100, 100, 80])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#d63384')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))

    elementos.append(Paragraph("<b>CONTROL DE EFECTIVO</b>", styles['Heading2']))
    elementos.append(tabla)
    elementos.append(Spacer(1, 10))

    # =====================================================
    # RESUMEN POR MONEDA
    # =====================================================

    dolar_en_cordoba_inicio = total_dolar_inicio * tasa
    dolar_en_cordoba_cierre = total_dolar_cierre * tasa

    total_general_inicio = total_cordoba_inicio + dolar_en_cordoba_inicio
    total_general_cierre = total_cordoba_cierre + dolar_en_cordoba_cierre

    resumen = [
        ['Concepto', 'Inicio', 'Cierre'],
        
        ['DÓLAR (USD)',
        f"${fmt(total_dolar_inicio)}",
        f"${fmt(total_dolar_cierre)}"],
        
        ['DÓLAR (en C$)',
         f"C${fmt(dolar_en_cordoba_inicio)}",
         f"C${fmt(dolar_en_cordoba_cierre)}"],

        ['CÓRDOBA',
         f"C${fmt(total_cordoba_inicio)}",
         f"C${fmt(total_cordoba_cierre)}"],

        ['TOTAL GENERAL (C$)',
         f"C${fmt(total_general_inicio)}",
         f"C${fmt(total_general_cierre)}"],
    ]

    tabla_resumen = Table(resumen, colWidths=[200, 150, 150])
    tabla_resumen.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ]))

    elementos.append(Paragraph("<b>RESUMEN GENERAL</b>", styles['Heading2']))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 15))
    
    # =====================================================
    # MOVIMIENTOS (MEDIOS ELECTRÓNICOS)
    # =====================================================

    movimientos = MovimientoCaja.objects.filter(apertura=apertura)

    total_tarjeta_c = Decimal('0')
    total_tarjeta_d = Decimal('0')

    total_trans_c = Decimal('0')
    total_trans_d = Decimal('0')

    for m in movimientos:

        desc = (m.descripcion or '').upper()


        if 'TARJETA C$' in desc:
            total_tarjeta_c += m.monto

        elif 'TARJETA USD' in desc:
            total_tarjeta_d += m.monto


        elif 'TRANSFERENCIA C$' in desc:
            total_trans_c += m.monto

        elif 'TRANSFERENCIA USD' in desc:
            total_trans_d += m.monto

    elementos.append(Paragraph("<b>MÉTODOS ELECTRÓNICOS</b>", styles['Heading2']))

    tabla_pago = Table([
        ['Método', 'C$', 'USD'],

        ['Tarjetas',
        f"C${total_tarjeta_c}",
        f"${total_tarjeta_d}"],

        ['Transferencias',
        f"C${total_trans_c}",
        f"${total_trans_d}"],
    ])

    tabla_pago.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elementos.append(tabla_pago)
    elementos.append(Spacer(1, 15))

    # =====================================================
    # VALIDACIÓN
    # =====================================================

    diferencia = arqueo.monto_fisico - arqueo.monto_sistema
    sobrante = diferencia if diferencia > 0 else Decimal('0')
    faltante = abs(diferencia) if diferencia < 0 else Decimal('0')

    validacion = [
        ['Concepto', 'Monto'],
        ['Sistema', f"C${arqueo.monto_sistema}"],
        ['Físico', f"C${arqueo.monto_fisico}"],
        ['Sobrante', f"C${sobrante}"],
        ['Faltante', f"C${faltante}"],
    ]

    tabla_validacion = Table(validacion, colWidths=[250, 150])
    tabla_validacion.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elementos.append(Paragraph("<b>VALIDACIÓN DEL ARQUEO</b>", styles['Heading2']))
    elementos.append(tabla_validacion)
    elementos.append(Spacer(1, 20))

    # =====================================================
    # FIRMAS
    # =====================================================
    firmas = Table([[
        "Cajero Responsable\n\n__________________",
        "Supervisor / Gerente\n\n__________________"
    ]], colWidths=[250, 250])

    firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elementos.append(firmas)

    doc.build(elementos)
    return response






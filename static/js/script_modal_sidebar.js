/* === LÓGICA DEL SIDEBAR (GLOBAL) === */
// Usamos comprobación de existencia para evitar errores si el elemento no existe en alguna página
const menuToggle = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');

if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
    });
}

if (overlay) {
    overlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
    });
}
/* === LÓGICA DE MODALES GENÉRICA === */
// Esta función sirve para cualquier modal del sistema
function abrirModal(idModal) {
    const modal = document.getElementById(idModal);
    if (modal) {
        modal.style.display = 'flex';
    } else {
        console.error("No se encontró la modal con ID: " + idModal);
    }
}

function cerrarModal(idModal) {
    const modal = document.getElementById(idModal);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Cerrar al hacer clic fuera de la caja blanca (opcional pero recomendado)
window.onclick = function(event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.style.display = 'none';
    }
}

// --- LÓGICA DE CAJA LUCY'S SYSTEM ---

document.addEventListener("DOMContentLoaded", function() {
    // 1. Verificar si la caja ya está abierta al cargar
    const cajaAbierta = localStorage.getItem('cajaAbierta');
    
    if (cajaAbierta !== 'true') {
        abrirModal('modalApertura');
    } else {
        // Si ya está abierta, cargamos el monto en la tarjeta de "Efectivo Inicial"
        const montoGuardado = localStorage.getItem('montoInicial');
        document.querySelector('.cash-card.income h3').innerText = `$${montoGuardado}`;
    }
});

// Función para Abrir Caja
function confirmarApertura(event) {
    event.preventDefault();
    const monto = document.getElementById('monto-apertura').value;

    if (monto && monto > 0) {
        localStorage.setItem('cajaAbierta', 'true');
        localStorage.setItem('montoInicial', monto);
        
        // Actualizar la interfaz sin recargar
        document.querySelector('.cash-card.income h3').innerText = `$${parseFloat(monto).toFixed(2)}`;
        cerrarModal('modalApertura');
        alert("¡Caja abierta exitosamente!");
    }
}

// Función para Cerrar Caja y mostrar Ticket
function confirmarCierre() {
    // 1. Cerramos el modal de entrada de datos
    cerrarModal('modalCierre');
    
    // 2. Mostramos el ticket final
    abrirModal('modalTicket');
    
    // 3. Limpiamos el estado para el día siguiente
    localStorage.removeItem('cajaAbierta');
    localStorage.removeItem('montoInicial');
}

// Función para WhatsApp
function enviarWhatsApp() {
    const mensaje = encodeURIComponent("*CIERRE DE CAJA - LUCY'S BOUTIQUE*\nTotal en Caja: $455.00\nEstado: Balanceado");
    window.open(`https://wa.me/50581703596?text=${mensaje}`, '_blank');
}

// Función para Imprimir
function imprimirTicket() {
    window.print();
}

// --- FUNCIONES BASE (Asegúrate de tenerlas) ---
function abrirModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function cerrarModal(id) {
    document.getElementById(id).style.display = 'none';
}

document.addEventListener('input', function (e) {
    if (e.target.classList.contains('denom-input')) {
        calcularTotalApertura();
    }
});

function calcularTotalApertura() {
    let total = 0;
    const inputs = document.querySelectorAll('.denom-input');

    inputs.forEach(input => {
        const denominacion = parseFloat(input.getAttribute('data-value'));
        const cantidad = parseInt(input.value) || 0;
        total += denominacion * cantidad;
    });

    // Actualizar visualmente el modal
    document.getElementById('labelTotalApertura').innerText = `$${total.toFixed(2)}`;
    // Asignar al valor oculto para el SQL
    document.getElementById('inputSaldoInicial').value = total.toFixed(2);
}

/* ==========================================
   FUNCIONES DE GESTIÓN DE INVENTARIO
   ========================================== */

/**
 * 1. EDITAR PRODUCTO
 * Prepara el modal de registro para edición
 */
function editarProducto(sku) {
    // Cambiamos el comportamiento visual del modal de producto
    const modal = document.getElementById('modalProducto');
    if(modal) {
        // Cambiar título e icono
        modal.querySelector('h3').innerHTML = `<i class="fas fa-edit"></i> Editar Producto: ${sku}`;
        
        // Cambiar texto del botón primordial
        const btnSubmit = modal.querySelector('button[type="submit"]');
        if(btnSubmit) btnSubmit.innerText = "Actualizar Cambios";

        // Simulación: Aquí llenarías los inputs con los datos de la fila
        // document.getElementById('sku_input').value = sku;
        
        abrirModal('modalProducto');
    }
}

/**
 * 2. VER DETALLES COMPLETOS
 * Abre un modal de solo lectura con la ficha técnica
 */
function verProductoDetalle(sku) {
    const modal = document.getElementById('modalVerProducto');
    if(modal) {
        // Actualizamos el SKU en la vista para que se vea real
        const skuDisplay = document.getElementById('v_sku');
        if(skuDisplay) skuDisplay.innerText = sku;
        
        abrirModal('modalVerProducto');
    }
}

/**
 * 3. VER KARDEX (HISTORIAL)
 * Abre el modal con la tabla de movimientos
 */
function verKardex(sku) {
    const modal = document.getElementById('modalKardex');
    if(modal) {
        // Podrías cambiar el título para saber de qué producto es el historial
        modal.querySelector('h3').innerHTML = `<i class="fas fa-history"></i> Kardex: ${sku}`;
        
        abrirModal('modalKardex');
    }
}

/**
 * 4. CAMBIAR ESTADO (TOGGLE)
 * Simula el cambio de activo/inactivo con una confirmación
 */
function toggleEstadoProducto(sku) {
    // Usamos el confirm nativo para darle funcionalidad visual
    const respuesta = confirm(`¿Desea cambiar el estado actual del producto ${sku}? \n\n(Si está Activo pasará a Inactivo y viceversa)`);
    
    if (respuesta) {
        alert(`Estado del producto ${sku} actualizado con éxito.`);
        // Aquí no recargamos ni enviamos nada, solo cerramos el flujo
    }
}

/**
 * EXTRA: LIMPIAR AL AGREGAR NUEVO
 * Asegura que si abrimos para "Nuevo", no diga "Editar"
 */
function abrirModalNuevoProducto() {
    const modal = document.getElementById('modalProducto');
    if(modal) {
        modal.querySelector('h3').innerHTML = `<i class="fas fa-plus-circle"></i> Nuevo Producto`;
        modal.querySelector('button[type="submit"]').innerText = "Registrar en DB";
        
        // Limpiar formulario si existe
        const form = modal.querySelector('form');
        if(form) form.reset();
        
        abrirModal('modalProducto');
    }
}

/**
 * Muestra la vista previa de la imagen seleccionada
 */
function previsualizarImagen(event) {
    const reader = new FileReader();
    const previewContainer = document.getElementById('imagePreview');
    const imgElement = previewContainer.querySelector('img');
    const iconElement = previewContainer.querySelector('i');

    reader.onload = function() {
        if (reader.readyState === 2) {
            imgElement.src = reader.result;
            imgElement.style.display = 'block';
            iconElement.style.display = 'none';
            previewContainer.style.border = 'none';
        }
    }

    if (event.target.files[0]) {
        reader.readAsDataURL(event.target.files[0]);
    }
}

/**
 * Resetear la vista previa al cerrar o limpiar el modal
 */
function resetPreview() {
    const previewContainer = document.getElementById('imagePreview');
    const imgElement = previewContainer.querySelector('img');
    const iconElement = previewContainer.querySelector('i');

    imgElement.src = "";
    imgElement.style.display = 'none';
    iconElement.style.display = 'block';
}

// Llama a resetPreview() dentro de tu función abrirModalNuevoProducto()

function establecerFechaActual() {
    const ahora = new Date();
    
    // Formatear Fecha: DD/MM/YYYY
    const dia = String(ahora.getDate()).padStart(2, '0');
    const mes = String(ahora.getMonth() + 1).padStart(2, '0');
    const anio = ahora.getFullYear();
    
    // Formatear Hora: HH:MM AM/PM
    let horas = ahora.getHours();
    const minutos = String(ahora.getMinutes()).padStart(2, '0');
    const ampm = horas >= 12 ? 'PM' : 'AM';
    
    horas = horas % 12;
    horas = horas ? horas : 12; // La hora 0 será 12
    const strTime = `${horas}:${minutos} ${ampm}`;

    const fechaCompleta = `${dia}/${mes}/${anio} ${strTime}`;
    
    // Asignar al input
    const inputFecha = document.getElementById('fechaVentaActual');
    if (inputFecha) {
        inputFecha.value = fechaCompleta;
    }
}

function abrirModalVenta() {
    // 1. Llamamos a la función de la fecha antes de mostrar el modal
    establecerFechaActual();
    
    // 2. Abrimos el modal (usando tu función existente)
    abrirModal('modalVenta');
}

/**
 * 1. Simular agregar producto a la tabla del modal
 */
function agregarProductoALista() {
    const lista = document.querySelector('#modalVenta tbody');
    const inputBusqueda = document.getElementById('input_buscar_prod');
    
    // Si el input está vacío, no agregamos nada (solo visual)
    if(inputBusqueda.value === "") {
        alert("Por favor, busque un producto primero.");
        return;
    }

    // Quitamos el mensaje de "No hay productos" si existe
    if (lista.innerHTML.includes("No hay productos agregados")) {
        lista.innerHTML = "";
    }

    // Creamos la nueva fila con el formato de tu tabla Detalles_Ventas
    const nuevaFila = `
        <tr>
            <td>${inputBusqueda.value}</td>
            <td>$15.00</td>
            <td><input type="number" value="3" min="3" class="input-table" style="width:60px"></td>
            <td><input type="number" value="0.00" class="input-table" style="width:60px"></td>
            <td class="font-bold">$45.00</td>
            <td><button type="button" class="btn-delete-row" onclick="this.closest('tr').remove()"><i class="fas fa-times"></i></button></td>
        </tr>
    `;
    
    lista.insertAdjacentHTML('beforeend', nuevaFila);
    inputBusqueda.value = ""; // Limpiar buscador
    actualizarTotalVenta(45.00); // Función ficticia para sumar
}

/**
 * 2. PROCESAR VENTA Y ABRIR TICKET
 * Esta es la función que debe ir en el onsubmit del form o el onclick del botón Finalizar
 */
function procesarVentaFinal() {
    // 1. Validar que haya productos (Opcional)
    const tieneProductos = document.querySelectorAll('#modalVenta tbody tr').length;
    
    if (tieneProductos === 0) {
        alert("El carrito está vacío.");
        return;
    }

    // 2. Cerrar el modal de venta
    cerrarModal('modalVenta');
    
    // 3. Abrir el modal del ticket (Asegúrate que el ID sea modalTicket)
    setTimeout(() => {
        abrirModal('modalTicket');
    }, 300); // Pequeño delay para que la animación se vea fluida
}



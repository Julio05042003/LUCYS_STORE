// ==========================================
// ESTADO GLOBAL DEL CARRITO
// ==========================================
let carrito = JSON.parse(localStorage.getItem('lucy_cart')) || [];

// Al cargar el documento, renderizar el estado inicial
document.addEventListener('DOMContentLoaded', () => {
    actualizarInterfazCarrito();
});

// ==========================================
// FUNCIONES DE APERTURA / CIERRE INTERFAZ
// ==========================================
function abrirCarrito() {
    const sidebar = document.getElementById('cart-sidebar');
    if (sidebar) sidebar.classList.add('active');
}

function cerrarCarrito() {
    const sidebar = document.getElementById('cart-sidebar');
    if (sidebar) sidebar.classList.remove('active');
}

function abrirCheckout() {
    if (carrito.length === 0) {
        alert("Tu bolsa de compras está vacía.");
        return;
    }
    const modal = document.getElementById('modalCheckout');
    if (modal) {
        modal.classList.add('show');
        actualizarResumenCheckout();
    }
}

function cerrarCheckout() {
    const modal = document.getElementById('modalCheckout');
    if (modal) modal.classList.remove('show');
}

function cerrarModal(idModal) {
    const modal = document.getElementById(idModal);
    if (modal) modal.classList.remove('active', 'show');
}

// ==========================================
// OPERACIONES DEL CARRITO (AÑADIR, QUITAR, LIMPIAR)
// ==========================================
// =========================================================================
// FUNCIÓN UNIFICADA DEL CARRITO (VENTA AL POR MAYOR - DE 3 EN 3)
// =========================================================================

function agregarAlCarrito(id, nombre, precio) {
    const precioNum = parseFloat(precio);
    
    // Definimos que el bloque de compra obligatorio es siempre de 3 unidades
    const unidadesPorPaquete = 3; 
    
    // Buscamos si el producto ya está en el carrito
    const productoExistente = carrito.find(item => item.id === id);

    if (productoExistente) {
        // Si ya existe, le sumamos 3 unidades más
        productoExistente.cantidad += unidadesPorPaquete;
    } else {
        // Si es nuevo, lo registramos directamente con 3 unidades
        carrito.push({
            id: id,
            nombre: nombre,
            precio: precioNum,
            cantidad: unidadesPorPaquete
        });
    }

    // Lanzamos la notificación visual elegante en la pantalla
    mostrarNotificacion(`¡Paquete de 3 unidades de "${nombre}" añadido con éxito!`);

    // Efecto visual de rebote (bump) en el icono del carrito
    const cartIcon = document.querySelector('.cart-icon');
    if (cartIcon) {
        cartIcon.classList.add('bump');
        setTimeout(() => cartIcon.classList.remove('bump'), 300);
    }

    // Guarda los cambios en LocalStorage y actualiza los contadores de la web
    guardarYActualizar();
}

/**
 * Panel de Notificaciones Flotantes Integrado (Toast)
 */
function mostrarNotificacion(mensaje, tipo = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return; 

    const toast = document.createElement('div');
    toast.className = `custom-toast ${tipo}`;
    
    let icono = '<i class="fas fa-check-circle"></i>';
    if (tipo === 'error') {
        icono = '<i class="fas fa-exclamation-circle"></i>';
    }

    toast.innerHTML = `${icono} <span>${mensaje}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 50);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, 3500);
}

function cambiarCantidad(id, cambio) {
    const producto = carrito.find(item => item.id === id);
    if (!producto) return;

    producto.cantidad += cambio;

    if (producto.cantidad <= 0) {
        eliminarDelCarrito(id);
    } else {
        guardarYActualizar();
    }
}

function eliminarDelCarrito(id) {
    carrito = carrito.filter(item => item.id !== id);
    guardarYActualizar();
}

/**
 * FUNCIÓN CRÍTICA: Vacía por completo el almacenamiento 
 * y actualiza los contenedores de la UI.
 */
function limpiarCarritoCompleto() {
    if (confirm("¿Estás segura de que deseas vaciar tu bolsa de compras?")) {
        carrito = [];
        guardarYActualizar();
        cerrarCarrito();
    }
}

function guardarYActualizar() {
    localStorage.setItem('lucy_cart', JSON.stringify(carrito));
    actualizarInterfazCarrito();
}

// ==========================================
// RENDERIZADO DINÁMICO DE LA INTERFAZ
// ==========================================
function actualizarInterfazCarrito() {
    const contenedorItems = document.getElementById('items-carrito');
    const contadorBadge = document.getElementById('contador-carrito');
    const subtotalLabel = document.getElementById('subtotal-carrito');

    if (!contenedorItems) return;

    // Calcular totales
    let totalProductos = 0;
    let subtotalDinero = 0;

    if (carrito.length === 0) {
        contenedorItems.innerHTML = `<p class="empty-msg">No hay productos aún en tu bolsa.</p>`;
    } else {
        contenedorItems.innerHTML = '';
        carrito.forEach(item => {
            totalProductos += item.cantidad;
            subtotalDinero += (item.precio * item.cantidad);

            const itemHTML = `
                <div class="cart-item">
                    <div class="item-info">
                        <div class="item-name">${item.nombre}</div>
                        <div class="item-controls">
                            <button class="qty-btn" onclick="cambiarCantidad('${item.id}', -1)">-</button>
                            <span class="item-qty">${item.cantidad}</span>
                            <button class="qty-btn" onclick="cambiarCantidad('${item.id}', 1)">+</button>
                        </div>
                        <div class="item-price">C$ ${(item.precio * item.cantidad).toFixed(2)}</div>
                    </div>
                    <button class="btn-remove" onclick="eliminarDelCarrito('${item.id}')">
                        <i class="far fa-trash-alt"></i>
                    </button>
                </div>
            `;
            contenedorItems.insertAdjacentHTML('beforeend', itemHTML);
        });
    }

    // Actualizar elementos fijos de la Navbar y Sidebar
    if (contadorBadge) contadorBadge.innerText = totalProductos;
    if (subtotalLabel) subtotalLabel.innerText = `C$ ${subtotalDinero.toFixed(2)}`;
}



// ==========================================
// CONTROL DE CHECKOUT (SIN COSTO DE ENVÍO)
// ==========================================
function actualizarResumenCheckout() {
    const totalFinal = document.getElementById('total-final');
    if (!totalFinal) return;

    // El total es simplemente la suma de los productos
    let total = carrito.reduce((acc, item) => acc + (item.precio * item.cantidad), 0);
    totalFinal.innerText = `C$ ${total.toFixed(2)}`;
}

// ==========================================
// INTEGRACIÓN CON WHATSAPP MODIFICADA
// ==========================================
function confirmarPedido() {
    const nombreCliente = document.getElementById('cliente-nombre').value.trim();
    
    if (!nombreCliente) {
        alert("Por favor, introduce tu nombre para procesar el pedido.");
        return;
    }

    let total = carrito.reduce((acc, item) => acc + (item.precio * item.cantidad), 0);

    // Construcción del mensaje sin datos de envío
    let mensaje = `🌸 *LUCY'S STORE - NUEVO PEDIDO* 🌸\n\n`;
    mensaje += `👤 *Cliente:* ${nombreCliente}\n`;
    mensaje += `------------------------------------------\n`;
    
    carrito.forEach(item => {
        mensaje += `🛍️ *${item.nombre}*\n`;
        mensaje += `   _Cant:_ ${item.cantidad} x C$ ${item.precio.toFixed(2)} = *C$ ${(item.precio * item.cantidad).toFixed(2)}*\n`;
    });
    
    mensaje += `------------------------------------------\n`;
    mensaje += `💰 *TOTAL A PAGAR:* C$ ${total.toFixed(2)}\n\n`;
    mensaje += `¡Hola! Me gustaría confirmar la disponibilidad de estos artículos. ✨`;

    // Número oficial de soporte de tu tienda
    const telefonoTienda = "50581703596"; 
    const urlWhatsapp = `https://api.whatsapp.com/send?phone=${telefonoTienda}&text=${encodeURIComponent(mensaje)}`;
    
    window.open(urlWhatsapp, '_blank');
}

// ==========================================
// DETALLE DE PRODUCTO INTERNO (QUICK VIEW)
// ==========================================
function verProducto(id, nombre, descripcion, precio, sku, marca, categoria, stock, urlImagen) {
    document.getElementById('v_nombre').innerText = nombre;
    document.getElementById('v_desc').innerText = descripcion || "Sin descripción disponible.";
    document.getElementById('v_precio_venta').innerText = `C$ ${parseFloat(precio).toFixed(2)}`;
    document.getElementById('v_sku').innerText = sku || "N/A";
    document.getElementById('v_marca').innerText = marca || "Genérico";
    document.getElementById('v_cat').innerText = categoria;
    document.getElementById('v_stock').innerText = stock;
    document.getElementById('view_img').src = urlImagen;

    // Configurar el botón de agregar interno del modal de forma dinámica
    const btnAgregar = document.getElementById('btnAgregarModal');
    if (btnAgregar) {
        btnAgregar.onclick = () => {
            agregarAlCarrito(id, nombre, precio);
            cerrarModal('modalVerProducto');
        };
    }

    const modal = document.getElementById('modalVerProducto');
    if (modal) modal.classList.add('active');
}

let carrito = [];
let productoModal = null;

// ======================================
// INICIAR
// ======================================
document.addEventListener('DOMContentLoaded', () => {

    cargarCarritoStorage();
    actualizarVistaCarrito();

});

// ======================================
// AGREGAR AL CARRITO
// ======================================
function agregarAlCarrito(id, nombre, precio) {

    precio = parseFloat(precio);

    const existe = carrito.find(p => p.id == id);

    if (existe) {

        existe.cantidad++;

    } else {

        carrito.push({
            id: id,
            nombre: nombre,
            precio: precio,
            cantidad: 1
        });

    }

    guardarCarritoStorage();
    actualizarVistaCarrito();
    abrirCarrito();
}

// ======================================
// ACTUALIZAR VISTA
// ======================================
function actualizarVistaCarrito() {

    const contenedor =
        document.getElementById('items-carrito');

    const contador =
        document.getElementById('contador-carrito');

    const subtotalText =
        document.getElementById('subtotal-carrito');

    let subtotal = 0;
    let totalItems = 0;

    if (carrito.length === 0) {

        contenedor.innerHTML = `
            <p class="empty-msg">
                No hay productos aún.
            </p>
        `;

    } else {

        contenedor.innerHTML = carrito.map((item, index) => {

            subtotal += item.precio * item.cantidad;
            totalItems += item.cantidad;

            return `
                <div class="cart-item">

                    <div class="item-info">

                        <p class="item-name">
                            ${item.nombre}
                        </p>

                        <div class="item-controls">

                            <button class="qty-btn"
                                onclick="cambiarCantidad(${index}, -1)">
                                -
                            </button>

                            <span class="item-qty">
                                ${item.cantidad}
                            </span>

                            <button class="qty-btn"
                                onclick="cambiarCantidad(${index}, 1)">
                                +
                            </button>

                        </div>

                        <p class="item-price">
                            C$ ${(item.precio * item.cantidad).toFixed(2)}
                        </p>

                    </div>

                    <button class="btn-remove"
                        onclick="eliminarDelCarrito(${index})">

                        <i class="fas fa-trash"></i>

                    </button>

                </div>
            `;

        }).join('');

    }

    contador.innerText = totalItems;
    subtotalText.innerText = `C$ ${subtotal.toFixed(2)}`;

    actualizarResumenCheckout();
}

// ======================================
// CANTIDAD
// ======================================
function cambiarCantidad(index, cambio) {

    carrito[index].cantidad += cambio;

    if (carrito[index].cantidad <= 0) {

        carrito.splice(index, 1);

    }

    guardarCarritoStorage();
    actualizarVistaCarrito();
}

// ======================================
// ELIMINAR
// ======================================
function eliminarDelCarrito(index) {

    carrito.splice(index, 1);

    guardarCarritoStorage();
    actualizarVistaCarrito();
}

// ======================================
// STORAGE
// ======================================
function guardarCarritoStorage() {

    localStorage.setItem(
        'carritoLucys',
        JSON.stringify(carrito)
    );
}

function cargarCarritoStorage() {

    const data = localStorage.getItem('carritoLucys');

    if (data) {

        carrito = JSON.parse(data);

    }
}

// ======================================
// CARRITO
// ======================================
function abrirCarrito() {

    document.getElementById('cart-sidebar')
        .classList.add('active');
}

function cerrarCarrito() {

    document.getElementById('cart-sidebar')
        .classList.remove('active');
}

// ======================================
// CHECKOUT
// ======================================
function abrirCheckout() {

    if (carrito.length === 0) {

        alert('Tu carrito está vacío');
        return;
    }

    cerrarCarrito();

    document.getElementById('modalCheckout')
        .classList.add('show');

    actualizarResumenCheckout();
}

function cerrarCheckout() {

    document.getElementById('modalCheckout')
        .classList.remove('show');
}

// ======================================
// RESUMEN
// ======================================
function actualizarResumenCheckout() {

    const subtotal = carrito.reduce((acc, item) => {
        return acc + (item.precio * item.cantidad);
    }, 0);

    const envio = parseFloat(
        document.getElementById('ubicacion')?.value || 0
    );

    const total = subtotal + envio;

    document.getElementById('resumen-subtotal')
        .innerText = `C$ ${subtotal.toFixed(2)}`;

    document.getElementById('envio-costo')
        .innerText = `C$ ${envio.toFixed(2)}`;

    document.getElementById('total-final')
        .innerText = `C$ ${total.toFixed(2)}`;
}

// ======================================
// TARIFA
// ======================================
function actualizarTarifa() {

    actualizarResumenCheckout();
}

// ======================================
// VER PRODUCTO
// ======================================
function verProducto(
    id,
    nombre,
    descripcion,
    precio,
    codigo,
    marca,
    categoria,
    stock,
    imagen
) {

    productoModal = {
        id,
        nombre,
        precio
    };

    document.getElementById('v_nombre').innerText = nombre;
    document.getElementById('v_desc').innerText = descripcion;
    document.getElementById('v_precio_venta').innerText = `C$ ${precio}`;
    document.getElementById('v_sku').innerText = codigo;
    document.getElementById('v_marca').innerText = marca;
    document.getElementById('v_cat').innerText = categoria;
    document.getElementById('v_stock').innerText = stock;

    document.getElementById('view_img').src =
        imagen || '/static/img/no-image.png';

    document.getElementById('modalVerProducto')
        .classList.add('show');
}

// ======================================
// AGREGAR MODAL
// ======================================
document.getElementById('btnAgregarModal')
?.addEventListener('click', () => {

    if (!productoModal) return;

    agregarAlCarrito(
        productoModal.id,
        productoModal.nombre,
        productoModal.precio
    );

    cerrarModal('modalVerProducto');
});

// ======================================
// MODALES
// ======================================
function cerrarModal(id) {

    document.getElementById(id)
        .classList.remove('show');
}

// ======================================
// CONFIRMAR PEDIDO
// ======================================
function confirmarPedido() {

    const nombre =
        document.getElementById('cliente-nombre').value;

    if (!nombre) {

        alert('Ingrese su nombre');
        return;
    }

    fetch(URL_CREAR_PEDIDO, {

        method: 'POST',

        headers: {
            'Content-Type': 'application/json'
        },

        body: JSON.stringify({
            nombre: nombre,
            carrito: carrito
        })

    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            alert('Pedido creado correctamente');

            carrito = [];

            guardarCarritoStorage();
            actualizarVistaCarrito();
            cerrarCheckout();

        } else {

            alert('Error al crear pedido');

        }

    })
    .catch(error => {

        console.error(error);

        alert('Error del servidor');

    });
}

// ======================================
// ESC
// ======================================
document.addEventListener('keydown', e => {

    if (e.key === 'Escape') {

        cerrarCarrito();
        cerrarCheckout();
        cerrarModal('modalVerProducto');

    }

});
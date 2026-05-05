// =============================
// CONFIG
// =============================
const URL_CREAR_PEDIDO = "/api/crear-pedido/";

// =============================
// ENVIAR PEDIDO (BD + WHATSAPP)
// =============================
async function enviarPedido() {
    const nombre = document.getElementById('cliente-nombre').value.trim();
    const ubicacion = document.getElementById('ubicacion').value;

    if (!nombre) {
        alert("Ingrese su nombre");
        return;
    }

    if (ubicacion === "0") {
        alert("Seleccione ubicación");
        return;
    }

    if (carrito.length === 0) {
        alert("Carrito vacío");
        return;
    }

    try {
        const response = await fetch(URL_CREAR_PEDIDO, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({
                nombre: nombre,
                ubicacion: ubicacion,
                carrito: carrito
            })
        });

        const data = await response.json();

        if (data.success) {

            // ✅ MENSAJE WHATSAPP
            let mensaje = `🛍️ *Pedido Lucy's Boutique*\n\n`;
            mensaje += `👤 Cliente: ${nombre}\n\n`;

            carrito.forEach(item => {
                mensaje += `• ${item.nombre} x${item.cantidad} = C$${(item.precio * item.cantidad).toFixed(2)}\n`;
            });

            mensaje += `\n💰 Total: C$${data.total}\n`;

            const url = `https://wa.me/50581703596?text=${encodeURIComponent(mensaje)}`;
            window.open(url, "_blank");

            alert("Pedido guardado correctamente");

            carrito = [];
            actualizarVistaCarrito();
            guardarCarritoStorage();

        } else {
            alert("Error al guardar pedido");
        }

    } catch (error) {
        console.error(error);
        alert("Error en el servidor");
    }
}

// =============================
// CSRF TOKEN
// =============================
function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken'))
        ?.split('=')[1];
}
/* === LÓGICA DEL SIDEBAR (GLOBAL) === */
// Usamos comprobación de existencia para evitar errores si el elemento no existe en alguna página
document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.btn-editar').forEach(btn => {
        btn.addEventListener('click', function () {

            editarProducto(
                this.dataset.id,
                this.dataset.codigo,
                this.dataset.nombre,
                this.dataset.descripcion,
                this.dataset.categoria,
                this.dataset.marca,
                this.dataset.imagen
            );

        });
    });

});

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
window.onclick = function (event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.style.display = 'none';
    }
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


/* ==========================================
   FUNCIONES DE GESTIÓN DE INVENTARIO
   ========================================== */

/**
 * 1. EDITAR PRODUCTO
 * Prepara el modal de registro para edición
 */
// 🟢 ABRIR MODAL EDITAR
function editarProducto(id, codigo, nombre, descripcion, categoria, marca, imagenUrl) {
console.log("Entró a editarProducto");

    abrirModal('modalProductoEditar');
    abrirModal('modalProductoEditar');

    const modal = document.getElementById('modalProductoEditar');
    const form = document.getElementById('formEditarProducto');

    form.action = `/producto/editar/${id}/`;

    document.getElementById('producto_id_edit').value = id;
    document.getElementById('codigo_edit').value = codigo;
    document.getElementById('nombre_edit').value = nombre;
    document.getElementById('categoria_edit').value = categoria;
    document.getElementById('marca_edit').value = marca;

    // Descripción
    document.getElementById('descripcion_edit').value =
        descripcion || '';

    // Imagen
    const preview = modal.querySelector('#imagePreviewEdit img');
    const icon = modal.querySelector('#imagePreviewEdit i');

    if (imagenUrl && imagenUrl.trim() !== '') {
        preview.src = imagenUrl;
        preview.style.display = 'block';
        icon.style.display = 'none';
    } else {
        preview.src = '/static/img/no-image.png';
        preview.style.display = 'block';
        icon.style.display = 'none';
    }
}


// 🟢 PREVISUALIZAR IMAGEN
function previsualizarImagenEdit(event) {

    const file = event.target.files[0];
    const preview = document.querySelector('#imagePreviewEdit img');
    const icon = document.querySelector('#imagePreviewEdit i');

    if (file) {
        const reader = new FileReader();

        reader.onload = function (e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
            icon.style.display = 'none';
        }

        reader.readAsDataURL(file);
    }
}
/* 2. VER DETALLES COMPLETOS
* Abre un modal de solo lectura con la ficha técnica
*/
function verProductoDetalle(id) {

    fetch(`/producto/json/${id}/`)
        .then(response => {

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.json();
        })

        .then(data => {

            console.log("DATA:", data);

            // =========================================
            // ELEMENTOS
            // =========================================

            const sku = document.getElementById('v_sku');
            const nombre = document.getElementById('v_nombre');
            const cat = document.getElementById('v_cat');
            const marca = document.getElementById('v_marca');
            const desc = document.getElementById('v_desc');

            const stock = document.querySelector('.badge-stock');

            const img = document.getElementById('view_img');

            const costo = document.getElementById('v_precio_costo');
            const venta = document.getElementById('v_precio_venta');

            const tabla = document.getElementById('tabla_bodegas');

            // =========================================
            // VALIDAR ELEMENTOS
            // =========================================

            if (!sku || !nombre || !cat || !marca ||
                !desc || !stock || !img ||
                !costo || !venta || !tabla) {

                console.error("Faltan elementos HTML");

                return;
            }

            // =========================================
            // DATOS BÁSICOS
            // =========================================

            sku.textContent = data.codigo || "";
            nombre.textContent = data.nombre || "";
            cat.textContent = data.categoria || "";
            marca.textContent = data.marca || "";
            desc.textContent = data.descripcion || "Sin descripción";

            stock.textContent =
                `${data.stock || 0} Unidades`;

            // =========================================
            // IMAGEN
            // =========================================

            img.src = data.imagen && data.imagen !== ""
                ? data.imagen
                : "/static/img/no-image.png";

            // =========================================
            // PRECIOS
            // =========================================

            venta.textContent =
                `C$${parseFloat(data.precio_venta || 0).toFixed(2)}`;

            const contenedorCosto = costo.closest('.info-item');

            if (data.rol === "Vendedor") {

                if (contenedorCosto) {
                    contenedorCosto.style.display = "none";
                }

            } else {

                if (contenedorCosto) {
                    contenedorCosto.style.display = "block";
                }

                costo.textContent =
                    `C$${parseFloat(data.precio_costo || 0).toFixed(2)}`;
            }

            // =========================================
            // TABLA INVENTARIO
            // =========================================

            tabla.innerHTML = "";

            if (data.inventarios.length > 0) {

                let filas = "";

                data.inventarios.forEach(i => {

                    filas += `
            <tr>
                <td>${i.bodega}</td>
                <td>${i.sucursal}</td>
                <td>${i.stock}</td>
            </tr>
        `;
                });

                tabla.innerHTML = filas;

            } else {

                tabla.innerHTML = `
        <tr>
            <td colspan="3">
                Sin stock disponible
            </td>
        </tr>
    `;
            }

            // =========================================
            // ABRIR MODAL
            // =========================================

            abrirModal('modalVerProducto');

        })

        .catch(error => {

            console.error("ERROR:", error);

            alert("Error cargando producto");

        });
}

/**
 * 3. VER KARDEX (HISTORIAL)
 * Abre el modal con la tabla de movimientos
 */
function verKardex(sku) {
    const modal = document.getElementById('modalKardex');
    if (modal) {
        // Podrías cambiar el título para saber de qué producto es el historial
        modal.querySelector('h3').innerHTML = `<i class="fas fa-history"></i> Kardex: ${sku}`;

        abrirModal('modalKardex');
    }
}

/**
 * 4. CAMBIAR ESTADO (TOGGLE)
 * Simula el cambio de activo/inactivo con una confirmación
 */
function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken'))
        ?.split('=')[1];
}

function toggleEstadoProducto(id) {

    const respuesta = confirm(`¿Desea cambiar el estado del producto?`);

    if (!respuesta) return;

    fetch(`/producto/estado/${id}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                location.reload(); // 🔥 refresca tabla
            } else {
                alert(data.error || "Error al cambiar estado");
            }
        })
        .catch(() => alert("Error en la petición"));
}
/**
 * EXTRA: LIMPIAR AL AGREGAR NUEVO
 * Asegura que si abrimos para "Nuevo", no diga "Editar"
 */
function abrirModalNuevoProducto() {
    const modal = document.getElementById('modalProducto');
    if (modal) {
        modal.querySelector('h3').innerHTML = `<i class="fas fa-plus-circle"></i> Nuevo Producto`;
        modal.querySelector('button[type="submit"]').innerText = "Registrar en DB";

        // Limpiar formulario si existe
        const form = modal.querySelector('form');
        if (form) form.reset();

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

    reader.onload = function () {
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



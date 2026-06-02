// =====================================================
// VARIABLES GLOBALES
// =====================================================

let productos = [];

let totalPedido = 0;


// =====================================================
// CSRF
// =====================================================

function getCSRFToken() {

    return document.querySelector(
        '[name=csrfmiddlewaretoken]'
    )?.value
    ||
    document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}


// =====================================================
// MODAL CREAR
// =====================================================

function openModal(){

    document
        .getElementById('pedidoModal')
        .classList.add('show');
}

function closeModal(){

    document
        .getElementById('pedidoModal')
        .classList.remove('show');
}


// =====================================================
// MODAL DETALLE
// =====================================================

function closeDetalleModal(){

    document
        .getElementById('detallePedidoModal')
        .classList.remove('show');
}


// =====================================================
// SELECT2 CLIENTES
// =====================================================

$('#clienteSelect').select2({

    dropdownParent: $('#pedidoModal'),

    ajax: {

        url: buscarClientesURL,

        dataType: 'json',

        delay: 300,

        data: function(params){

            return {

                term: params.term
            };
        },

        processResults: function(data){

            return {

                results: data
            };
        }
    }
});


// =====================================================
// CARGAR DIRECCIONES CLIENTE
// =====================================================

$('#clienteSelect').on(
    'select2:select',
    function(e){

        const clienteId = e.params.data.id;

        fetch(

            cargarDireccionesURL.replace(
                '0',
                clienteId
            )

        )
        .then(r => r.json())
        .then(data => {

            let html = `
                <option value="">
                    Seleccionar dirección
                </option>
            `;

            data.forEach(dir => {

                html += `

                <option value="${dir.id}">
                    ${dir.text}
                </option>

                `;
            });

            document.getElementById(
                'direccionEnvio'
            ).innerHTML = html;
        });
    }
);


// =====================================================
// SELECT2 PRODUCTOS
// =====================================================

$('#productoSearch').select2({

    dropdownParent: $('#pedidoModal'),

    ajax: {

        url: buscarProductosURL,

        dataType: 'json',

        delay: 300,

        data: function(params){

            return {

                term: params.term
            };
        },

        processResults: function(data){

            return {

                results: data
            };
        }
    }
});


// =====================================================
// AGREGAR PRODUCTO
// =====================================================

$('#productoSearch').on(
    'select2:select',
    function(e){

        const p = e.params.data;

        const existe = productos.find(

            item =>
            item.producto == p.id
        );

        if(existe){

            Swal.fire(
                'Aviso',
                'El producto ya fue agregado',
                'warning'
            );

            return;
        }

        productos.push({

            producto: p.id,
            nombre: p.nombre,
            precio: parseFloat(
                p.precio
            ),
            stock: parseInt(
                p.stock
            ),
            cantidad: 1
        });

        renderProductos();
    }
);


// =====================================================
// RENDER PRODUCTOS
// =====================================================

function renderProductos(){

    let html = '';

    totalPedido = 0;

    productos.forEach(

        (p,index) => {

            let subtotal =
                p.precio *
                p.cantidad;

            totalPedido += subtotal;

            html += `

            <div class="product-card">

                <div class="product-top">

                    <div class="product-name">

                        ${p.nombre}

                    </div>

                    <button
                        class="btn-action btn-cancel"
                        onclick="removeProducto(${index})"
                    >

                        Eliminar

                    </button>

                </div>

                <div class="product-info">

                    <div>

                        <label>

                            Precio

                        </label>

                        <input
                            class="form-control"
                            disabled
                            value="C$ ${p.precio}"
                        >

                    </div>

                    <div>

                        <label>

                            Stock

                        </label>

                        <input
                            class="form-control"
                            disabled
                            value="${p.stock}"
                        >

                    </div>

                    <div>

                        <label>

                            Cantidad

                        </label>

                        <input
                            type="number"
                            min="1"
                            class="form-control"
                            value="${p.cantidad}"
                            onchange="
                                changeCantidad(
                                    ${index},
                                    this.value
                                )
                            "
                        >

                    </div>

                    <div>

                        <label>

                            Subtotal

                        </label>

                        <input
                            disabled
                            class="form-control"
                            value="C$ ${subtotal.toFixed(2)}"
                        >

                    </div>

                </div>

            </div>

            `;
        }
    );

    document.getElementById(
        'productsContainer'
    ).innerHTML = html;

    document.getElementById(
        'totalPedido'
    ).innerHTML =

        `Total: C$ ${totalPedido.toFixed(2)}`;
}


// =====================================================
// CAMBIAR CANTIDAD
// =====================================================

function changeCantidad(index,value){

    value = parseInt(value);

    if(value <= 0){

        Swal.fire(
            'Error',
            'Cantidad inválida',
            'error'
        );

        return;
    }

    if(value > productos[index].stock){

        Swal.fire(
            'Error',
            'Stock insuficiente',
            'error'
        );

        return;
    }

    productos[index].cantidad = value;

    renderProductos();
}


// =====================================================
// ELIMINAR PRODUCTO
// =====================================================

function removeProducto(index){

    productos.splice(index,1);

    renderProductos();
}


// =====================================================
// DELIVERY
// =====================================================

document
.getElementById('tipoEntrega')
?.addEventListener(

    'change',

    function(){

        const texto =
        this.options[
            this.selectedIndex
        ]
        .text
        .toLowerCase();

        if(texto === 'delivery'){

            $('#deliverySection').slideDown();

            $('#direccionSection').slideDown();

        }else{

            $('#deliverySection').slideUp();

            $('#direccionSection').slideUp();
        }
    }
);


// =====================================================
// CREAR PEDIDO
// =====================================================

function guardarPedido(){

    if(productos.length === 0){

        Swal.fire(
            'Error',
            'Debe agregar productos',
            'error'
        );

        return;
    }

    fetch(

        crearPedidoURL,

        {

            method:'POST',

            headers:{

                'Content-Type':
                'application/json',

                'X-CSRFToken':
                getCSRFToken()
            },

            body: JSON.stringify({

                cliente:
                $('#clienteSelect').val(),

                tipo_entrega:
                document
                .getElementById(
                    'tipoEntrega'
                ).value,

                metodo_envio:
                document
                .getElementById(
                    'metodoEnvio'
                ).value,

                direccion_envio:
                document
                .getElementById(
                    'direccionEnvio'
                ).value,

                productos:
                productos
            })
        }

    )

    .then(r=>r.json())

    .then(data=>{

        if(data.success){

            Swal.fire(

                'Correcto',

                data.message,

                'success'

            ).then(()=>{

                location.reload();
            });

        }else{

            Swal.fire(

                'Error',

                data.message,

                'error'
            );
        }
    });
}


// =====================================================
// CAMBIAR ESTADO
// =====================================================

function cambiarEstado(id,estado){

    Swal.fire({

        title:'¿Confirmar?',

        text:
        `Cambiar a ${estado}`,

        icon:'question',

        showCancelButton:true,

        confirmButtonText:'Sí'
    })

    .then(result=>{

        if(!result.isConfirmed)
            return;

        fetch(

            cambiarEstadoURL.replace(
                '0',
                id
            ),

            {

                method:'POST',

                headers:{

                    'Content-Type':
                    'application/json',

                    'X-CSRFToken':
                    getCSRFToken()
                },

                body: JSON.stringify({

                    estado: estado
                })
            }
        )

        .then(r=>r.json())

        .then(data=>{

            if(data.success){

                Swal.fire(

                    'Correcto',

                    data.message,

                    'success'

                ).then(()=>{

                    location.reload();
                });

            }else{

                Swal.fire(

                    'Error',

                    data.message,

                    'error'
                );
            }
        });
    });
}


// =====================================================
// VER DETALLE
// =====================================================

function verPedido(id){

    fetch(

        detallePedidoURL.replace(
            '0',
            id
        )
    )

    .then(r=>r.json())

    .then(data=>{

        document
        .getElementById(
            'detalleCodigo'
        )
        .innerText =

        `Pedido #${data.id}`;

        document
        .getElementById(
            'detalleCliente'
        )
        .innerText =
        data.cliente;

        document
        .getElementById(
            'detalleVendedor'
        )
        .innerText =
        data.vendedor;

        document
        .getElementById(
            'detalleSucursal'
        )
        .innerText =
        data.sucursal;

        document
        .getElementById(
            'detalleEstado'
        )
        .innerText =
        data.estado;

        document
        .getElementById(
            'detalleEntrega'
        )
        .innerText =
        data.entrega;

        document
        .getElementById(
            'detalleFecha'
        )
        .innerText =
        data.fecha;

        let html = '';

        data.productos.forEach(p=>{

            html += `

            <tr>

                <td>
                    ${p.producto}
                </td>

                <td>
                    ${p.cantidad}
                </td>

                <td>
                    C$ ${p.precio}
                </td>

                <td>
                    C$ ${p.subtotal}
                </td>

            </tr>

            `;
        });

        document
        .getElementById(
            'detalleProductos'
        )
        .innerHTML = html;

        document
        .getElementById(
            'detalleTotal'
        )
        .innerHTML =

        `Total: C$ ${data.total}`;

        document
        .getElementById(
            'detallePedidoModal'
        )
        .classList.add('show');
    });
}


// =====================================================
// BUSCADOR
// =====================================================

document
.getElementById('searchInput')
?.addEventListener(

    'keyup',

    function(){

        const value =
        this.value.toLowerCase();

        document
        .querySelectorAll(
            '.order-card'
        )
        .forEach(card=>{

            card.style.display =

            card.innerText
            .toLowerCase()
            .includes(value)

            ? 'block'
            : 'none';
        });
    }
);


// =====================================================
// FILTRO ESTADO
// =====================================================

document
.getElementById('filterEstado')
?.addEventListener(

    'change',

    function(){

        const value =
        this.value;

        document
        .querySelectorAll(
            '.order-card'
        )
        .forEach(card=>{

            const estado =
            card.dataset.estado;

            card.style.display =

            value === ''
            ||
            estado === value

            ? 'block'
            : 'none';
        });
    }
);
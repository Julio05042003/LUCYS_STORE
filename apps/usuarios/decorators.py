from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages

from apps.usuarios.models import Empleado


def rol_requerido(roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('login')

            try:

                empleado = Empleado.objects.select_related(
                    'rol',
                    'sucursal',
                    'estado'
                ).get(user=request.user)

            except Empleado.DoesNotExist:

                messages.error(
                    request,
                    "No tienes acceso"
                )

                return redirect('login')

            if empleado.estado.nombre.lower() != 'activo':

                messages.error(
                    request,
                    "Empleado inactivo"
                )

                return redirect('login')

            roles_validos = [
                r.lower() for r in roles
            ]

            if empleado.rol.nombre.lower() not in roles_validos:

                messages.error(
                    request,
                    "No tienes permisos"
                )

                return redirect('index_empleados')

            #  guardar empleado en request
            request.empleado = empleado

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator



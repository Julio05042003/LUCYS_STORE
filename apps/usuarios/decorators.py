from django.shortcuts import redirect
from django.contrib import messages
from apps.usuarios.models import Empleado

def rol_requerido(roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('login')

            try:
                empleado = Empleado.objects.get(user=request.user)
            except Empleado.DoesNotExist:
                return redirect('login')

            if empleado.rol.nombre not in roles:
                messages.error(request, "No tienes permiso")
                return redirect('index_empleados')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
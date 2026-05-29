from apps.usuarios.models import Empleado

def empleado_actual(request):

    if request.user.is_authenticated:

        try:

            empleado = Empleado.objects.select_related(
                'rol',
                'sucursal',
                'user'
            ).get(user=request.user)

            return {

                'empleado': empleado,
                'rol_usuario': empleado.rol.nombre.lower(),

            }

        except Empleado.DoesNotExist:

            return {}

    return {}
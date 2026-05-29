from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

from apps.usuarios.tokens import token_generator


def enviar_verificacion_email(request, user):

    token = token_generator.make_token(user)

    ruta = reverse(
        'activar_cuenta',
        args=[user.id, token]
    )

    url = f"http://127.0.0.1:8000{ruta}"

    print(url)

    asunto = 'Verifica tu cuenta'

    mensaje = f'''
Hola {user.first_name}

Gracias por registrarte.

Haz clic en el siguiente enlace para activar tu cuenta:

{url}
'''

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )
import re
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from apps.usuarios.tokens import token_generator

def validar_email(email):

    return re.match(
        r"[^@]+@[^@]+\.[^@]+",
        email
    )


import re

def validar_password(password):

    # mínimo 8 caracteres
    if len(password) < 8:
        return False

    # mínimo una mayúscula
    if not re.search(r'[A-Z]', password):
        return False

    # mínimo una minúscula
    if not re.search(r'[a-z]', password):
        return False

    # mínimo un número
    if not re.search(r'\d', password):
        return False

    # mínimo un carácter especial
    if not re.search(r'[@$!%*?&._#-]', password):
        return False

    return True


def validar_telefono(numero):

    numero = numero.replace('-', '')

    return (
        numero.isdigit()
        and len(numero) == 8
    )
    


def enviar_verificacion_email(request, user):

    token = token_generator.make_token(user)

    url = request.build_absolute_uri(
        reverse(
            'activar_cuenta',
            args=[user.id, token]
        )
    )

    asunto = 'Verifica tu cuenta'

    mensaje = f'''
Hola {user.first_name}

Haz clic para verificar tu cuenta:

{url}
'''

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )
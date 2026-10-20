from django.conf import settings
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from Taberna.dev_login import (
    DEV_LOGIN_SALT,
    DEV_USERNAME,
    obter_ou_criar_usuario_dev,
)


class Command(BaseCommand):
    help = 'Cria/atualiza o usuário local de desenvolvimento e imprime um link de login.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'O login de desenvolvimento só está disponível com DJANGO_DEBUG=True.'
            )

        usuario = obter_ou_criar_usuario_dev()
        token = signing.dumps(usuario.pk, salt=DEV_LOGIN_SALT)
        caminho = reverse('dev_login', args=[token])
        base_url = getattr(
            settings,
            'DEV_LOGIN_BASE_URL',
            'http://127.0.0.1:8000',
        ).rstrip('/')
        validade_minutos = max(1, settings.DEV_LOGIN_MAX_AGE // 60)

        self.stdout.write(self.style.SUCCESS('Login de desenvolvimento pronto.'))
        self.stdout.write(f'Usuário: {DEV_USERNAME} (superusuário, perfil Professor)')
        self.stdout.write(f'Link: {base_url}{caminho}')
        self.stdout.write(f'Validade: {validade_minutos} minuto(s).')
        self.stdout.write('')
        self.stdout.write(
            'Abra o link no navegador. Em outra porta, ajuste '
            'DJANGO_DEV_LOGIN_BASE_URL ou use apenas o caminho acima.'
        )

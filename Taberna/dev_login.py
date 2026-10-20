from django.contrib.auth.models import User
from django.db import transaction

from .models import Pessoa, Professor

DEV_LOGIN_SALT = 'taberna-dev-login'
DEV_USERNAME = 'dev_taberna'
DEV_NOME = 'Desenvolvedor (teste)'
DEV_CELULAR = '00000000000'


def _cpf_disponivel():
    for indice in range(100):
        cpf = f'000.000.000-{indice:02d}'
        if not Pessoa.objects.filter(cpf=cpf).exists():
            return cpf
    raise RuntimeError('Não foi possível gerar um CPF de teste livre.')


def _email_disponivel():
    for indice in range(100):
        email = 'dev@taberna.local' if indice == 0 else f'dev{indice}@taberna.local'
        if not Pessoa.objects.filter(email=email).exists():
            return email
    raise RuntimeError('Não foi possível gerar um e-mail de teste livre.')


@transaction.atomic
def obter_ou_criar_usuario_dev():
    """
    Cria (ou reutiliza) o usuário local de desenvolvimento.

    Ele é superusuário e também tem um perfil Professor, para que o checkout
    permita testar todas as formas de pagamento, inclusive fiado.
    """
    usuario = User.objects.filter(username=DEV_USERNAME).first()

    if usuario is None:
        usuario = User(
            username=DEV_USERNAME,
            email='dev@taberna.local',
            first_name='Desenvolvedor',
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        usuario.set_unusable_password()
        usuario.save()
    else:
        campos = []
        if not usuario.is_staff:
            usuario.is_staff = True
            campos.append('is_staff')
        if not usuario.is_superuser:
            usuario.is_superuser = True
            campos.append('is_superuser')
        if not usuario.is_active:
            usuario.is_active = True
            campos.append('is_active')
        if campos:
            usuario.save(update_fields=campos)

    pessoa = Pessoa.objects.filter(usuario=usuario).first()

    if pessoa is None:
        Professor.objects.create(
            usuario=usuario,
            nome=DEV_NOME,
            cpf=_cpf_disponivel(),
            celular=DEV_CELULAR,
            email=_email_disponivel(),
            area='Desenvolvimento',
            detalhes_regime='Teste',
        )
        return usuario

    try:
        pessoa.professor
    except Professor.DoesNotExist:
        Professor.objects.create(
            pessoa_ptr=pessoa,
            area='Desenvolvimento',
            detalhes_regime='Teste',
        )

    return usuario

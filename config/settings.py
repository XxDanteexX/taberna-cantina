"""
Django settings for the Taberna project.

As configurações sensíveis são lidas de variáveis de ambiente. Para
desenvolvimento local, copie .env.example e exporte as variáveis no shell
(o projeto não carrega .env automaticamente).
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nome, padrao=False):
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {'1', 'true', 'sim', 'yes', 'on'}


# SECURITY WARNING: em produção, defina DJANGO_DEBUG=False e DJANGO_SECRET_KEY.
DEBUG = env_bool('DJANGO_DEBUG', True)

SECRET_KEY = (os.environ.get('DJANGO_SECRET_KEY') or '').strip()
if not SECRET_KEY:
    if DEBUG:
        # Chave exclusiva para desenvolvimento local. Nunca use em produção.
        SECRET_KEY = 'django-insecure-dev-only-nao-use-em-producao'
    else:
        raise ImproperlyConfigured(
            'Defina a variável de ambiente DJANGO_SECRET_KEY para executar em produção.'
        )

if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
else:
    ALLOWED_HOSTS = [
        host.strip()
        for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
        if host.strip()
    ]
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'Defina DJANGO_ALLOWED_HOSTS com os domínios permitidos em produção.'
        )

CSRF_TRUSTED_ORIGINS = [
    origem.strip()
    for origem in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origem.strip()
]


# Application definition

INSTALLED_APPS = [
    'Taberna',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Authentication

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'cardapio'
LOGOUT_REDIRECT_URL = 'login'


# Login local de desenvolvimento
# A rota /dev-login/<token>/ só funciona com DEBUG=True. O token é assinado com
# SECRET_KEY e gerado pelo comando "python manage.py dev_login".

try:
    DEV_LOGIN_MAX_AGE = int(os.environ.get('DJANGO_DEV_LOGIN_MAX_AGE', '3600'))
except ValueError:
    DEV_LOGIN_MAX_AGE = 3600

DEV_LOGIN_BASE_URL = os.environ.get(
    'DJANGO_DEV_LOGIN_BASE_URL',
    'http://127.0.0.1:8000',
).rstrip('/')


# Security
# Em produção (DEBUG=False), HTTPS e cookies seguros ficam habilitados por padrão.

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

if env_bool('DJANGO_BEHIND_PROXY', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Caches
# O throttle de login usa o cache padrão (LocMemCache). Em vários processos,
# troque por Redis/Memcached para que o limite seja compartilhado.

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'taberna-login-throttle',
    }
}

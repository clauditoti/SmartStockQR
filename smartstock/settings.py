"""
Django settings for smartstock project.
ARCHIVO DE CONFIGURACIÓN UNIFICADO (LOCAL + RAILWAY)
"""

from pathlib import Path
import os
import pymysql
import dj_database_url

# Configuración necesaria para usar PyMySQL como conector de MySQL
pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. SEGURIDAD Y ENTORNO
# ==============================================================================

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-guulpy(xuuzh^*=ts=o4=k(0=3%wlii^q3qvywnj4#3j^q)97_')

# En Railway, DEBUG será False automáticamente si configuras la variable de entorno
DEBUG = True

# Permitimos el host de Railway y localhost
ALLOWED_HOSTS = ['*']

# Configuración CSRF para Ngrok y Railway
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
    'https://*.up.railway.app', # Soporte para el dominio de Railway
]

# ==============================================================================
# 2. APLICACIONES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bodega', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Para servir archivos estáticos en Railway
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smartstock.urls'

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

WSGI_APPLICATION = 'smartstock.wsgi.application'

# ==============================================================================
# 3. BASE DE DATOS (LOCAL + PRODUCTION)
# ==============================================================================

# Si estamos en Railway, usará MYSQL_URL. Si no, usará tu configuración local de 3307.
if os.getenv('MYSQL_URL'):
    DATABASES = {
        'default': dj_database_url.config(default=os.getenv('MYSQL_URL'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'smartstock_db',
            'USER': 'root',
            'PASSWORD': 'bdsmartstock123',
            'HOST': 'localhost',
            'PORT': '3307',
        }
    }

# ==============================================================================
# 4. VALIDACIÓN DE PASSWORD
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================================================================
# 5. INTERNACIONALIZACIÓN
# ==============================================================================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# 6. ARCHIVOS ESTÁTICOS Y MULTIMEDIA
# ==============================================================================

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuración CRÍTICA para que funcionen las fotos en Railway
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Asegura que la carpeta media exista para evitar errores al guardar
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

# ==============================================================================
# 7. REDIRECCIONES
# ==============================================================================

LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración específica para WhiteNoise y archivos estáticos en producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
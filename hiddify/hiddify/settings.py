from pathlib import Path
import os
from datetime import timedelta
from celery.schedules import timedelta


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------- Local settings -----------------
DEBUG = True if os.environ.get('DEBUG') == 'True' else False
IS_DEVELOPMENT = True if os.environ.get('IS_DEVELOPMENT') == 'True' else False
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key').strip()
ALLOWED_HOSTS = [os.environ.get('ALLOWED_HOSTS', '*').strip()]

IS_HTTPS_USED = True if os.environ.get('IS_HTTPS_USED') == 'True' else False
if IS_HTTPS_USED:
    CSRF_COOKIE_SECURE = True if os.environ.get('CSRF_COOKIE_SECURE') == 'True' else False
    SESSION_COOKIE_SECURE = True if os.environ.get('SESSION_COOKIE_SECURE') == 'True' else False
    CSRF_TRUSTED_ORIGINS = [
        os.environ.get('CSRF_TRUSTED_ORIGINS'),
        ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'rest_framework_simplejwt',
    
    'accounts',
    'client_actions',
    'plans',
    
    'api',
    'telegram_bot',
    
    'task_manager',
    'adminlogs',
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

ROOT_URLCONF = 'hiddify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hiddify.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME'  : os.environ.get('DATABASE_NAME', 'postgres'),
        'USER'  : os.environ.get('DATABASE_USER', 'postgres'),
        'PASSWORD'  : os.environ.get('DATABASE_PASSWORD', 'postgres'),
        'HOST'  : os.environ.get('DATABASE_HOST', 'database'),
        'PORT'  : os.environ.get('DATABASE_PORT', '5432'),
    }
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = 'media/'
# You can still have STATICFILES_DIRS for development purposes
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'accounts/static'),] # Add the accounts app static files directory to the list

STATIC_ROOT = BASE_DIR / 'static' 
MEDIA_ROOT = BASE_DIR / 'media' 



# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Tell Django to use the CustomUser model for authentication
AUTH_USER_MODEL = 'accounts.CustomUser'


# ----------------- REST Framework settings -----------------
REST_FRAMEWORK = {
    
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    
}

# ----------------- Celery settings -----------------

# Celery settings
CELERY_BEAT_SCHEDULE = {
    'fetch-data-every-1-minutes': {
        'task': 'task_manager.tasks.fetch_data_from_api',
        'schedule': timedelta(seconds=60),  # Executes every 1 minutes
    },
    
    'check-subscription-expiry-every-1-minutes': {
        'task': 'task_manager.tasks.check_subscription_expiry',
        'schedule': timedelta(seconds=60),  # Executes every 2 hours   
    },
    
    'disable-not-paid-users-every-day' : {
        'task': 'task_manager.tasks.disable_not_paid_users',
        'schedule': timedelta(seconds=43200),  # Executes every day
    },
    
    'send-telegram-notification-to-unpayed-users': {
        'task': 'task_manager.tasks.send_payment_reminder_messsage',
        'schedule': timedelta(seconds=43200),  # Executes every day
    },
    'send-telegram-warning-to-expired-users': {
        'task': 'task_manager.tasks.send_warning_message',
        'schedule': timedelta(seconds=21600),  # Executes 12 hours
    },
}
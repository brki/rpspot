import environ
root = environ.Path(__file__) - 3

# Sets env defaults and casting
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
env.read_env(root('.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': env.db(), # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
}

public_root = root.path('public/')
MEDIA_ROOT = public_root('media')
MEDIA_URL = 'media/'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_ROOT = public_root('static')
STATIC_URL = '/static/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY') # Raises ImproperlyConfigured exception if SECRET_KEY not in os.environ

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rphistory',
    'trackmap',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'rpspot.urls'

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

WSGI_APPLICATION = 'rpspot.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

INTERNAL_IPS=tuple(env.list('INTERNAL_IPS', None, ['127.0.0.1']))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': root('fs_cache', 'cache')
    }
}

SPOTIFY_CACHE = 'default'
SPOTIFY_CLIENT_ID = env.str('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = env.str('SPOTIFY_CLIENT_SECRET')

#TODO: adjust for different environments:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        # 'default': {
        #     'level':'DEBUG',
        #     'class':'logging.handlers.RotatingFileHandler',
        #     'filename': 'logs/mylog.log',
        #     'maxBytes': 1024*1024*5, # 5 MB
        #     'backupCount': 5,
        #     'formatter':'standard',
        # },
        # 'request_handler': {
        #     'level':'DEBUG',
        #     'class':'logging.handlers.RotatingFileHandler',
        #     'filename': 'logs/django_request.log',
        #     'maxBytes': 1024*1024*5, # 5 MB
        #     'backupCount': 5,
        #     'formatter':'standard',
        # },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        # '': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG' if DEBUG else 'ERROR',
        #     'propagate': True
        # },
        'trackmap.trackmap': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'ERROR',
            'propagate': True
        },
        # 'django.request': {
        #     'handlers': ['request_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False
        # },
    }
}

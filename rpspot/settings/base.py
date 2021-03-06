from tempfile import gettempdir
import environ
root = environ.Path(__file__) - 3

# Sets env defaults and casting
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    PUBLIC_ROOT_PATH=(str, None),
    FS_CACHE_PATH=(str, None),
)
env.read_env(root('.env'))

DEBUG = env('DEBUG')

public_root_str = env('PUBLIC_ROOT_PATH')
if public_root_str:
    PUBLIC_ROOT = environ.Path(public_root_str)
else:
    PUBLIC_ROOT = root.path('public/')

fs_cache_str = env('FS_CACHE_PATH')
if fs_cache_str:
    FS_CACHE_ROOT = environ.Path(fs_cache_str)
else:
    FS_CACHE_ROOT = root.path('fs_cache/')

LOG_DIR = env.str('LOG_DIR')

DATABASES = {
    'default': env.db(),  # Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
}


MEDIA_ROOT = PUBLIC_ROOT('media')
MEDIA_URL = 'media/'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_ROOT = PUBLIC_ROOT('static')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    root('static'),
)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/spotify-playlist/radio-paradise/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')  # Raises ImproperlyConfigured exception if SECRET_KEY not in os.environ

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rphistory',
    'trackmap',
    'rest'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
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
        'DIRS': [root('templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
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

INTERNAL_IPS = tuple(env.list('INTERNAL_IPS', None, ['127.0.0.1']))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': FS_CACHE_ROOT('cache')
    },
    'rphistory': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': FS_CACHE_ROOT('rphistory_cache')

    },
    'trackmap': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': FS_CACHE_ROOT('trackmap_cache')

    },
}

REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
}

SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = env.str('SESSION_FILE_PATH', gettempdir())

RP_CACHE = 'rphistory'

SPOTIFY_CACHE = 'default'
SPOTIFY_CLIENT_ID = env.str('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = env.str('SPOTIFY_CLIENT_SECRET')

GEOIP_PATH = env.str('GEOIP_PATH')

TRACKMAP_LOG_LEVEL = env.str('TRACKMAP_LOG_LEVEL', None)
RPHISTORY_LOG_LEVEL = env.str('RPHISTORY_LOG_LEVEL', None)
REQUEST_LOG_LEVEL = env.str('REQUEST_LOG_LEVEL', None)
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
       'request_handler': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR +'/django_request.log',
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        },
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
        'trackmap': {
            'handlers': ['console'],
            'level': TRACKMAP_LOG_LEVEL or 'ERROR',
            'propagate': True
        },
        'rphistory': {
            'handlers': ['console'],
            'level': RPHISTORY_LOG_LEVEL or 'ERROR',
            'propagate': True
        },
        'django.request': {
            'handlers': ['request_handler'],
            'level': REQUEST_LOG_LEVEL or 'ERROR',
            'propagate': False
        },
    }
}

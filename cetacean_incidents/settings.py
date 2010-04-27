import os
from os import path
try:
    from cetacean_incidents.local_settings import *
except ImportError:
    from local_settings import *

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = URL_PREFIX + 'site_media/'
# only needed when serving static media with django itself
MEDIA_ROOT = path.join(PROJECT_PATH, 'site_media/')

ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin/'

LOGIN_URL = URL_PREFIX + 'login/' 
LOGIN_REDIRECT_URL = URL_PREFIX

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_DIRS = (
    path.join(PROJECT_PATH, 'templates/'),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'cetacean_incidents.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.databrowse',
    'django_extensions',
    'cetacean_incidents.apps.countries',
    'cetacean_incidents.apps.locations',
    'cetacean_incidents.apps.contacts',
    'cetacean_incidents.apps.datetime',
    'cetacean_incidents.apps.vessels',
    'cetacean_incidents.apps.taxons',
    'cetacean_incidents.apps.incidents',
)


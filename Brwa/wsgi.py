import os

from django.core.wsgi import get_wsgi_application

settings_module = 'api.deployment_settings' if 'RENDER_EXTERNAL_HOSTNAME' in os.environ else 'api.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE',settings_module )


application = get_wsgi_application()

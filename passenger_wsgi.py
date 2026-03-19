import os
import sys

# Ajouter le projet au path
sys.path.insert(0, os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'social_immo.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

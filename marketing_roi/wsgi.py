"""WSGI config for marketing_roi project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketing_roi.settings")

application = get_wsgi_application()

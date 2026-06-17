"""ASGI config for marketing_roi project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketing_roi.settings")

application = get_asgi_application()

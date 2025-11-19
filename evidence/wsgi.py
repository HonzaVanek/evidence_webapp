"""
WSGI config for evidence project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""


import os
import sys

# Absolutní cesta k rootu projektu (kde je manage.py)
project_path = '/home/vanekj/evidence'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Nastavení Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "evidence.settings")

# Spuštění aplikace
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
"""
WSGI config for the expense tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')

# Import the application from the main project's WSGI file
from expense_tracker.wsgi import application as _application

# Create the WSGI application
application = _application

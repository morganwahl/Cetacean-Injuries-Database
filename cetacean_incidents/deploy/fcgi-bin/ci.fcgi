#!/usr/bin/env python
import sys, os

PROJECT_DIR = "/home/morgan/Development/ci"

# Add a custom Python path.
sys.path = [
    PROJECT_DIR,
] + sys.path

# Switch to the directory of your project. (Optional.)
os.chdir(os.path.join(PROJECT_DIR, 'cetacean_incidents'))

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "cetacean_incidents.settings"

from django.core.servers.fastcgi import runfastcgi
runfastcgi(method="threaded", daemonize="false")


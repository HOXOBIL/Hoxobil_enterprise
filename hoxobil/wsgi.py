# +++++++++++ DJANGO +++++++++++
# To use your own Django app use code like this:
import os
import sys

# assuming your Django settings file is at '/home/yourusername/yourprojectname/yourprojectname/settings.py'
# and your manage.py is at '/home/yourusername/yourprojectname/manage.py'
# path = '/home/yourusername/yourprojectname'

# ----- CHANGE THESE TO YOUR SPECIFIC PATHS ON PYTHONANYWHERE -----
# Path to the directory containing your manage.py
path = '/home/yanex/hoxobil' # Example: /home/your_pythonanywhere_username/your_project_directory_name
if path not in sys.path:
    sys.path.insert(0, path)

# Path to the directory containing your settings.py
# This is usually your project's main configuration directory.
# If settings.py is in /home/yanex/hoxobil/hoxobil/settings.py
# then the path to add is /home/yanex/hoxobil
# The DJANGO_SETTINGS_MODULE will then be 'hoxobil.settings'

# Set the DJANGO_SETTINGS_MODULE environment variable
# This tells Django where to find your settings file.
# Replace 'hoxobil.settings' with 'yourprojectname.settings' if your project is structured differently
os.environ['DJANGO_SETTINGS_MODULE'] = 'hoxobil.settings'
# -------------------------------------------------------------------

# This is the standard WSGI application line for Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

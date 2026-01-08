"""
Django admin configuration with Django Unfold.
"""

from django.contrib import admin
from unfold.admin import UnfoldAdmin

# Configure the admin site with Django Unfold
admin.site = UnfoldAdmin(
    title="Open WebUI Customizer",
    site_header="Open WebUI Customizer Admin",
    site_title="Open WebUI Customizer",
    index_title="Welcome to Open WebUI Customizer Admin Panel",
)
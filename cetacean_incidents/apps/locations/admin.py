from django.contrib import admin

from reversion.admin import VersionAdmin

from models import Location

class LocationAdmin(VersionAdmin):
    pass
admin.site.register(Location, LocationAdmin)


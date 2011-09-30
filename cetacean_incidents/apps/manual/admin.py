from django.contrib import admin

from reversion.admin import VersionAdmin

from models import Manual

class ManualAdmin(VersionAdmin):
    pass
admin.site.register(Manual, ManualAdmin)


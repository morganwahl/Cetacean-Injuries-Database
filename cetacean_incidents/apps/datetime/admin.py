from django.contrib import admin
from reversion.admin import VersionAdmin
from models import DateTime

class DateTimeAdmin(VersionAdmin):
    pass
admin.site.register(DateTime, DateTimeAdmin)


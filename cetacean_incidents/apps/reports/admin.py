from django.contrib import admin

from reversion.admin import VersionAdmin

from models import Report

class ReportAdmin(VersionAdmin):
    pass
admin.site.register(Report, ReportAdmin)


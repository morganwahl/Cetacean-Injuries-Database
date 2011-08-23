from django.contrib import admin

from reversion.admin import VersionAdmin

from models import (
    FileReport,
    StringReport,
)

class FileReportAdmin(VersionAdmin):
    pass
admin.site.register(FileReport, FileReportAdmin)

class StringReportAdmin(VersionAdmin):
    pass
admin.site.register(StringReport, StringReportAdmin)


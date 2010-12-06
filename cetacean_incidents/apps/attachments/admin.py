from django.contrib import admin
from reversion.admin import VersionAdmin
from models import AttachmentType, Attachment

class AttachmentTypeAdmin(VersionAdmin):
    pass
admin.site.register(AttachmentType, AttachmentTypeAdmin)

class AttachmentAdmin(VersionAdmin):
    list_display = ('__unicode__', 'storage_type', 'name', 'attachment_type')
    list_display_links = ('__unicode__',)
    list_filter = ('storage_type', 'attachment_type', 'repo')
admin.site.register(Attachment, AttachmentAdmin)


from django.contrib import admin
from reversion.admin import VersionAdmin
from models import AttachmentType, Attachment

class AttachmentTypeAdmin(VersionAdmin):
    pass
admin.site.register(AttachmentType, AttachmentTypeAdmin)

class AttachmentAdmin(VersionAdmin):
    pass
admin.site.register(Attachment, AttachmentAdmin)


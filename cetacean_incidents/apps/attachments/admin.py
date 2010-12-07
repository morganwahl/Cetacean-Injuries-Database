from django.contrib import admin
from reversion.admin import VersionAdmin
from models import AttachmentType, Attachment, UploadedFile, RepositoryFile

class AttachmentTypeAdmin(VersionAdmin):
    pass
admin.site.register(AttachmentType, AttachmentTypeAdmin)

class AttachmentAdmin(VersionAdmin):
    list_display = ('__unicode__', 'attachment_type')
    list_display_links = ('__unicode__',)
    list_filter = ('attachment_type',)
admin.site.register(Attachment, AttachmentAdmin)

class UploadedFileAdmin(AttachmentAdmin):
    list_display = AttachmentAdmin.list_display + ('uploader', 'datetime_uploaded')
    list_filter = AttachmentAdmin.list_filter + ('uploader', 'datetime_uploaded')
admin.site.register(UploadedFile, UploadedFileAdmin)
class RepositoryFileAdmin(AttachmentAdmin):
    list_filter = AttachmentAdmin.list_filter + ('repo',)
admin.site.register(RepositoryFile, RepositoryFileAdmin)

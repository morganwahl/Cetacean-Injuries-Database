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
    date_hierarchy = 'datetime_uploaded'
    list_display = AttachmentAdmin.list_display + ('uploader', 'datetime_uploaded')
    list_filter = AttachmentAdmin.list_filter + ('uploader', 'datetime_uploaded')
admin.site.register(UploadedFile, UploadedFileAdmin)

def repo_name(rf):
    return rf.repo_name
repo_name.short_description = 'Repository'
repo_name.admin_order_field = 'repo'

def is_dir(rf):
    return rf.is_dir
is_dir.short_description = 'Directory?'
is_dir.boolean = True

class RepositoryFileAdmin(AttachmentAdmin):
    list_display = AttachmentAdmin.list_display + (repo_name, is_dir)
    list_filter = AttachmentAdmin.list_filter + ('repo',)
admin.site.register(RepositoryFile, RepositoryFileAdmin)


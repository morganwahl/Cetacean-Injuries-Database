from django.contrib import admin
from reversion.admin import VersionAdmin
from models import DocumentType, Document, UploadedFile, RepositoryFile

class DocumentTypeAdmin(VersionAdmin):
    pass
admin.site.register(DocumentType, DocumentTypeAdmin)

class DocumentAdmin(VersionAdmin):
    list_display = ('__unicode__', 'document_type')
    list_display_links = ('__unicode__',)
    list_filter = ('document_type',)
admin.site.register(Document, DocumentAdmin)

class UploadedFileAdmin(DocumentAdmin):
    date_hierarchy = 'datetime_uploaded'
    list_display = DocumentAdmin.list_display + ('uploader', 'datetime_uploaded')
    list_filter = DocumentAdmin.list_filter + ('uploader', 'datetime_uploaded')
admin.site.register(UploadedFile, UploadedFileAdmin)

def repo_name(rf):
    return rf.repo_name
repo_name.short_description = 'Repository'
repo_name.admin_order_field = 'repo'

def is_dir(rf):
    return rf.is_dir
is_dir.short_description = 'Directory?'
is_dir.boolean = True

class RepositoryFileAdmin(DocumentAdmin):
    list_display = DocumentAdmin.list_display + (repo_name, is_dir)
    list_filter = DocumentAdmin.list_filter + ('repo',)
admin.site.register(RepositoryFile, RepositoryFileAdmin)


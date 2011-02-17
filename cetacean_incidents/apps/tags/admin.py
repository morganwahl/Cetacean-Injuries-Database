from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Tag

class TagAdmin(VersionAdmin):
    pass
admin.site.register(Tag, TagAdmin)


from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Taxon

class TaxonAdmin(VersionAdmin):
    list_display = ('__unicode__', 'tsn', 'rank', 'name', 'common_names')
    list_display_links = ('__unicode__',)
    list_filter = ('rank',)
admin.site.register(Taxon, TaxonAdmin)

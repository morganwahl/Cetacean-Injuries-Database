from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Taxon

class TaxonAdmin(VersionAdmin):
    pass
admin.site.register(Taxon, TaxonAdmin)

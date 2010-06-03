from django.contrib import admin
from reversion.admin import VersionAdmin
from models import VesselInfo
from forms import VesselAdminForm

class VesselAdmin(VersionAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselAdminForm
admin.site.register(VesselInfo, VesselAdmin)


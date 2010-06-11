from django.contrib import admin
from reversion.admin import VersionAdmin
from models import VesselInfo
from forms import VesselInfoForm

class VesselAdmin(VersionAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselInfoForm
admin.site.register(VesselInfo, VesselAdmin)


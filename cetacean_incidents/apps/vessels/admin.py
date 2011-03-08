from django.contrib import admin

from reversion.admin import VersionAdmin

from forms import VesselInfoForm
from models import (
    VesselInfo,
    VesselTag,
)

class VesselAdmin(VersionAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselInfoForm
admin.site.register(VesselInfo, VesselAdmin)

class VesselTagAdmin(VersionAdmin):
    pass
admin.site.register(VesselTag, VesselTagAdmin)


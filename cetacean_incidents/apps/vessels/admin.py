from django.contrib import admin
from models import VesselInfo, StrikingVesselInfo
from forms import VesselAdminForm

class VesselAdmin(admin.ModelAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselAdminForm
admin.site.register(VesselInfo, VesselAdmin)
admin.site.register(StrikingVesselInfo, VesselAdmin)


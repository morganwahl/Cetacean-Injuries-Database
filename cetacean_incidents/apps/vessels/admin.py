from django.contrib import admin
from reversion.admin import VersionAdmin
from models import VesselInfo, VesselType, VesselTypeRelation
from forms import VesselInfoForm

class VesselAdmin(VersionAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselInfoForm
admin.site.register(VesselInfo, VesselAdmin)

class VesselTypeAdmin(VersionAdmin):
    pass
admin.site.register(VesselType, VesselTypeAdmin)

class VesselTypeRelationAdmin(VersionAdmin):
    pass
admin.site.register(VesselTypeRelation, VesselTypeRelationAdmin)


from django.contrib import admin
from models import Vessel
from forms import VesselAdminForm

class VesselAdmin(admin.ModelAdmin):
    #list_display = ('name', 'flag', 'description')
    
    form = VesselAdminForm
admin.site.register(Vessel, VesselAdmin)


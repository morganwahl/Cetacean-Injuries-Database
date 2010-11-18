from django.contrib import admin
from reversion.admin import VersionAdmin

from models import Stranding, StrandingObservation

class StrandingAdmin(VersionAdmin):
    pass
admin.site.register(Stranding, StrandingAdmin)

class StrandingObservationAdmin(VersionAdmin):
    pass
admin.site.register(StrandingObservation, StrandingObservationAdmin)


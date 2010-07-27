from django.contrib import admin
from reversion.admin import VersionAdmin

from cetacean_incidents.apps.vessels.admin import VesselAdmin

from models import Shipstrike, ShipstrikeObservation, StrikingVesselInfo

class ShipstrikeAdmin(VersionAdmin):
    pass
admin.site.register(Shipstrike, ShipstrikeAdmin)

class ShipstrikeObservationAdmin(VersionAdmin):
    pass
admin.site.register(ShipstrikeObservation, ShipstrikeObservationAdmin)

class StrikingVesselAdmin(VesselAdmin):
    pass
admin.site.register(StrikingVesselInfo, StrikingVesselAdmin)


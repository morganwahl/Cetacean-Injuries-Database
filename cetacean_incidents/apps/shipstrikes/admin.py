from django.contrib import admin

from cetacean_incidents.apps.vessels.admin import VesselAdmin
from cetacean_incidents.apps.incidents.admin import CaseAdmin, ObservationAdmin

from models import Shipstrike, ShipstrikeObservation, StrikingVesselInfo

class ShipstrikeAdmin(CaseAdmin):
    pass
admin.site.register(Shipstrike, ShipstrikeAdmin)

class ShipstrikeObservationAdmin(ObservationAdmin):
    pass
admin.site.register(ShipstrikeObservation, ShipstrikeObservationAdmin)

class StrikingVesselAdmin(VesselAdmin):
    pass
admin.site.register(StrikingVesselInfo, StrikingVesselAdmin)


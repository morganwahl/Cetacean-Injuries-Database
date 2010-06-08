from django.contrib import admin

from models import Entanglement, EntanglementObservation, GearType, GearTypeRelation

from cetacean_incidents.apps.incidents.admin import CaseAdmin

class EntanglementAdmin(CaseAdmin):
    pass
admin.site.register(Entanglement, EntanglementAdmin)

class EntanglementObservationAdmin(ObservationAdmin):
    pass
admin.site.register(EntanglementObservation, EntanglementObservationAdmin)

class GearTypeAdmin(VersionAdmin):
    pass
admin.site.register(GearType, GearTypeAdmin)

class GearTypeRelationAdmin(VersionAdmin):
    pass
admin.site.register(GearTypeRelation, GearTypeRelationAdmin)


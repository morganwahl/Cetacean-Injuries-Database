from django.contrib import admin

from reversion.admin import VersionAdmin

from models import (
    BodyLocation,
    Entanglement,
    EntanglementObservation,
    GearBodyLocation,
    GearOwner,
    GearTarget,
    GearAttribute,
    GearAttributeImplication,
    LocationGearSet,
)

class EntanglementAdmin(VersionAdmin):
    pass
admin.site.register(Entanglement, EntanglementAdmin)

class EntanglementObservationAdmin(VersionAdmin):
    pass
admin.site.register(EntanglementObservation, EntanglementObservationAdmin)

class GearAttributeAdmin(VersionAdmin):
    pass
admin.site.register(GearAttribute, GearAttributeAdmin)

class GearAttributeImplicationAdmin(VersionAdmin):
    pass
admin.site.register(GearAttributeImplication, GearAttributeImplicationAdmin)

class LocationGearSetAdmin(VersionAdmin):
    pass
admin.site.register(LocationGearSet, LocationGearSetAdmin)

class GearOwnerAdmin(VersionAdmin):
    pass
admin.site.register(GearOwner, GearOwnerAdmin)

class BodyLocationAdmin(VersionAdmin):
    list_display = ('name', 'definition', 'ordering')
admin.site.register(BodyLocation, BodyLocationAdmin)

class GearBodyLocationAdmin(VersionAdmin):
    pass
admin.site.register(GearBodyLocation, GearBodyLocationAdmin)

class GearTargetAdmin(VersionAdmin):
    pass
admin.site.register(GearTarget, GearTargetAdmin)


from django.contrib import admin

from reversion.admin import VersionAdmin

from models import (
    BodyLocation,
    Entanglement,
    EntanglementObservation,
    GearBodyLocation,
    GearOwner,
    GearType,
    GearTypeRelation,
)

class EntanglementAdmin(VersionAdmin):
    pass
admin.site.register(Entanglement, EntanglementAdmin)

class EntanglementObservationAdmin(VersionAdmin):
    pass
admin.site.register(EntanglementObservation, EntanglementObservationAdmin)

class GearTypeAdmin(VersionAdmin):
    pass
admin.site.register(GearType, GearTypeAdmin)

class GearTypeRelationAdmin(VersionAdmin):
    pass
admin.site.register(GearTypeRelation, GearTypeRelationAdmin)

class GearOwnerAdmin(VersionAdmin):
    pass
admin.site.register(GearOwner, GearOwnerAdmin)

class BodyLocationAdmin(VersionAdmin):
    list_display = ('name', 'definition', 'ordering')
admin.site.register(BodyLocation, BodyLocationAdmin)

class GearBodyLocationAdmin(VersionAdmin):
    pass
admin.site.register(GearBodyLocation, GearBodyLocationAdmin)


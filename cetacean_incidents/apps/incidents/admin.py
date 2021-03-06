from django.contrib import admin

from reversion.admin import VersionAdmin

from models import (
    Animal,
    Case,
    Observation,
    YearCaseNumber,
)

class AnimalAdmin(VersionAdmin):
    list_display = ('id', 'field_number', 'name')
admin.site.register(Animal, AnimalAdmin)

class CaseAdmin(VersionAdmin):
    pass
admin.site.register(Case, CaseAdmin)

class ObservationAdmin(VersionAdmin):
    pass
admin.site.register(Observation, ObservationAdmin)

# YearCaseNumber doesn't really belong in the admin interface (it's
# automatically maintained), but it's handy for fixing screw-ups. Also, the 
# revision machinery needs to know about it.
class YearCaseNumberAdmin(VersionAdmin):
    pass
admin.site.register(YearCaseNumber, YearCaseNumberAdmin)


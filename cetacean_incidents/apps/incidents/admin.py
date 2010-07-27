from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Animal, Case, Observation, YearCaseNumber

class AnimalAdmin(VersionAdmin):
    pass
admin.site.register(Animal, AnimalAdmin)

# since these models should always be subclasses (but aren't abstract so you can
# query over all the subclass instances), don't include them in the admin or
# revision machinery.

#class CaseAdmin(VersionAdmin):
#    pass
#admin.site.register(Case, CaseAdmin)
#
#class ObservationAdmin(VersionAdmin):
#    pass
#admin.site.register(Observation, ObservationAdmin)

# YearCaseNumber doesn't really belong in the admin interface (it's
# automatically maintained, but it's handy for fixing screw-ups. Also, the 
# revision machinery needs to know about it.
class YearCaseNumberAdmin(VersionAdmin):
    pass
admin.site.register(YearCaseNumber, YearCaseNumberAdmin)

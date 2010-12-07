from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Animal, YearCaseNumber, Case, Observation, ObservationAttachment

class AnimalAdmin(VersionAdmin):
    pass
admin.site.register(Animal, AnimalAdmin)

class CaseAdmin(VersionAdmin):
    pass
admin.site.register(Case, CaseAdmin)

class ObservationAdmin(VersionAdmin):
    pass
admin.site.register(Observation, ObservationAdmin)

class ObservationAttachmentAdmin(VersionAdmin):
    pass
admin.site.register(ObservationAttachment, ObservationAttachmentAdmin)

# YearCaseNumber doesn't really belong in the admin interface (it's
# automatically maintained), but it's handy for fixing screw-ups. Also, the 
# revision machinery needs to know about it.
class YearCaseNumberAdmin(VersionAdmin):
    pass
admin.site.register(YearCaseNumber, YearCaseNumberAdmin)


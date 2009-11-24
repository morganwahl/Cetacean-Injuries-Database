from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Case, Visit, Entanglement, EntanglementVisit, Biopsy, Biopsy_Result

class VisitAdmin(VersionAdmin):
    pass

admin.site.register(Case)
admin.site.register(Visit, VisitAdmin)
admin.site.register(Entanglement)
admin.site.register(EntanglementVisit)
admin.site.register(Biopsy)
admin.site.register(Biopsy_Result)


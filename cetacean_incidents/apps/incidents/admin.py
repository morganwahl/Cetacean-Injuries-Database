from django.contrib import admin
from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation

admin.site.register(Animal)
admin.site.register(Case)
admin.site.register(Observation)
admin.site.register(Entanglement)
admin.site.register(EntanglementObservation)
admin.site.register(Shipstrike)
admin.site.register(ShipstrikeObservation)


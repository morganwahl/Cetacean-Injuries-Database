from django.contrib import admin
from models import Animal, Observation, Tag, TagObservation, Taxon

admin.site.register(Animal)
admin.site.register(Observation)
admin.site.register(Tag)
admin.site.register(TagObservation)
admin.site.register(Taxon)

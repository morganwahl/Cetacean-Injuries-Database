from django.contrib import admin
from models import Person, Organization, Affiliation, PhoneNumber, Address

admin.site.register(Person)
admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(PhoneNumber)
admin.site.register(Address)

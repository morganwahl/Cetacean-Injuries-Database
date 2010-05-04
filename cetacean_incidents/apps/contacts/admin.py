from django.contrib import admin
from reversion.admin import VersionAdmin
from models import Contact, Organization

class ContactAdmin(VersionAdmin):

    def join_all(self, queryset):
        strings = []
        for item in queryset:
            strings.append(item.__unicode__())
        return ', '.join(strings)
    
    def affiliations_column(self, contact):
        return self.join_all(contact.affiliations.all())
    affiliations_column.short_description = 'affiliations'

    list_display = ('name', 'sort_name', 'affiliations_column', 'email', 'phone', 'address')
    list_filter = ('person', 'affiliations')

    filter_horizontal = ('affiliations',)

admin.site.register(Contact, ContactAdmin)

class OrganizationAdmin(VersionAdmin):
    pass
admin.site.register(Organization, OrganizationAdmin)


from django.contrib import admin
from models import Contact, Organization

class ContactAdmin(admin.ModelAdmin):

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

admin.site.register(Organization)


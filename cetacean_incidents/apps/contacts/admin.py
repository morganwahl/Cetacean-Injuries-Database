from django.contrib import admin
from models import Contact, Organization, PhoneNumber, Address, Email

class EmailInline(admin.TabularInline):
    model = Email

class PhoneInline(admin.TabularInline):
    model = PhoneNumber

class AddressInline(admin.TabularInline):
    model = Address

class ContactAdmin(admin.ModelAdmin):

    def join_all(self, queryset):
        strings = []
        for item in queryset:
            strings.append(item.__unicode__())
        return ', '.join(strings)
    
    def affiliations_column(self, contact):
        return self.join_all(contact.affiliations.all())
    affiliations_column.short_description = 'affiliations'

    def emails_column(self, contact):
        return self.join_all(contact.email_addresses.all())
    emails_column.short_description = 'email addresses'

    def phones_column(self, contact):
        return self.join_all(contact.phone_numbers.all())
    phones_column.short_description = 'phone numbers'

    def addresses_column(self, contact):
        return self.join_all(contact.addresses.all())
    addresses_column.short_description = 'addresses'

    list_display = ('name', 'sort_name', 'affiliations_column', 'emails_column', 'phones_column', 'addresses_column')
    list_filter = ('person', 'affiliations')

    filter_horizontal = ('affiliations',)
    inlines = [
        EmailInline,
        PhoneInline,
        AddressInline,
    ]

admin.site.register(Contact, ContactAdmin)

admin.site.register(Organization)


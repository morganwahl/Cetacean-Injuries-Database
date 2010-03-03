from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from models import Contact, Organization

class ContactForm(forms.ModelForm):
    
    affiliations = forms.ModelMultipleChoiceField(
        queryset= Organization.objects.all(),
        widget= FilteredSelectMultiple(
            verbose_name= Contact.affiliations.field.verbose_name,
            is_stacked= False,
        ),
        required = not Contact.affiliations.field.blank,
        help_text = Contact.affiliations.field.help_text,
    )
    
    class Media:
        css = {
            'all': ('selectfilter.css',)
        }
    
    class Meta:
        model = Contact


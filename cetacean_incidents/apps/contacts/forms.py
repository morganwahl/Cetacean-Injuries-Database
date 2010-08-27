from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from models import Contact, Organization
from django.core.urlresolvers import reverse

class EmailInput(forms.TextInput):
    '''\
    Just like a django.forms.TextWidget, except with the 'type' attribute set
    to 'email' (a backward-compatible HTML5 input-element type).
    '''
    
    input_type = 'email'

class OrganizationForm(forms.ModelForm):
    
    class Meta:
        model = Organization

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
    
    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = Contact._meta.get_field('email')
    email = forms.EmailField(
        required= _f.blank != True,
        help_text= _f.help_text,
        max_length= _f.max_length,
        label= _f.verbose_name.capitalize(),
        widget=EmailInput,
    )
    
    @property
    def media(self):
        # the FilteredSelectMultiple assumes jsi18n catalog and admin-specific
        # css have been loaded. The CSS rules that it needs have been placed in    
        # our own site-media file 'selectfilter.css'. The jsi18n catalog is
        # available at a urlconf named 'jsi18n'
        return forms.Media(
            css = {'all': ('selectfilter.css',)},
            js = (reverse('jsi18n'),),
        ) + self.fields['affiliations'].widget.media
    
    class Meta:
        model = Contact


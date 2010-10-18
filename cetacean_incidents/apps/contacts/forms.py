from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from models import Contact, Organization
from django.core.urlresolvers import reverse

from cetacean_incidents.apps.merge_form.forms import MergeForm

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
        widgets = {
            'email': EmailInput,
        }

class ContactMergeSourceForm(forms.Form):
    
    source = forms.ModelChoiceField(
        queryset= Contact.objects.all(),
        label= 'other contact',
    )

class ContactMergeForm(MergeForm):
    
    affiliations = forms.ModelMultipleChoiceField(
        queryset= Organization.objects.all(),
        widget= FilteredSelectMultiple(
            verbose_name= Contact.affiliations.field.verbose_name,
            is_stacked= False,
        ),
        required = not Contact.affiliations.field.blank,
        help_text = Contact.affiliations.field.help_text,
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
        widgets = {
            'email': EmailInput,
        }
    

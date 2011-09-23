from django.core.urlresolvers import reverse
from django import forms
from django.db.models import Q
from django.forms.formsets import formset_factory

from django.contrib.admin.widgets import FilteredSelectMultiple

from cetacean_incidents.apps.merge_form.forms import MergeForm

from cetacean_incidents.apps.search_forms.fields import (
    QueryField,
    MatchOptions,
    MatchOption,
)
from cetacean_incidents.apps.search_forms.forms import SearchForm
from cetacean_incidents.apps.search_forms.related import ManyToManyFieldQuery

from models import (
    Contact,
    Organization,
)

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

    # TODO should we preservere the args-ordering of ModelForm?
    def __init__(self, data=None, prefix=None, *args, **kwargs):
        super(ContactForm, self).__init__(data, prefix=prefix, *args, **kwargs)

        # the exisintg affiliations will be in the widget in for 
        # 'affiliations'. 
        # This is only for adding new Organizations from within the same page
        new_affs_prefix = 'new_affs'
        if not prefix is None:
            new_affs_prefix = prefix + '-' + new_affs_prefix
        # TODO take argument for 'extra'?
        # we're not using modelformset_factory since we're only creating new
        # Organizations, not editing existing ones.
        new_affs_class = formset_factory(OrganizationForm, extra=2)
        self.new_affs = new_affs_class(data, prefix=new_affs_prefix)

    def __unicode__(self):
        return super(ContactForm, self).__unicode__() + self.new_affs.__unicode__()
    
    def __iter__(self):
        for result in super(ContactForm, self).__iter__():
            yield result
        # TODO yield self.new_affs

    def is_valid(self):
        return super(ContactForm, self).is_valid() and self.new_affs.is_valid()
    
    def as_table(self):
        return super(ContactForm, self).as_table() + self.new_affs.as_table()
    
    def non_field_errors(self):
        return super(ContactForm, self).non_field_errors() + self.new_affs.non_form_errors()
    
    def full_clean(self):
        super(ContactForm, self).full_clean()
        self.new_affs.full_clean()
    
    def clean(self):
        cleaned_data = super(ContactForm, self).clean()
        # Formset.clean doesn't return anything
        self.new_affs.clean()
        return cleaned_data
    
    def has_changed(self):
        raise NotImplementedError(
            "has_changed not implemented for ContactForm.new_affs",
        )
    
    def is_multipart(self):
        return super(ContactForm, self).is_multipart() or self.new_affs.is_multipart()

    affiliations = forms.ModelMultipleChoiceField(
        queryset= Organization.objects.all(),
        widget= FilteredSelectMultiple(
            verbose_name= Contact.affiliations.field.verbose_name,
            is_stacked= False,
        ),
        required = not Contact.affiliations.field.blank,
        help_text = Contact.affiliations.field.help_text,
    )
    
    def save(self, commit=True):
        contact = super(ContactForm, self).save(commit)
        new_orgs = []
        # add the affiliations from the new_affs formset
        for org_form in self.new_affs.forms:
            # don't save orgs with blank names.
            if not 'name' in org_form.cleaned_data:
                continue
            # if given the same name as an existing org, just use the existing
            # org
            org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
            if org_query.count():
                org = org_query[0] # orgs shouldn't really have 
                                   # identical names anyway, so 
                                   # just use the first one.
            else:
                org = org_form.save(commit)
            new_orgs.append(org)

        if commit:
            for org in new_orgs:
                contact.affiliations.add(org)
        else:
            # we need to override self.save_m2m, which didn't exist until 
            # we called super.save() above
            old_save_m2m = self.save_m2m
            def new_save_m2m():
                old_save_m2m()
                self.new_affs.save_m2m()
                for org in new_orgs:
                    contact.affiliations.add(org)
            self.save_m2m = new_save_m2m
            
        return contact
    
    @property
    def media(self):
        # the FilteredSelectMultiple assumes jsi18n catalog and admin-specific
        # css have been loaded. The CSS rules that it needs have been placed in    
        # our own site-media file 'selectfilter.css'. The jsi18n catalog is
        # available at a urlconf named 'jsi18n'
        return forms.Media(
            css = {'all': ('selectfilter.css',)},
            js = (reverse('jsi18n'),),
        ) + self.fields['affiliations'].widget.media + self.new_affs.media
    
    class Meta:
        model = Contact
        widgets = {
            'email': EmailInput,
        }

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

class AffiliationQueryField(QueryField):
    
    default_match_options = MatchOptions([
        MatchOption('and', 'all of',
            forms.ModelMultipleChoiceField(
                queryset= Organization.objects.all(),
                widget= forms.CheckboxSelectMultiple,
            ),
        ),
        MatchOption('or', 'any of',
            forms.ModelMultipleChoiceField(
                queryset= Organization.objects.all(),
                widget= forms.CheckboxSelectMultiple,
            ),
        ),
    ])
    
    blank_option = True
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.name
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            if lookup_type == 'and':
                # lookup_value is a list of Organizations
                if len(lookup_value) == 0:
                    return Q()
                
                q = Q()
                # no way to return a Q value for contacts with each of these
                # targets :-(
                # this is a so-so workaround
                qs = self.model_field.model.objects
                for target in lookup_value:
                    qs = qs.filter(**{lookup_fieldname: target})
                ids = qs.values_list('pk', flat=True)
                q = Q(pk__in=ids)
                
                return q
        
            if lookup_type == 'or':
                # lookup_value is a list of Organizations
                if len(lookup_value) == 0:
                    return Q()
                
                q = Q(**{lookup_fieldname + '__in': lookup_value})
                
                return q

        return super(AffiliationQueryField, self).query(value, prefix)

class ContactSearchForm(SearchForm):

    class ContactAffiliationsSearchForm(SearchForm):
        class Meta:
            model = Organization
            exclude = ('id',)

    _f = Contact._meta.get_field('affiliations')
    affiliations = AffiliationQueryField(
        model_field= _f,
        required=False,
        label= _f.verbose_name.capitalize(),
        # we have to set the help_text ourselves since ManyToManyField alters
        # the field's help_text with instructions for a SelectMultiple widget.
        help_text= u'search for contacts with these affiliations',
    )

    class Meta:
        model = Contact
        exclude = ('id', 'sort_name')
        sort_field = True


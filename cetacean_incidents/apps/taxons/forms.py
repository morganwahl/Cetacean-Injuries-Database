from django.core.validators import EMPTY_VALUES
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django import forms
from django.forms.models import (
    ModelChoiceIterator,
    ModelMultipleChoiceField,
)    
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.generic_templates.templatetags.html_filter import html

from cetacean_incidents.apps.dag.widgets import HierarchicalCheckboxSelectMultiple

from cetacean_incidents.apps.jquery_ui.widgets import ModelAutocomplete

from cetacean_incidents.apps.merge_form.forms import MergeForm

from models import Taxon

class TaxonAutocomplete(ModelAutocomplete):
    
    model = Taxon
    
    def __init__(self, attrs=None):
        super(TaxonAutocomplete, self).__init__(
            attrs=attrs,
            source= 'taxon_autocomplete_source',
            options= {
                'minLength': 2,
            },
        )
    
    def id_to_display(self, id):
        return self.model.objects.get(id=id).scientific_name()
    
    def id_to_html_display(self, id):
        taxon = Taxon.objects.get(id=id)
        return html(taxon)

    def render(self, name, value, attrs=None):
        return super(TaxonAutocomplete, self).render(
            name=name,
            value=value,
            attrs=attrs,
            custom_html= 'taxon_autocomplete_entry',
            # TODO better was to pass this URL
            extra_js= '''\
            taxon_autocomplete_source_url = "%s";
            ''' % reverse('taxon_search'),
        )
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE, 'taxon_autocomplete.css')}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'taxon_autocomplete.js')

class TaxonChoiceIterator(ModelChoiceIterator):
    # based on dag.forms.DAGModelChoiceIterator
    
    @staticmethod
    def get_roots(queryset):
        '''\
        Filters out taxa that are _direct_ descendants of other taxa in this queryset.
        '''
        
        return queryset.exclude(supertaxon__in=queryset.all())
    
    def _qs_to_choices(self, qs):
        choices = []
        pks = qs.values_list('pk', flat=True)
        roots = self.get_roots(qs)
        for root in roots:
            # TODO this will actually include widget that shouldn't be in choices
            children = root.subtaxa
            if children.count():
                choices.append((
                    self.choice(root),
                    self._qs_to_choices(children)
                ))
            else:
                choices.append(self.choice(root))
        
        return tuple(choices)

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        if self.field.cache_choices:
            if self.field.choice_cache is None:
                self.field.choice_cache = self._qs_to_choices(self.queryset)
            for choice in self.field.choice_cache:
                yield choice
        else:
            for choice in self._qs_to_choices(self.queryset):
                yield choice

class TaxonMultipleChoiceField(ModelMultipleChoiceField):
    """
    A MultipleChoiceField whose choices are Taxa.
    """
    # TODO merge with DAGField?
    
    widget = HierarchicalCheckboxSelectMultiple
    
    def label_from_instance(self, taxon):
        label = u"<i>%s</i>" % taxon.scientific_name()
        if taxon.common_names:
            label += u"<br/>%s" % taxon.common_names
        return mark_safe(label)
    
    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices

        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not been
        # consumed. Note that we're instantiating a new QuerySetIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        return TaxonChoiceIterator(self)

    choices = property(_get_choices, ModelMultipleChoiceField._set_choices)
    
class TaxonField(forms.Field):
    # based on ModelChoiceField, except you can't choose queryset, and there
    # are no choices, since we're using an AJAX-y TaxonAutocomplete
    
    # a Field's widget defaults to self.widget
    widget = TaxonAutocomplete
    
    def clean(self, value):
        '''Value is a taxon ID as (as a string), returns a Taxon instance.'''
        
        super(TaxonField, self).clean(value)
        if value in EMPTY_VALUES:
            return None
        try:
            value = Taxon.objects.get(pk=value)
        except Taxon.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value

class TaxonMergeForm(MergeForm):
    
    class Meta:
        model = Taxon

class TaxonQueryField(TaxonField):
    
    def __init__(self, model_field, *args, **kwargs):
        # TODO model_field should be a One2One or ForeignKey reference to a
        # Taxon
        self.model_field = model_field
        return super(TaxonQueryField, self).__init__(*args, **kwargs)
    
    def query(self, value, prefix=None):
        if value is None:
            return Q()
        
        lookup_fieldname = self.model_field.name
        if not prefix is None:
            lookup_fieldname = prefix + '__' + lookup_fieldname
        
        return Q(**{lookup_fieldname + '__in': value.with_descendants()})


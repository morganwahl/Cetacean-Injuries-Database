from django.conf import settings
from django.core.urlresolvers import reverse
from django import forms

from cetacean_incidents.apps.documents.forms import DocumentableMergeForm

from cetacean_incidents.apps.jquery_ui.widgets import (
    Datepicker,
    ModelAutocomplete,
)

from cetacean_incidents.apps.search_forms.forms import SearchForm
from cetacean_incidents.apps.search_forms.related import (
    HideableReverseForeignKeyQuery,
    ForeignKeyQuery,
)

from cetacean_incidents.apps.taxons.forms import (
    TaxonField,
    TaxonQueryField,
)

from ..models import (
    Animal,
    Case,
    Observation,
)

from observation import ObservationSearchForm

class AnimalAutocomplete(ModelAutocomplete):
    
    model = Animal
    
    def __init__(self, attrs=None):
        super(AnimalAutocomplete, self).__init__(
            attrs=attrs,
            source= 'animal_autocomplete_source',
            options= {
                'minLength': 2,
            },
        )
    
    def render(self, name, value, attrs=None):
        return super(AnimalAutocomplete, self).render(
            name=name,
            value=value,
            attrs=attrs,
            custom_html= 'animal_autocomplete_entry',
            # TODO better way to pass this URL
            extra_js= '''\
            animal_autocomplete_source_url = "%s";
            ''' % reverse('animal_search_json'),
        )
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE, 'animal_autocomplete.css')}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'animal_autocomplete.js')

class AnimalForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal._meta.get_field('determined_taxon')
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

class AnimalMergeSourceForm(forms.Form):
    
    # note that all fields are added dynamically in __init__
    
    def __init__(self, destination, *args, **kwargs):
        super(AnimalMergeSourceForm, self).__init__(*args, **kwargs)
        
        self.fields['source'] = forms.ModelChoiceField(
            queryset= Animal.objects.exclude(id=destination.id),
            label= 'other %s' % Animal._meta.verbose_name,
            required= True, # ensures an animal is selected
            initial= None,
            widget= AnimalAutocomplete,
            help_text= u"""Choose an animal to merge into this one. That animal's entry will be deleted and references to it will refer to this entry instead.""",
            error_messages= {
                'required': u"You must select an animal.",
            },
        )
        
# TODO this is the same as the AnimalForm, just with a different superclass
class AnimalMergeForm(DocumentableMergeForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal._meta.get_field('determined_taxon')
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    
    def save(self, commit=True):
        # concatenate import_notes
        self.destination.import_notes += self.source.import_notes
        return super(AnimalMergeForm, self).save(commit)
        
    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

class AnimalSearchForm(SearchForm):
    
    class AnimalCaseSearchForm(SearchForm):
        class Meta:
            model = Case
            exclude = ('id', 'import_notes', 'case_type') + tuple(Case.si_n_m_fieldnames())
    
    # TODO better way of finding ROs?
    _f = Case._meta.get_field_by_name('animal')[0]
    cases = HideableReverseForeignKeyQuery(
        model_field= _f,
        subform= AnimalCaseSearchForm,
        help_text= "Only match animals with a case that matches this."
    )

    class AnimalObservationSearchForm(ObservationSearchForm):
        class Meta(ObservationSearchForm.Meta):
            sort_field = False

    # TODO better way of finding ROs?
    _f = Observation._meta.get_field_by_name('animal')[0]
    observations = HideableReverseForeignKeyQuery(
        model_field= _f,
        subform= AnimalObservationSearchForm,
        help_text= "Only match animals with an observation that matches this."
    )
    
    # TODO better way of finding ROs?
    _f = Animal._meta.get_field_by_name('determined_taxon')[0]
    determined_taxon = TaxonQueryField(model_field= _f, required=False)

    class Meta:
        model = Animal
        exclude = ('id', 'import_notes',)
        sort_field = True


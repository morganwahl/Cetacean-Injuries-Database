from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.documents.forms import DocumentableMergeForm

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from cetacean_incidents.apps.search_forms.forms import SearchForm
from cetacean_incidents.apps.search_forms.related import (
    HideableReverseManyToManyFieldQuery,
    HideableForeignKeyQuery,
)

from cetacean_incidents.apps.reports.forms import (
    FileReportForm,
    StringReportForm,
)
from cetacean_incidents.apps.reports.models import Report

from cetacean_incidents.apps.jquery_ui.widgets import CheckboxSelectMultiple as JQueryCheckboxSelectMultiple

from cetacean_incidents.apps.utils.forms import RestModelForm

from ..models import (
    Animal,
    Case,
    Observation,
    SeriousInjuryAndMortality,
    YearCaseNumber,
)

from animal import AnimalSearchForm
from observation import ObservationSearchForm

class CaseAnimalForm(forms.Form):
    '''\
    Form to change the animal of a case. Provides one field to select an animal.
    '''
    
    animal = forms.ModelChoiceField(
        queryset= Animal.objects.all(),
        required= False, # makes the empty choice (which indicates 'new animal') available
        empty_label= '<new animal>',
        widget= forms.RadioSelect,
    )

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case
        # custom widgets for date fields
        widgets = {
            'happened_after': Datepicker,
        }
        # don't edit model-relationship fields
        exclude = ('animal',)
        # don't edit SI&MD fields
        exclude += tuple(Case.si_n_m_fieldnames())

Case.form_class = CaseForm

class SINMForm(RestModelForm):
    
    class Meta:
        model = Case
        # ordering matters
        fields = (
            'review_1_date',
            'review_1_inits',
            'review_2_date',
            'review_2_inits',
            'reviewer_casetype',
            'case_confirm_criteria',
            'animal_fate',
            'fate_cause',
            'fate_cause_indications',
            'si_prevented',
            'included_in_sar',
            'review_1_notes',
            'review_2_notes',
        )
        widgets = {
            'review_1_date': Datepicker,
            'review_2_date': Datepicker,
        }

class CaseMergeSourceForm(forms.Form):
    
    # note that all fields are added dynamically in __init__
    
    def __init__(self, destination, *args, **kwargs):
        super(CaseMergeSourceForm, self).__init__(*args, **kwargs)
        
        self.fields['source'] = forms.ModelChoiceField(
            queryset= Case.objects.exclude(id=destination.id).filter(animal=destination.animal),
            label= 'other %s' % Case._meta.verbose_name,
            required= True, # ensures a case is selected
            initial= None,
            help_text= u"""Choose a case to merge into this one. That case will be deleted and references to it will refer to this case instead.""",
            error_messages= {
                'required': u"You must select a case."
            },
        )

class CaseMergeForm(DocumentableMergeForm):
    
    def __init__(self, source, destination, data=None, **kwargs):
        # don't merge cases that aren't already for the same animal
        if source.animal != destination.animal:
            raise ValueError("can't merge cases for different animals!")

        # TODO SI&M !
        if destination.si_n_m_info or source.si_n_m_info:
            raise NotImplementedError("Can't yet merge cases with Serious Injury and Mortality info.")
        
        super(CaseMergeForm, self).__init__(source, destination, data, **kwargs)
    
    def save(self, commit=True):
        # append source import_notes to destination import_notes
        self.destination.import_notes += self.source.import_notes

        # TODO SI&M !
        
        # prepend source names to destination names
        if self.destination.names:
            if self.source.names:
                self.destination.names = self.source.names + ',' + self.destination.names
            else:
                self.source.names = self.destination.names
        
        # In cases where souce and destination has YearCaseNumbers in the same
        # year, Case.save() will handle setting destination.current_yearnumber
        # to the lower of the two numbers.
        
        return super(CaseMergeForm, self).save(commit)

    class Meta:
        model = Case
        # don't even include this field so that a CaseMergeForm can't change the
        # animal of the destination case
        exclude = ('animal',)

class CaseSearchForm(SearchForm):

    class CaseAnimalSearchForm(AnimalSearchForm):
        class Meta(AnimalSearchForm.Meta):
            sort_field = False
    
    _f = Case._meta.get_field('animal')
    animal = HideableForeignKeyQuery(
        model_field= _f,
        subform_class= CaseAnimalSearchForm,
        help_text= "Only match cases for an animal that matches this."
    )

    class CaseObservationSearchForm(ObservationSearchForm):
        class Meta(ObservationSearchForm.Meta):
            sort_field = False

    _f = Observation._meta.get_field('cases')
    observations = HideableReverseManyToManyFieldQuery(
        model_field= _f,
        subform_class= CaseObservationSearchForm,
        help_text= "Only match cases with an observation that matches this."
    )

    class Meta:
        model = Case
        exclude = ('id', 'import_notes')
        sort_field = True
    
    def __init__(self, *args, **kwargs):
        super(CaseSearchForm, self).__init__(*args, **kwargs)
        self.fields['sort_by'].initial = 'date'
        # put an extra CSS class on SI&M fields
        for fieldname in SeriousInjuryAndMortality.si_n_m_fieldnames():
            if fieldname not in self.fields:
                continue
            
            self.fields[fieldname].widget.attrs.update({
                'class': 'si_n_m',
            })
    
    def as_table(self):
        output = super(CaseSearchForm, self).as_table()
        output = mark_safe(u"""\
            <tr><td colspan="2"><a href="" class="toggle_sinm_link">show/hide <abbr title="Serious Injury and Mortality">SI&M</abbr> fields...</a></td></tr>
        """ + output)
        return output
    
    class Media:
        js = (settings.JQUERY_FILE, 'toggle_sinm.js')
    
class CaseSelectionForm(forms.Form):
    def __init__(self, cases, *args, **kwargs):
        super(CaseSelectionForm, self).__init__(*args, **kwargs)
        self.fields['cases'] = forms.ModelMultipleChoiceField(
            queryset= cases,
            initial= cases,
            label= u'',
            widget= JQueryCheckboxSelectMultiple,
        )

class UseCaseReportForm(forms.Form):
    
    show = forms.BooleanField(
        initial= False,
        label= u'generate a report using these cases...'
    )

    report = forms.ModelChoiceField(queryset= Report.objects.all())

    def __init__(self, cases_qs, cases_initial, *args, **kwargs):
        super(UseCaseReportForm, self).__init__(*args, **kwargs)
        self.fields['cases'] = forms.ModelMultipleChoiceField(
            queryset= cases_qs,
            initial= cases_initial,
            label= u'',
            widget= JQueryCheckboxSelectMultiple,
        )

    def clean_cases(self):
        result = []
        for c in self.cleaned_data['cases']:
            result.append(c.specific_instance())
        return result

class CaseCSVForm(forms.Form):
    
    show = forms.BooleanField(
        initial= False,
        label= u'generate a CSV file with the data from these cases...'
    )
    
    def __init__(self, cases_qs, cases_initial, *args, **kwargs):
        super(CaseCSVForm, self).__init__(*args, **kwargs)
        self.fields['cases'] = forms.ModelMultipleChoiceField(
            queryset= cases_qs,
            initial= cases_initial,
            label= u'',
            widget= JQueryCheckboxSelectMultiple,
        )
        
    def clean_cases(self):
        result = []
        for c in self.cleaned_data['cases']:
            result.append(c.specific_instance())
        return result

class ChangeCaseReportForm(forms.Form):
    
    show = forms.BooleanField(
        initial= False,
        label= u'add/edit a report template using these cases...'
    )
    
    report = forms.ModelChoiceField(
        queryset= Report.objects.all(),
        required= False,
        empty_label= '<new report template>',
    )
    
    report_type = forms.ChoiceField(
        choices= (
            ('string', 'HTML directly edited on this site'),
            ('file', 'an uploaded file'),
        ),
        label= 'type of new report',
    )


from django import forms

from cetacean_incidents.apps.documents.forms import DocumentableMergeForm

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from ..models import (
    Animal,
    Case,
    YearCaseNumber,
)

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
            'review_1_date': Datepicker,
            'review_2_date': Datepicker,
        }
        # don't edit model-relationship fields
        exclude = ('animal',)

class AddCaseForm(CaseForm):
    
    class Meta(CaseForm.Meta):
        exclude = ('animal',)

Case.form_class = AddCaseForm

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


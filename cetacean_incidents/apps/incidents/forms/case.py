from django import forms

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from ..models import (
    Animal,
    Case,
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

class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case


from django import forms
from models import Case, Visit, Entanglement, EntanglementVisit

from cetacean_incidents.apps.animals.models import Animal

visit_forms = {}

class CaseForm(forms.ModelForm):

    class Meta:
        model = Case

class VisitForm(forms.ModelForm):

    animal = forms.ModelChoiceField(
        queryset= Animal.objects.all(),
        empty_label= '<new animal>',
        required= False,
    )

    class Meta:
        model = Visit
        # the case for a new visit is set by the view
        # tags_seen is an many-to-many relationship with an intermediary model.
        # ModelForm can't handle that.
        exclude = ('case', 'tags_seen') 

visit_forms['Case'] = VisitForm

class CreateCaseForm(CaseForm):
    '''\
    A CaseForm with some additional fields for the inital creation of animals
    and a visit.
    '''
    
    # TODO get this info from the model
    type_names = (
        ('e', 'entanglement'),
    )
    case_type = forms.ChoiceField(choices=type_names)
    # type_models's keys should be values of the case_type field
    type_models = {
        'e': Entanglement,
    }

class EntanglementForm(forms.ModelForm):
    
    class Meta:
        model = Entanglement

class EntanglementVisitForm(forms.ModelForm):

    class Meta:
        model = EntanglementVisit
        exclude = VisitForm.Meta.exclude
visit_forms['Entanglement'] = EntanglementVisitForm


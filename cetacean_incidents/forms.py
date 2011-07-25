'''\
Forms that make use of multiple apps (really just incidents, and its
descendants: entanglements and shipstrikes.
'''

# TODO does this file's existence even make sense? Does this mean entanglements
# and shipstrikes shouldn't be separate apps from incidents? No, since one
# could imagine having the incidents app in a library and extending it to 
# create a new Case type, like strandings.

from django import forms

from cetacean_incidents.apps.entanglements.forms import (
    AddEntanglementForm,
    EntanglementForm,
)
from cetacean_incidents.apps.entanglements.models import Entanglement

from cetacean_incidents.apps.incidents.forms import (
    AnimalAutocomplete,
    CaseForm,
)
from cetacean_incidents.apps.incidents.models import (
    Animal,
    Case,
)

from cetacean_incidents.apps.shipstrikes.forms import (
    AddShipstrikeForm,
    ShipstrikeForm,
)
from cetacean_incidents.apps.shipstrikes.models import Shipstrike

def CaseTypeForm_factory(user):
    'Generates a CaseTypeForm based on what types a user can add.'
    
    # a tuple of doubles: <class>.__name__, <class>._meta.verbose_name
    type_names = (
        ('Case', 'Case (generic stranding case)'),
        ('Entanglement', 'Entanglement'),
        ('Shipstrike', 'Shipstrike'),
    )
    type_perms = {
        'Case': lambda u: u.has_perm('incidents.add_case'),
        'Entanglement': lambda u: u.has_perm('entanglements.add_entanglement'),
        'Shipstrike': lambda u: u.has_perm('shipstrikes.add_shipstrike'),
    }

    class _CaseTypeForm(forms.Form):
        '''\
        A form with the case-type field needed when creating new cases.
        '''
        
        # TODO port to documents.Specificable's API
        
        # where <class> is a subclass of Case:
        
        # keys are <class>.__name__, values are <class>
        type_models = {
            'Case': Case,
            'Entanglement': Entanglement,
            'Shipstrike': Shipstrike,
        }

        case_type = forms.ChoiceField(
            choices=(
                ('', '<select a case type>'),
            ) + filter(
                lambda choice: type_perms[choice[0]](user),
                type_names,
            )
        )

        # basically the same problem as above; we need a list of subclass of CaseForm
        case_form_classes = {
            'Case': CaseForm,
            'Entanglement': EntanglementForm,
            'Shipstrike': ShipstrikeForm,
        }
        addcase_form_classes = {
            'Case': CaseForm,
            'Entanglement': AddEntanglementForm,
            'Shipstrike': AddShipstrikeForm,
        }
    
    return _CaseTypeForm

class AnimalChoiceForm(forms.Form):
    '''\
    A form that depends on whether a user can add new animals.
    '''
    
    # all the fields are generated dynamically in __init__
    
    def __init__(self, user=None, *args, **kwargs):
        super(AnimalChoiceForm, self).__init__(*args, **kwargs)

        if not user is None and user.has_perm('incidents.add_animal'):
            self.can_add = True
        else:
            self.can_add = False
        
        if self.can_add:
            self.fields['new_animal'] = forms.TypedChoiceField(
                choices= (
                    ('yes', 'add a new animal entry'),
                    ('', 'use a existing entry'),
                ),
                coerce= bool,
                initial= '',
                required= False, # allows a False value
                label= '',
                widget= forms.RadioSelect,
            )
        
        self.fields['existing_animal'] = forms.ModelChoiceField(
            queryset= Animal.objects.all(),
            widget = AnimalAutocomplete,
            empty_label= '<none chosen>',
            required= not self.can_add,
            help_text= "choose an existing animal in the database",
        )
    
    def clean(self):
        # if not self.can_add fields['existing_animal'].required = True
        data = self.cleaned_data
        if self.can_add:
            # fields['existing_animal'].required = False, but it is required if
            # fields['new_animal'] is False
            new = data.get('new_animal')

            if not new:
                if 'existing_animal' in data: # did 'existing_animal' validate?
                    if data['existing_animal'] is None:
                        raise forms.ValidationError('Either add a new animal or choose an existing one.')
        
        return data
            
def merge_source_form_factory(model, destination):

    class _MergeSourceForm(forms.Form):
        
        source = forms.ModelChoiceField(
            queryset= model.objects.exclude(id=destination.id),
            label= 'other %s' % model._meta.verbose_name,
        )
    
    return _MergeSourceForm

class PagingForm(forms.Form):
    
    per_page = forms.IntegerField(
        initial= 20,
        min_value= 1,
        required= False,
        label= 'Results per page',
    )
    page_num = forms.IntegerField(
        widget = forms.HiddenInput,
        initial= 1,
        min_value= 1,
        required= False,
    )


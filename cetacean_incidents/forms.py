'''\
Forms that make use of multiple apps (really just incidents, and its
descendants: entanglements and shipstrikes.
'''

# TODO does this file's existence even make sense? Does this mean entanglements
# and shipstrikes shouldn't be separate apps from incidents? No, since one
# could imagine having the incidents app in a library and extending it to 
# create a new Case type, like strandings.

from django import forms

from cetacean_incidents.apps.incidents.models import Case, Animal
from cetacean_incidents.apps.incidents.forms import CaseForm
from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.entanglements.forms import EntanglementForm, AddEntanglementForm
from cetacean_incidents.apps.shipstrikes.models import Shipstrike
from cetacean_incidents.apps.shipstrikes.forms import ShipstrikeForm, AddShipstrikeForm

class CaseTypeFormMeta(forms.Form.__metaclass__):
    
    def __new__(self, name, bases, dict):
        type_names = []
        type_models = {}
        for c in Case.detailed_classes.values():
            type_names.append( (c.__name__, c._meta.verbose_name) )
            # type_models's keys should be values of the case_type field
            type_models[c.__name__] = c
        type_names = tuple(type_names)
        
        dict['type_names'] = type_names
        dict['case_type'] = forms.ChoiceField(choices=(('','<select a case type>'),) + type_names)
        dict['type_models'] = type_models
        return super(CaseTypeFormMeta, self).__new__(self, name, bases, dict)

class CaseTypeForm(forms.Form):
    '''\
    A form with the case-type field needed when creating new cases.
    '''
    
    # TODO get this working
    ## this form is almost entirely dynamically created
    #__metaclass__ = CaseTypeFormMeta
    
    # where <class> is a subclass of Case:
    
    # a tuple of doubles: <class>.__name__, <class>._meta.verbose_name
    type_names = (('Entanglement', 'Entanglement'), ('Shipstrike', 'Shipstrike'))
    # keys are <class>.__name__, values are <class>
    type_models = {
        'Entanglement': Entanglement,
        'Shipstrike': Shipstrike,
    }

    case_type = forms.ChoiceField(
        choices=(
            ('', '<select a case type>'),
        ) + type_names,
    )

    # basically the same problem as above; we need a list of subclass of CaseForm
    case_form_classes = {
        'Case': CaseForm,
        'Entanglement': EntanglementForm,
        'Shipstrike': ShipstrikeForm,
    }
    addcase_form_classes = {
        'Entanglement': AddEntanglementForm,
        'Shipstrike': AddShipstrikeForm
    }

class AnimalChoiceForm(forms.Form):
    
    animal = forms.ModelChoiceField(
        queryset= Animal.objects.all(),
        empty_label= '<new animal>',
        required=False,
        help_text= "choose an existing animal in the database, or to add a new one",
    )

def merge_source_form_factory(model, destination):

    class _MergeSourceForm(forms.Form):
        
        source = forms.ModelChoiceField(
            queryset= model.objects.exclude(id=destination.id),
            label= 'other %s' % model._meta.verbose_name,
        )
    
    return _MergeSourceForm


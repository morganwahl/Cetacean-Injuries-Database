from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation, GearType

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact

observation_forms = {}

class AnimalForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = Animal.determined_taxon.field
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    
    class Meta:
        model = Animal

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class AddCaseForm(CaseForm):
    '''\
    A CaseForm minus the Animal field, for adding a case to an existing animal.
    '''

    class Meta(CaseForm.Meta):
        exclude = ('animal',)

class GearTypeWidget(forms.widgets.CheckboxSelectMultiple):
    '''\
    A widget that shows a javascripty heirarchy of checkboxes for GearTypes.
    '''
    
    # a modified version of django.forms.widgets.CheckboxSelectMultiple
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        print repr(value)
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])

        choices_iter = chain(self.choices, choices)
        
        # traverse all GearTypes in a tree-fashion. Note that geartypes with
        # multiple supertypes will appear multiple times.
        choice_map = {}
        for i, choice in enumerate(choices_iter):
            # TODO don't assume choice[0] is an id for a GearType?
            geartype = GearType.objects.get(id=choice[0])
            geartype.order = i
            # TODO make use of geartype.order in the ordering
            choice_map[geartype] = choice
        
        def make_checkbox_list(geartypes, id_suffix=u'', final_attrs=final_attrs):
            checkboxes = []
            
            this_list = []
            for i, geartype in enumerate(geartypes):
                this_box = []
                if geartype in choice_map.keys():
                    (option_value, option_label) = choice_map[geartype]
                    # If an ID attribute was given, add a numeric index as a 
                    # suffix, so that the checkboxes don't all have the same ID 
                    # attribute.
                    if has_id:
                        final_attrs = dict(final_attrs, id='%s_%s_%s' % (attrs['id'], id_suffix, i))
                        label_for = u' for="%s"' % final_attrs['id']
                    else:
                        label_for = ''
                    
                    cb = forms.widgets.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
                    option_value = force_unicode(option_value)
                    rendered_cb = cb.render(name, option_value)
                    option_label = conditional_escape(force_unicode(option_label))
                    this_box.append(u'<label%s>%s %s</label>' % (label_for, rendered_cb, option_label))
                    
                sub_boxes = make_checkbox_list(geartype.subtypes.all(), id_suffix=i)
                if this_box or sub_boxes:
                    this_list.append(u'<li>%s' % '\n'.join(this_box))
                    this_list.append(u'%s' % sub_boxes)
                    this_list.append(u'</li>')
            
            if set(geartypes) & set(choice_map.keys()):
                checkboxes.append(u'<ul>')
                checkboxes.append(u'\n'.join(this_list))
                checkboxes.append(u'</ul>')
            
            return u'\n'.join(checkboxes)
            
        return mark_safe(make_checkbox_list(GearType.roots.all()))
    
class EntanglementForm(forms.ModelForm):
    
    _f = Entanglement._meta.get_field('gear_types')
    gear_types = forms.ModelMultipleChoiceField(
        queryset= GearType.objects.all(),
        required= _f.blank != True,
        help_text= 'selecting a type implies the ones above it in the hierarchy',
        label= _f.verbose_name.capitalize(),
        widget= GearTypeWidget
    )
    
    class Meta:
        model = Entanglement

class ShipstrikeForm(forms.ModelForm):
    
    class Meta:
        model = Shipstrike

class CaseTypeForm(forms.Form):
    '''\
    An form with the extra case-type field needed when creating new cases.
    '''
    
    # TODO get this info from the models.py
    type_names = (
        ('e', 'entanglement'),
        ('s', 'shipstrike'),
    )
    case_type = forms.ChoiceField(choices=type_names)
    # type_models's keys should be values of the case_type field
    type_models = {
        'e': Entanglement,
        's': Shipstrike,
    }
    type_forms = {
        'e': EntanglementForm,
        's': ShipstrikeForm,
    }

class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):
    '''\
    This class merely handles commonalities between the different observation
    types.
    '''

    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = Observation._meta.get_field('taxon')
    taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    observer_on_vessel = forms.BooleanField(
        required= False,
        help_text= "Was the observer on a vessel?"
    )
    new_reporter = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('none', 'no contact info for the reporter'),
        ),
        initial= 'none',
        required= False,
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the reporter?",
        # help_text isn't really necessary; the choices are self-explanitory
    )
    new_observer = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('reporter', 'same contact info as reporter'),
            ('none', 'no contact info for the observer'),
        ),
        initial= 'none',
        required= False,
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the observer?",
        # help_text isn't really necessary; the choices are self-explanitory
    )

    class Meta:
        model = Observation
        # the case for a new observation is set by the view. The one-to-one 
        # relations shouldn't be shown.
        exclude = ('case', 'location', 'report_datetime', 'observation_datetime', 'observer_vessel') 
observation_forms['Case'] = ObservationForm

class EntanglementObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

observation_forms['Entanglement'] = EntanglementObservationForm


class ShipstrikeObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = ShipstrikeObservation

observation_forms['Shipstrike'] = ShipstrikeObservationForm


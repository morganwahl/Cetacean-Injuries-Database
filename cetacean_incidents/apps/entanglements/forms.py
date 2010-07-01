from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.vessels.forms import VesselInfoForm
from cetacean_incidents.apps.incidents.models import Animal, Case, Observation
from cetacean_incidents.apps.incidents.forms import ObservationForm, case_form_classes, observation_forms

from models import Entanglement, EntanglementObservation, GearType, GearOwner

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
        exclude = ('gear_owner_info')

# TODO better way of tracking this
case_form_classes['Entanglement'] = EntanglementForm

class EntanglementObservationForm(ObservationForm):
    
    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

# TODO better way of tracking this
observation_forms['Entanglement'] = EntanglementObservationForm

class GearOwnerForm(forms.ModelForm):
    
    date_set_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'date gear was set is known',
        help_text= "check even if just the year is known"
    )
    
    location_set_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'location gear was set is known',
        help_text= "check even if just a vague location is known",
    )
    
    date_lost_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'date gear went missing is known',
        help_text= "check even if just the year is known"
    )
    
    class Meta:
        model = GearOwner
        exclude = ('case', 'date_gear_set', 'location_gear_set', 'date_gear_missing')


from copy import copy

from django.db import models
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.entanglements.models import Entanglement

from cetacean_incidents.apps.generic_templates.templatetags.generic_field_display import (
    display_cell,
    display_yesno_cell,
    display_animal_length_cell,
)

register = template.Library()

@register.simple_tag
def display_merge_row(destination, source, merge_form, field_name, cell_template_name=None, cell_kwargs={}, template='display_merge_row.html'):
    if isinstance(destination._meta.get_field(field_name), models.ManyToManyField):
        # comparing m2m fields is a little more complicated
        # unsaved instances may not have PKs yet
        if not destination.pk:
            destination_value = tuple()
        else:
            destination_value = getattr(destination, field_name)
    else:
        destination_value = getattr(destination, field_name)
    # the source may not have all the fields of the destination
    try:
        if isinstance(source._meta.get_field(field_name), models.ManyToManyField):
            # comparing m2m fields is a little more complicated
            # unsaved instances may not have PKs yet
            if not source.pk:
                source_value = tuple()
            else:
                source_value = getattr(source, field_name)
        else:
            source_value = getattr(source, field_name)
        in_source = True
    except models.fields.FieldDoesNotExist:
        in_source = False
    
    if in_source:
        if isinstance(destination_value, models.Manager):
            def _pks_set(manager):
                return set(manager.values_list('pk', flat=True))
            if isinstance(source_value, models.Manager):
                differ = not bool(_pks_set(destination_value) == _pks_set(source_value))
            else:
                differ = not bool(_pks_set(destination_value) == set(source_value))
        else:
            differ = not bool(destination_value == source_value)
    else:
        differ = None
    
    if isinstance(cell_kwargs, tuple):
        destination_kwargs, source_kwargs = cell_kwargs
    else:
        destination_kwargs, source_kwargs = map(copy, (cell_kwargs, cell_kwargs))

    destination_cell = display_cell(destination, field_name, cell_template_name, **destination_kwargs)

    if in_source:
        source_cell = display_cell(source, field_name, cell_template_name, **source_kwargs)
    else:
        source_cell = mark_safe(u'<td class="added"><i>no field</i></td>')
    
    return render_to_string(
        template,
        {
            'differ': differ,
            'in_source': in_source,
            'destination_cell': destination_cell,
            'source_cell': source_cell,
            'field': merge_form[field_name],
        },
    )

@register.simple_tag
def display_defined_merge_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='chosen_cell', cell_kwargs={}, template='display_defined_merge_row.html')

@register.simple_tag
def display_merge_yesunk_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='yesunk_cell')

@register.simple_tag
def display_merge_yesnounk_row(destination, source, merge_form, field_name, choices="yes,no,unknown"):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='yesnounk_cell', cell_kwargs={'choices': choices})

@register.simple_tag
def display_merge_chosen_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='chosen_cell')

@register.simple_tag
def display_merge_taxon_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='taxon_cell', cell_kwargs={'link': False})

@register.simple_tag
def display_merge_gender_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='gender_cell')

@register.simple_tag
def display_merge_geartypes_row(destination, source, merge_form, field_name):
    return display_merge_row(
        destination,
        source,
        merge_form,
        field_name,
        cell_template_name= 'geartypes_cell',
        cell_kwargs= (
            {'implied': destination.implied_gear_types},
            {'implied': source.implied_gear_types} if isinstance(source, Entanglement) else {},
        )
    )

@register.simple_tag
def display_merge_list_row(destination, source, merge_form, field_name):
    return display_merge_row(
        destination,
        source,
        merge_form,
        field_name,
        cell_template_name= 'list_cell',
    )

@register.simple_tag
def display_merge_animal_length_row(destination, source, merge_form, form_field_name, length_field_name, sigdigs_field_name):
    
    destination_value = [None, None]
    source_value = [None, None]
    in_source = [False, False]
    differ = False
    destination_cell = [None, None]
    source_cell = [None, None]
    # the source may not have all the fields of the destination
    for i, f in enumerate((length_field_name, sigdigs_field_name)):
        destination_value[i] = getattr(destination, f)
        try:
            source_value[i] = getattr(source, f)
            in_source[i] = True
        except AttributeError:
            pass
    
        if in_source[i]:
            differ |= not bool(destination_value[i] == source_value[i])
    
    destination_cell[0] = display_animal_length_cell(destination, length_field_name, destination_value[1])
    if in_source[0]:
        source_cell[0] = display_animal_length_cell(source, length_field_name, source_value[1])
    else:
        source_cell[0] = mark_safe(u'<td class="added"><i>no field</i></td>')

    destination_cell[1] = display_cell(destination, f)
    if in_source[1]:
        source_cell[1] = display_cell(source, f)
    else:
        source_cell[1] = mark_safe(u'<td class="added"><i>no field</i></td>')
    
    return render_to_string(
        'display_animal_length_merge_row.html',
        {
            'differ': differ,
            'in_source': in_source,
            'destination_cell': destination_cell,
            'source_cell': source_cell,
            'field': merge_form[form_field_name],
        },
    )


@register.simple_tag
def display_o2o_merge_row(destination, source, merge_form, o2o_field_name, has_o2o_field_name):
    destination_value = getattr(destination, o2o_field_name)
    # the source may not have all the fields of the destination
    try:
        source_value = getattr(source, o2o_field_name)
        in_source = True
    except AttributeError:
        in_source = False
    
    if in_source:
        has_differ = not bool(destination_value) == bool(source_value)
    else:
        has_differ = None
    
    has_destination_cell = display_yesno_cell(destination, o2o_field_name)
    if in_source:
        has_source_cell = display_yesno_cell(source, o2o_field_name)
    else:
        has_source_cell = mark_safe(u'<td class="added"><i>no field</i></td>')
    
    return render_to_string(
        'display_o2o_merge_row.html',
        {
            'has_differ': has_differ,
            'in_source': in_source,
            'has_destination_cell': has_destination_cell,
            'has_source_cell': has_source_cell,
            'has_field': merge_form[has_o2o_field_name],
            'subform': merge_form.subforms[o2o_field_name],
        },
    )

@register.simple_tag
def display_observationextension_merge_row(destination, source, merge_form, oe_field_name):
    if not oe_field_name in merge_form.subforms.keys():
        return 
    
    return render_to_string(
        'display_oe_merge_row.html',
        {
            'subform': merge_form.subforms[oe_field_name],
        },
    )

@register.simple_tag
def display_gear_body_location_merge_row(destination, source, merge_form):
    
    differ = not bool(destination.get_gear_body_locations_dict() == source.get_gear_body_locations_dict())
    
    return render_to_string(
        'display_gear_body_location_merge_row.html',
        {
            'differ': differ,
            'destination': destination,
            'source': source,
            'merge_form': merge_form,
        }
    )


from copy import copy

from django.db import models
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.entanglements.models import Entanglement

from cetacean_incidents.apps.generic_templates.templatetags.generic_field_display import display_cell

register = template.Library()

@register.simple_tag
def display_merge_row(destination, source, merge_form, field_name, cell_template_name=None, cell_kwargs={}):
    # comparing m2m fields is a little more complicated
    destination_value = getattr(destination, field_name)
    # the source may not have all the fields of the destination
    try:
        source_value = getattr(source, field_name)
        in_source = True
    except AttributeError:
        in_source = False
    
    if in_source:
        if isinstance(destination_value, models.Manager):
            def _pks_set(manager):
                return set(manager.values_list('pk', flat=True))
            differ = not bool(_pks_set(destination_value) == _pks_set(source_value))
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
        'display_merge_row.html',
        {
            'differ': differ,
            'in_source': in_source,
            'destination_cell': destination_cell,
            'source_cell': source_cell,
            'field': merge_form[field_name],
        },
    )

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


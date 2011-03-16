from django import template
from django.template.loader import render_to_string

from cetacean_incidents.apps.generic_templates.templatetags.generic_field_display import display_cell

register = template.Library()

@register.simple_tag
def display_merge_row(destination, source, merge_form, field_name, cell_template_name=None, cell_kwargs={}):
    differ = not bool(getattr(destination, field_name) == getattr(source, field_name))
    destination_cell = display_cell(destination, field_name, cell_template_name, **cell_kwargs)
    source_cell = display_cell(source, field_name, cell_template_name, **cell_kwargs)
    
    return render_to_string(
        'display_merge_row.html',
        {
            'differ': differ,
            'destination_cell': destination_cell,
            'source_cell': source_cell,
            'field': merge_form[field_name],
        },
    )

@register.simple_tag
def display_merge_yesnounk_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='yesunk_cell')

@register.simple_tag
def display_merge_yesunk_row(destination, source, merge_form, field_name, choices="yes,no,unknown"):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='yesnounk_cell', cell_kwargs={'choices': choices})

@register.simple_tag
def display_merge_taxon_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='taxon_cell', cell_kwargs={'link': False})

@register.simple_tag
def display_merge_gender_row(destination, source, merge_form, field_name):
    return display_merge_row(destination, source, merge_form, field_name, cell_template_name='gender_cell')


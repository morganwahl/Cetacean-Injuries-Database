from django import template
from django.template.loader import render_to_string

from django.db import models

register = template.Library()

@register.simple_tag
def display_row(instance, fieldname, label=None, template=None):
    '''\
    Given an instance of a django Model and a name of one of it's fields,
    display it as a table row
    '''
    
    field = instance._meta.get_field(fieldname)
    
    if label is None:
        label = field.verbose_name
    
    value = instance.__getattribute__(fieldname)
    
    if template is None:
        template = 'generic_templates/display_row.html'
        if isinstance(field, models.TextField):
            template = 'generic_templates/display_bigtext_row.html'
    
    return render_to_string(template, {
        'label': label,
        'value': value,
    })

@register.simple_tag
def display_simple_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'generic_templates/display_row.html')

@register.simple_tag
def display_bigtext_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'generic_templates/display_bigtext_row.html')

@register.simple_tag
def display_set_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'generic_templates/display_set_row.html')

@register.simple_tag
def display_yesunk_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'generic_templates/display_yesunk_row.html')


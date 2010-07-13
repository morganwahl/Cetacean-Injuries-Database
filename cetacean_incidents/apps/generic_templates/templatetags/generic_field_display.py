from django import template
from django.template.loader import render_to_string

from django.db import models

register = template.Library()

@register.simple_tag
def display_row(instance, fieldname, label=None, template_name=None, extra_context={}):
    '''\
    Given an instance of a django Model and a name of one of it's fields,
    display it as a table row
    '''
    
    context = {}
    
    field = instance._meta.get_field(fieldname)
    
    if label is None:
        label = field.verbose_name
    context['label'] = label
    
    context['value'] = instance.__getattribute__(fieldname)
    
    if template_name is None:
        template_name = 'row'
        if isinstance(field, models.TextField):
            template_name = 'bigtext_row'
    
    context.update(extra_context)
    
    return render_to_string('generic_templates/display_%s.html' % template_name, context)

@register.simple_tag
def display_simple_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'row')

@register.simple_tag
def display_bigtext_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'bigtext_row')

@register.simple_tag
def display_set_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'set_row')

@register.simple_tag
def display_yesunk_row(instance, fieldname, label=None):
    return display_row(instance, fieldname, label, 'yesunk_row')

@register.simple_tag
def display_yesnounk_row(instance, fieldname, label=None, choices= "yes,no,unknown"):
    return display_row(instance, fieldname, label, 'yesnounk_row', extra_context={'choices': choices})

def display_div(instance, fieldname, label=None, template_name=None):
    if template_name is None:
        template_name = 'div'
    return display_row(instance, fieldname, label, template_name) 

@register.simple_tag
def display_unlabeled_bigtext_div(instance, fieldname, label=None, choices= "yes,no,unknown"):
    return display_div(instance, fieldname, label, 'unlabeled_bigtext_div')


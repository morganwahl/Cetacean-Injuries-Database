from django.db import models
from django import template
from django.template.loader import render_to_string

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

register = template.Library()

@register.simple_tag
def display_cell(instance, fieldname, template_name=None, **kwargs):
    context = {}
    
    field = instance._meta.get_field(fieldname)
    
    context['value'] = getattr(instance, fieldname)
    display_func = getattr(instance, 'get_' + fieldname + '_display', None)
    if display_func:
        context['value_display'] = display_func()
    
    if template_name is None:
        template_name = 'cell'
        if isinstance(field, models.TextField):
            template_name = 'bigtext_cell'
    
    context.update(kwargs)
    
    return render_to_string('generic_templates/display_%s.html' % template_name, context)

@register.simple_tag
def display_yesunk_cell(instance, fieldname, **kwargs):
    return display_cell(instance, fieldname, 'yesunk_cell', **kwargs)

@register.simple_tag
def display_yesnounk_cell(instance, fieldname, choices="yes,no,unknown", **kwargs):
    kwargs.update({'choices': choices})
    return display_cell(instance, fieldname, 'yesnounk_cell', **kwargs)

@register.simple_tag
def display_bigtext_cell(instance, fieldname, **kwargs):
    return display_cell(instance, fieldname, 'bigtext_cell', **kwargs)

@register.simple_tag
def display_chosen_cell(instance, fieldname, **kwargs):
    return display_cell(instance, fieldname, 'chosen_cell', **kwargs)

@register.simple_tag
def display_taxon_cell(instance, fieldname, link=True, probable=None, **kwargs):
    kwargs.update({'link': link})
    if not probable is None:
        kwargs.update({'probable': probable})
    return display_cell(instance, fieldname, 'taxon_cell', **kwargs)

@register.simple_tag
def display_gender_cell(instance, fieldname, probable=None, **kwargs):
    if not probable is None:
        kwargs.update({'probable': probable})
    return display_cell(instance, fieldname, 'gender_cell', **kwargs)

@register.simple_tag
def display_geartype_cell(instance, fieldname, implied=None, **kwargs):
    if not implied is None:
        kwargs['implied'] = implied
    return display_cell(instance, fieldname, 'geartype_row', **kwargs)

@register.simple_tag
def display_row(instance, fieldname, label=None, template_name=None, **kwargs):
    '''\
    Given an instance of a django Model and a name of one of it's fields,
    display it as a table row. If template_name is None, the template_name will 
    be automatically picked based on the field type. If label is None, the label
    will be the field's verbose_name. Any additional keyword args will added to 
    the template's context.
    '''
    
    context = {}
    
    field = instance._meta.get_field(fieldname)
    
    if label is None:
        label = field.verbose_name
    context['label'] = label
    
    context['value'] = getattr(instance, fieldname)
    display_func = getattr(instance, 'get_' + fieldname + '_display', None)
    if display_func:
        context['value_display'] = display_func()
    
    if template_name is None:
        template_name = 'row'
        if isinstance(field, models.TextField):
            template_name = 'bigtext_row'
        if isinstance(field, UncertainDateTimeField):
            template_name = 'uncertain_datetime_row'
            context['value'] = context['value'].to_unicode(unknown_char=None, seconds=False)
    
    context.update(kwargs)
    
    return render_to_string('generic_templates/display_%s.html' % template_name, context)

@register.simple_tag
def display_simple_row(instance, fieldname, label=None, **kwargs):
    return display_row(instance, fieldname, label, 'row', **kwargs)

@register.simple_tag
def display_bigtext_row(instance, fieldname, label=None, **kwargs):
    return display_row(instance, fieldname, label, 'bigtext_row', **kwargs)

@register.simple_tag
def display_set_row(instance, fieldname, label=None, **kwargs):
    return display_row(instance, fieldname, label, 'set_row', **kwargs)

@register.simple_tag
def display_yesunk_row(instance, fieldname, label=None, **kwargs):
    return display_row(instance, fieldname, label, 'yesunk_row', **kwargs)

@register.simple_tag
def display_yesnounk_row(instance, fieldname, label=None, choices= "yes,no,unknown", **kwargs): 
    kwargs.update({'choices': choices})
    return display_row(instance, fieldname, label, 'yesnounk_row', **kwargs)

@register.simple_tag
def display_chosen_row(instance, fieldname, label=None, **kwargs):
    return display_row(instance, fieldname, label, 'chosen_row', **kwargs)

@register.simple_tag
def display_taxon_row(instance, fieldname, probable=None, link=True, label=None, **kwargs):
    kwargs.update({'link': link})
    if not probable is None:
        kwargs.update({'probable': probable})
    return display_row(instance, fieldname, label, 'taxon_row', **kwargs)

@register.simple_tag
def display_gender_row(instance, fieldname, probable=None, label=None, **kwargs):
    if not probable is None:
        kwargs.update({'probable': probable})
    return display_row(instance, fieldname, label, 'gender_row', **kwargs)

@register.simple_tag
def display_geartype_row(instance, fieldname, implied=None, label=None, **kwargs):
    if not implied is None:
        kwargs['implied'] = implied
    return display_row(instance, fieldname, label, 'geartype_row', **kwargs)

@register.simple_tag
def display_div(instance, fieldname, label=None, template_name=None, colon=True, **kwargs):
    if template_name is None:
        template_name = 'div'
    kwargs.update({'colon': colon})
    return display_row(instance, fieldname, label, template_name, **kwargs) 

@register.simple_tag
def display_bigtext_div(instance, fieldname, label=None, **kwargs):
    return display_div(instance, fieldname, label, 'bigtext_div', **kwargs)

@register.simple_tag
def display_unlabeled_bigtext_div(instance, fieldname, label=None, **kwargs):
    return display_div(instance, fieldname, label, 'unlabeled_bigtext_div', **kwargs)

@register.simple_tag
def display_yesnounk_div(instance, fieldname, label=None, choices= "yes,no,unknown", **kwargs):
    kwargs.update({'choices': choices})
    return display_div(instance, fieldname, label, 'yesnounk_div', colon=False, **kwargs)

@register.simple_tag
def display_chosen_div(instance, fieldname, label=None, **kwargs):
    return display_div(instance, fieldname, label, 'chosen_div', **kwargs)

@register.simple_tag
def display_geartypes_div(instance, fieldname, implied=None, label=None, **kwargs):
    if not implied is None:
        kwargs['implied'] = implied
    return display_div(instance, fieldname, label, 'geartypes_div', **kwargs)


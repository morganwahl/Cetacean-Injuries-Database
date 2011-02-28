from django import template

from cetacean_incidents.apps.incidents.models import Case

from django.utils.safestring import mark_safe
from django.conf import settings

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('animal_link.html')
def animal_link(animal, block=""):
    '''\
    Returns the link HTML for an animal.
    '''
    
    # get any NMFS IDs for it's cases, since these are often used as ersatz 
    # animal IDs
    
    # avoid circular imports
    from cetacean_incidents.apps.strandings_import.csv_import import IMPORT_TAGS
    from cetacean_incidents.apps.tags.models import Tag
    needs_review = bool(Tag.objects.filter(entry=animal, tag_text__in=IMPORT_TAGS))

    return {
        'animal': animal,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
        'animal_display': animal_display(animal, block),
    }

@register.simple_tag
def animal_display(animal, block=""):
    return animal_display_inline(animal) if not block else animal_display_block(animal)

def animal_display_inline(animal):
    '''\
    Inline HTML for an animal.
    '''
    
    field_number_html = u""
    if animal.field_number:
        field_number_html = animal_field_number_display(animal.field_number)
    
    names_html = u""
    names = animal.names
    if names:
        names_html = animal_names_display(animal.names)
        
    padding_html = ''
    if field_number_html and names_html:
        padding_html = ', '

    fallback_html = ''
    if not (field_number_html or names_html):
        fallback_html = u"""<span style="font-style: italic;">%s</span>""" % animal
    
    return mark_safe(field_number_html + padding_html + names_html + fallback_html)

def animal_display_block(animal):
    '''\
    Block HTML for an animal.
    '''
    
    names, field_number = animal.names, animal.field_number

    if (names and field_number) or len(names) > 1:
        result = u"""<ul style="margin: 0;">"""
        if field_number:
            result += u"""<li style="margin-left: 0; list-style-type: none;">%s</li>""" % animal_field_number_display(field_number)
        for n in names:
            if field_number:
                indent = 1
            else:
                indent = 0
            result += u"""<li style="margin-left: %dem; list-style-type: none;">%s</li>""" % (indent, animal_name_display(n))
        result += u"""</ul>"""
    else:
        result = u"""<div>%s</div>""" % animal_display_inline(animal)
    
    return mark_safe(result)

@register.simple_tag
def animal_names_display(names, block=""):
    if not names:
        return "<i>none</i>"
    if block and len(names) > 1:
        result = u"""<ul style="margin: 0;">"""
        for n in names:
            result += u"""<li style="margin-left: 0em; list-style-type: none;">%s</li>""" % animal_name_display(n)
        result += u"""</ul>"""
        return result
    else:
        return ', '.join(map(animal_name_display, names))

def animal_name_display(name):
    return u"""<span title="one of the the animal's name(s)">\u201c%s\u201d</span>""" % name

@register.simple_tag
def animal_field_number_display(field_number):
    if field_number:
        return u"""<span title="the animal's field number" style="font-weight: bold;">%s</span>""" % field_number
    else:
        return u"""<i>no field number has been assigned to this animal yet</i>"""

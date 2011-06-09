from django import template

register = template.Library()

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

@register.simple_tag
def animal_name_display(name):
    return u"""<span title="one of the the animal's name(s)">\u201c%s\u201d</span>""" % name

@register.simple_tag
def animal_field_number_display(field_number):
    if field_number:
        return u"""<span title="the animal's field number" style="font-weight: bold;">%s</span>""" % field_number
    else:
        return u"""<i>no field number has been assigned to this animal yet</i>"""


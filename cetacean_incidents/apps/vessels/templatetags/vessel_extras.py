from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.countries.utils.isoflag import iso_flag

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('flag_icon.html')
def flag_icon(country):
    '''\
    Returns the HTML img tag for a flag icon for a given Country.
    '''
    return {
        'flag_url': iso_flag(country.iso),
        'country_name': unicode(country),
    }

@register.inclusion_tag('vessels/display_boatname_row.html')
def display_boatname_row(vessel):
    label = ''
    value = ''
    
    if vessel.name:
        label = 'name'
        value = vessel.name
    if vessel.name and (vessel.home_port or vessel.flag):
        label += u' \u2014 '
        value += u' \u2014 '
    if vessel.flag:
        label += 'flag'
        flag_html = render_to_string('flag_icon.html', flag_icon(vessel.flag))
        value += flag_html
    if vessel.flag and vessel.home_port:
        label += ' and '
        value += ' '
    if vessel.home_port:
        label += 'home port'
        value += vessel.home_port

    return {
        'label': label,
        'value': mark_safe(value),
    }


from django import template
from django.template.loader import render_to_string

from cetacean_incidents.apps.countries.utils.isoflag import iso_flag
from cetacean_incidents.apps.generic_templates.templatetags.generic_field_display import display_row

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
    labels = []
    values = []
    if vessel.name:
        labels.append('name')
        values.append(vessel.name)
    if vessel.flag:
        labels.append('flag')
        flag_html = render_to_string('flag_icon.html', flag_icon(vessel.flag))
        values.append(flag_html)

    return {
        'labels': labels,
        'values': values,
    }


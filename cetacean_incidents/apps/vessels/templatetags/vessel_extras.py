from django import template

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


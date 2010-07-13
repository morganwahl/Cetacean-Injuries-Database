from django import template

from cetacean_incidents.apps.generic_templates.templatetags.generic_field_display import display_row

register = template.Library()

@register.inclusion_tag('locations/display_coord_dec_row.html')
def display_coord_dec_row(location, lat_or_lng):
    
    if lat_or_lng == 'lat':
        context = {
            'label': 'lat.',
            'coord': location.coords_pair[0],
        }
    elif lat_or_lng == 'lng':
        context = {
            'label': 'lng.',
            'coord': location.coords_pair[1],
        }
    
    return context

@register.inclusion_tag('locations/display_coord_dms_row.html')
def display_coord_dms_row(location, lat_or_lng):
    
    if lat_or_lng == 'lat':
        context = {
            'label': 'lat.',
            'coord': location.dms_coords_pair[0],
            'dirs': ('South', 'North'),
        }
    elif lat_or_lng == 'lng':
        context = {
            'label': 'lng.',
            'coord': location.dms_coords_pair[1],
            'dirs': ('West', 'East'),
        }
    
    return context


from urllib import urlencode, quote

from django import template
from django.conf import settings

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

@register.simple_tag
def map_url(obj, size=u'200x150'):
    '''\
    Returns a url of a map image with a marker or markers for the location
    indicated by the argument.
    
    Given a Location, uses location's coordinates.
    
    Given an Observation, uses the Observation's Location.
    
    Given a Case, uses all it's Observations.
    
    Given an Animal, uses all it's Observation.
    
    Given an iterable of any of the above, uses all of them.
    '''
    
    map_base = u'https://maps.google.com/maps/api/staticmap?'
    marker_base = u'http://chart.apis.google.com/chart?'
    
    from cetacean_incidents.apps.locations.models import Location

    if isinstance(obj, Location):
        return map_base + urlencode({
            'center': obj.coordinates,
            'zoom': 6,
            'size': size,
            'maptype': u'terrain',
            'markers': (u'size:small|color:yellow|%s' % obj.coordinates,),
            'sensor': u'false',
        }, doseq=True)
    
    from cetacean_incidents.apps.incidents.models import Observation

    if isinstance(obj, Observation):
        loc = obj.location
        marker_url = marker_base + urlencode({
            'chst': u'd_map_xpin_icon',
            'chld': u'pin|aquarium|ADDE63',
        })
        print marker_url
        map_url = map_base + urlencode({
            'center': loc.coordinates,
            'zoom': 6,
            'sensor': u'false',
            'language': settings.LANGUAGE_CODE,
            'maptype': u'terrain',
            'size': size,
            'markers': u'icon:%s|%s' % (marker_url, loc.coordinates),
        })
        print map_url
        return map_url
    
    raise NotImplementedError

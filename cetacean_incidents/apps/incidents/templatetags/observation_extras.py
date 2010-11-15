from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('observation_link.html')
def observation_link(observation):
    '''\
    Returns the link HTML for a observation.
    '''
    return {'observation': observation}
    
@register.simple_tag
def observation_datetime_display(dt):
    '''\
    Returns the HTML for displaying a UncertainDateTime from an Observation
    '''
    
    return dt.__unicode__(unknown_char=None, seconds=False)

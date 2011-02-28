from django import template
from django.utils.safestring import mark_safe
from django.conf import settings

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('observation_link.html')
def observation_link(observation):
    '''\
    Returns the link HTML for a observation.
    '''
    
    # avoid circular imports
    from cetacean_incidents.apps.strandings_import.csv_import import IMPORT_TAGS
    from cetacean_incidents.apps.tags.models import Tag
    needs_review = bool(Tag.objects.filter(entry=observation, tag_text__in=IMPORT_TAGS))

    return {
        'observation': observation,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
    }
    
@register.simple_tag
def date_observed_display(dt):
    '''\
    Returns the HTML for displaying a just the date of an UncertainDateTime
    from an Observation
    '''
    
    if dt:
        return dt.to_unicode(unknown_char=None, time=False)
    return ''

@register.simple_tag
def datetime_observed_display(dt):
    '''\
    Returns the HTML for displaying a UncertainDateTime from an Observation
    '''
    
    if dt:
        return dt.to_unicode(unknown_char=None, seconds=False)
    return ''


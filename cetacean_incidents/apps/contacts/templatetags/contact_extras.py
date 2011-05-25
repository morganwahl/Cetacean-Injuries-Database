from django.conf import settings
from django import template
from django.template import Context
from django.template.loader import get_template

from cetacean_incidents.apps.tags.models import Tag

register = template.Library()

@register.simple_tag
def contact_link(contact):
    '''\
    Returns the link HTML for a Contact.
    '''
    # avoid circular imports
    from cetacean_incidents.apps.csv_import import IMPORT_TAGS
    needs_review = bool(Tag.objects.filter(entry=contact, tag_text__in=IMPORT_TAGS))
    
    context = Context({
        'contact': contact,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
    })

    # TODO assumes the the
    # django.template.loaders.app_directories.load_template_source
    # is being used. (which is the default.)
    return get_template('contact_link.html').render(context)


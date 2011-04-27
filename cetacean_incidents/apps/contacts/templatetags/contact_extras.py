from django import template

register = template.Library()


# TODO assumes the the
# django.template.loaders.app_directories.load_template_source
# is being used. (which is the default.)
@register.inclusion_tag('contact_link.html')
def contact_link(contact):
    '''\
    Returns the link HTML for a Contact.
    '''
    return {'contact': contact}


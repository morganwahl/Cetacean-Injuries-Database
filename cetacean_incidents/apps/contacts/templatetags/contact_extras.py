from django import template

register = template.Library()

@register.inclusion_tag('contacts/contact_link.html')
def contact_link(contact):
    '''\
    Returns the link HTML for a Contact.
    '''
    return {'contact': contact}

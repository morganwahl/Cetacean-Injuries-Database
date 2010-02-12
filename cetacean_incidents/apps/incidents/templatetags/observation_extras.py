from django import template

register = template.Library()

@register.inclusion_tag('incidents/observation_link.html')
def observation_link(visit):
    '''\
    Returns the link HTML for a observation.
    '''
    return {'observation': observation}

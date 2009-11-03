from django import template

register = template.Library()

@register.inclusion_tag('incidents/visit_link.html')
def visit_link(visit):
    '''\
    Returns the link HTML for a visit.
    '''
    return {'visit': visit}

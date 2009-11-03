from django import template

register = template.Library()

@register.inclusion_tag('incidents/case_link.html')
def case_link(case):
    '''\
    Returns the link HTML for a case.
    '''
    return {'case': case}

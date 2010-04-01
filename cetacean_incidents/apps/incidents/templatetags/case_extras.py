from django import template

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('case_link.html')
def case_link(case):
    '''\
    Returns the link HTML for a case.
    '''
    return {'case': case}

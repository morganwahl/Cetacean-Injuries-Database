from django import template

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('observation_link.html')
def observation_link(observation):
    '''\
    Returns the link HTML for a observation.
    '''
    return {'observation': observation}

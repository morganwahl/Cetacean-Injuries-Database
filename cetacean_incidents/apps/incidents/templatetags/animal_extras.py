from django import template

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('animal_link.html')
def animal_link(animal):
    '''\
    Returns the link HTML for an animal.
    '''
    return {'animal': animal}

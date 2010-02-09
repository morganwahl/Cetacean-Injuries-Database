from django import template

register = template.Library()

@register.inclusion_tag('incidents/animal_link.html')
def animal_link(animal):
    '''\
    Returns the link HTML for an animal.
    '''
    return {'animal': animal}

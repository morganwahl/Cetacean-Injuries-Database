from django import template

from cetacean_incidents.apps.incidents.models import Case

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('animal_link.html')
def animal_link(animal):
    '''\
    Returns the link HTML for an animal.
    '''
    
    # get any NMFS IDs for it's cases, since these are often used as ersatz 
    # animal IDs
    
    return {
        'animal': animal,
        'nmfs_ids': Case.objects.filter(animal=animal).exclude(nmfs_id__isnull=True).exclude(nmfs_id='').values_list('nmfs_id', flat=True),
    }

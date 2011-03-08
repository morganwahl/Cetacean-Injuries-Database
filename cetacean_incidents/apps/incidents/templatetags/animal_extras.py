from django.conf import settings
from django.core.cache import cache
from django.db import models
from django import template
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.tags.models import Tag

from ..models import (
    Animal,
    Case,
)

register = template.Library()

@register.simple_tag
def animal_link(animal, block=False):
    '''\
    Returns the link HTML for an animal.
    '''
    
    cache_key = u'animal_link_%d' % animal.id
    if block:
        cache_key = cache_key + u'_block'

    cached = cache.get(cache_key)
    if cached:
        #print "cache hit!: %s" % cache_key
        return cached
    
    # get any NMFS IDs for it's cases, since these are often used as ersatz 
    # animal IDs
    
    # avoid circular imports
    from cetacean_incidents.apps.strandings_import.csv_import import IMPORT_TAGS
    needs_review = bool(Tag.objects.filter(entry=animal, tag_text__in=IMPORT_TAGS))
    
    context = Context({
        'animal': animal,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
        'animal_display': animal_display(animal, block),
    })
    
    # assumes the loader
    # django.template.loaders.app_directories.load_template_source is being
    # used, which is the default.
    template = get_template('animal_link.html')
    result = template.render(context)
    
    cache.set(cache_key, result, 7 * 24 * 3600)

    return result
        
@register.simple_tag
def animal_display(animal, block=False):

    cache_key = u'animal_display_%d' % animal.id
    if block:
        cache_key = cache_key + u'_block'

    cached = cache.get(cache_key)
    if cached:
        #print "cache hit!: %s" % cache_key
        return cached
    
    result = animal_display_inline(animal) if not block else animal_display_block(animal)
    
    cache.set(cache_key, result, 7 * 24 * 3600)

    return result

# remove stale cache entries
def _animal_post_save(sender, **kwargs):
    # sender should be Animal
    
    if kwargs['created']:
        return
    
    animal = kwargs['instance']
    # TODO we're repeating the cache_key above
    cache_keys = [
        u'animal_link_%d' % animal.id,
        u'animal_link_%d_block' % animal.id,
        u'animal_display_%d' % animal.id,
        u'animal_display_%d_block' % animal.id,
    ]
    #print "cache delete!: %s" % ', '.join(cache_keys)
    cache.delete_many(cache_keys)

models.signals.post_save.connect(
    sender= Animal,
    receiver= _animal_post_save,
    dispatch_uid= 'cache_clear__animal_extras__animal__post_save',
)

def _tag_post_save_or_post_delete(sender, **kwargs):
    # sender should be Tag
    
    tag = kwargs['instance']

    # avoid circular imports
    from cetacean_incidents.apps.strandings_import.csv_import import IMPORT_TAGS
    if not tag.tag_text in IMPORT_TAGS:
        return

    # we don't need to check if the entry is an animal, since if it isn't, it
    # won't have any cache entries. This assumes 
    # Animal.objects.filter(id=tag.entry_id).exists() is slower than 
    # cache.delete_many(cache_keys)
    # TODO we're repeating the cache_key above
    cache_keys = [
        u'animal_link_%d' % tag.entry_id,
        u'animal_link_%d_block' % tag.entry_id,
    ]
    #print "cache delete!: %s" % ', '.join(cache_keys)
    cache.delete_many(cache_keys)

models.signals.post_save.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__animal_extras__tag__post_save',
)
models.signals.post_delete.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__animal_extras__tag__post_delete',
)

def animal_display_inline(animal):
    '''\
    Inline HTML for an animal.
    '''
    
    field_number_html = u""
    if animal.field_number:
        field_number_html = animal_field_number_display(animal.field_number)
    
    names_html = u""
    names = animal.names
    if names:
        names_html = animal_names_display(animal.names)
        
    padding_html = ''
    if field_number_html and names_html:
        padding_html = ', '

    fallback_html = ''
    if not (field_number_html or names_html):
        fallback_html = u"""<span style="font-style: italic;">%s</span>""" % animal
    
    return mark_safe(field_number_html + padding_html + names_html + fallback_html)

def animal_display_block(animal):
    '''\
    Block HTML for an animal.
    '''
    
    names, field_number = animal.names, animal.field_number

    if (names and field_number) or len(names) > 1:
        result = u"""<ul style="margin: 0;">"""
        if field_number:
            result += u"""<li style="margin-left: 0; list-style-type: none;">%s</li>""" % animal_field_number_display(field_number)
        for n in names:
            if field_number:
                indent = 1
            else:
                indent = 0
            result += u"""<li style="margin-left: %dem; list-style-type: none;">%s</li>""" % (indent, animal_name_display(n))
        result += u"""</ul>"""
    else:
        result = u"""<div>%s</div>""" % animal_display_inline(animal)
    
    return mark_safe(result)

@register.simple_tag
def animal_names_display(names, block=""):
    if not names:
        return "<i>none</i>"
    if block and len(names) > 1:
        result = u"""<ul style="margin: 0;">"""
        for n in names:
            result += u"""<li style="margin-left: 0em; list-style-type: none;">%s</li>""" % animal_name_display(n)
        result += u"""</ul>"""
        return result
    else:
        return ', '.join(map(animal_name_display, names))

def animal_name_display(name):
    return u"""<span title="one of the the animal's name(s)">\u201c%s\u201d</span>""" % name

@register.simple_tag
def animal_field_number_display(field_number):
    if field_number:
        return u"""<span title="the animal's field number" style="font-weight: bold;">%s</span>""" % field_number
    else:
        return u"""<i>no field number has been assigned to this animal yet</i>"""

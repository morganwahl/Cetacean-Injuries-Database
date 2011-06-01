from django import template

from html_filter import html, CACHE_TIMEOUT

register = template.Library()

@register.filter
def link(obj, use_cache=None):
    '''\
    Given a model instance, return HTML for a link to that model, if it has a
    'get_absolute_url()' method.
    '''
    
    return html(obj, link=True, use_cache=use_cache)

@register.filter
def links(objs, use_cache=None):
    '''\
    Applies the 'link' filter to an iterable of model instance and returns an
    iterable of their link HTML.
    '''
    
    try:
        return map(lambda o: link(o, use_cache), objs)
    except TypeError:
        # if not iterable, just return a list with one link to whatever was
        # passed in
        return [link(objs, use_cache)]


from django.core.cache import cache
from django.db.models import Model
from django import template
from django.utils.safestring import mark_safe
from django.template.loader import select_template, get_template

register = template.Library()

CACHE_TIMEOUT = 7 * 24 * 3600

def cache_keys(obj):
    # TODO repeats the key definition in html()
    cache_key = u'%s__%s__%d__html' % (app_name, model_name, obj.id)
    return (cache_key, cache_key + '__link')

@register.filter
def html(obj, link=False, use_cache=None):
    '''\
    Given a model instance, return HTML an HTML representation of that model.
    '''
    
    if not isinstance(obj, Model):
        return unicode(obj)
    
    options = {}
    if hasattr(obj, 'get_html_options'):
        options = obj.get_html_options()
    
    if use_cache is None and 'use_cache' in options:
        use_cache = options['use_cache']
    
    # TODO caching requires and 'id' field
    if not hasattr(obj, 'id'):
        use_cache = False
    
    app_name = obj._meta.app_label
    model_name = obj._meta.object_name.lower()
    
    if use_cache:
        cache_key = u'%s__%s__%d__html' % (app_name, model_name, obj.id)
        if link:
            cache_key += '__link'
        cached = cache.get(cache_key)
        if cached:
            return mark_safe(cached)
    
    if 'template' in options:
        t = get_template(options['template'])
    else:
        # TODO we want to fall back to the default template included with this app;
        # how to make that explicit?
        template_names = [
            "%s/%s.html" % (app_name, model_name),
            'object.html',
        ]
        t = select_template(template_names)
    
    context = template.Context({
        'object': obj,
    })
    
    if link:
        if hasattr(obj, 'get_absolute_url'):
            context['url'] = obj.get_absolute_url()

    if 'context' in options:
        context.update(options['context'])
    
    html = t.render(context)
    # strip whitespace from the ends
    html = html.strip()
    
    if use_cache:
        cache.set(cache_key, html, CACHE_TIMEOUT)
    
    return mark_safe(html)

@register.filter
def htmls(objs, use_cache=None):
    '''\
    Applies the 'html' filter to an iterable of model instance and returns an
    iterable of their HTML representation.
    '''
    
    try:
        return map(lambda o: html(o, use_cache), objs)
    except TypeError:
        # if not iterable, just return a list with one string for whatever was
        # passed in
        return [html(objs, use_cache)]


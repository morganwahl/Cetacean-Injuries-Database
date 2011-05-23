from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django import forms
from django import template
from django.template import Context
from django.template.loader import get_template

from cetacean_incidents.apps.tags.models import Tag

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

from ..models import (
    Case,
    Observation,
)

register = template.Library()

@register.simple_tag
def case_link(case):
    '''\
    Returns the link HTML for a case.
    '''

    cache_key = u'case_link_%d' % case.id

    cached = cache.get(cache_key)
    if cached:
        return cached

    # avoid circular imports
    from cetacean_incidents.apps.csv_import import IMPORT_TAGS
    needs_review = bool(Tag.objects.filter(entry=case, tag_text__in=IMPORT_TAGS))

    context = Context({
        'case': case,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
    })
    
    # assumes the loader
    # django.template.loaders.app_directories.load_template_source is being used, 
    # which is the default.
    template = get_template('case_link.html')
    result = template.render(context)
    
    cache.set(cache_key, result, 7 * 24 * 3600)
    
    return result

# remove stale cache entries
def _case_post_save(sender, **kwargs):
    # sender should be Case
    
    if kwargs['created']:
        return
    
    case = kwargs['instance']
    # TODO we're repeating the cache_key above
    cache_key = u'case_link_%d' % case.id
    cache.delete(cache_key)
        
models.signals.post_save.connect(
    sender= Case,
    receiver= _case_post_save,
    dispatch_uid= 'cache_clear__case_extras__case__post_save',
)

def _tag_post_save_or_post_delete(sender, **kwargs):
    # sender should be Tag
    
    tag = kwargs['instance']

    # avoid circular imports
    from cetacean_incidents.apps.csv_import import IMPORT_TAGS
    if not tag.tag_text in IMPORT_TAGS:
        return

    # we don't need to check if the entry is a case, since if it isn't, it
    # won't have any cache entries. This assumes 
    # Case.objects.filter(id=tag.entry_id).exists() is slower than 
    # cache.delete_many(cache_keys)
    # TODO we're repeating the cache_key above
    cache_key = u'case_link_%d' % tag.entry_id
    cache.delete(cache_key)

models.signals.post_save.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__case_extras__tag__post_save',
)
models.signals.post_delete.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__case_extras__tag__post_delete',
)

@register.inclusion_tag('case_years_link.html')
def case_years_link():
    return {'years_form': YearsForm()}

_MIN_YEAR = 1500
class YearsForm(forms.Form):
    '''\
    Just a drop-down of years that have observations.
    '''

    @staticmethod
    def _get_year_choices():
        # datetime_observed, not datetime_reported
        return map(lambda y: (y, unicode(y)), reversed(sorted(list(set(map(
            # values_list returns the raw values, not UncertainDateTimes
            lambda dt: UncertainDateTime.from_sortkey(dt).year,
            Observation.objects.filter(
                datetime_observed__gte=unicode(_MIN_YEAR),
            ).values_list('datetime_observed', flat=True)
        ))))))

    def __init__(self, *args, **kwargs):
        super(YearsForm, self).__init__(*args, **kwargs)
        
        self.fields['year'] = forms.TypedChoiceField(
            choices= YearsForm._get_year_choices(),
            coerce= int,
            required= True,
        )
        

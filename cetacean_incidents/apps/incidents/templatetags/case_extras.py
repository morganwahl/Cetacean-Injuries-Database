from datetime import date

from django import template

from django.conf import settings
from django import forms

from ..models import Observation
from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

register = template.Library()

# assumes the the django.template.loaders.app_directories.load_template_source 
# is being used, which is the default.
@register.inclusion_tag('case_link.html')
def case_link(case):
    '''\
    Returns the link HTML for a case.
    '''

    # avoid circular imports
    from cetacean_incidents.apps.strandings_import.csv_import import IMPORT_TAGS
    from cetacean_incidents.apps.tags.models import Tag
    needs_review = bool(Tag.objects.filter(entry=case, tag_text__in=IMPORT_TAGS))

    return {
        'case': case,
        'needs_review': needs_review,
        'media_url': settings.MEDIA_URL,
    }

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
        

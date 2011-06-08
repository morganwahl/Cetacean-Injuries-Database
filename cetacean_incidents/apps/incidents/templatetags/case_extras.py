from django.core.cache import cache
from django import forms
from django import template

from ..models import Observation

register = template.Library()

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
        considered_obs = Observation.objects.filter(datetime_observed__gte=unicode(_MIN_YEAR)).only('datetime_observed')
        lowest_year = considered_obs.order_by('datetime_observed')[0].datetime_observed.year
        highest_year = considered_obs.order_by('-datetime_observed')[0].datetime_observed.year
        return map(lambda y: (y, unicode(y)), reversed(range(lowest_year, highest_year + 1)))

    def __init__(self, *args, **kwargs):
        super(YearsForm, self).__init__(*args, **kwargs)
        
        self.fields['year'] = forms.TypedChoiceField(
            choices= YearsForm._get_year_choices(),
            coerce= int,
            required= True,
        )
        

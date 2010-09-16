from django.conf.urls.defaults import *
from models import Case, Observation, Animal
import views

animals_args = {
    'queryset': Animal.objects.all(),
    'template_object_name': 'animal',
}
cases_args = {
    'queryset': Case.objects.all().reverse(),
    'template_object_name': 'case',
}
observations_args = {
    'queryset': Observation.objects.all(),
    'template_object_name': 'observation',
}

urlpatterns = patterns('cetacean_incidents.generic_views',
    # TODO should be use reverse() or are hard-coded URLs OK when they're
    # defined in this very file?
    (r'^animals/$', 'redirect_to', {'url': 'search'}, 'all_animals'),
    (r'^animals/(?P<object_id>\d+)/$', 'object_detail', animals_args, 'animal_detail'),

    (r'^cases/$', 'redirect_to', {'url': 'search'}, 'all_cases'),

    (r'^observations/$', 'object_list', observations_args, 'all_observations'),
)
urlpatterns += patterns('',
    (r'^animals/create$', views.create_animal, {}, 'create_animal'),
    (r'^animals/(\d+)/edit$', views.edit_animal, {}, 'edit_animal'),
    (r'^animals/(\d+)/add_case$', views.add_case, {}, 'add_case'),
    (r'^animals/search$', views.animal_search, {}, 'animal_search'),
    url(r'^animals/search_json$', views.animal_search_json, name='animal_search_json'),

    (r'^cases/(\d+)/$', views.case_detail, {}, 'case_detail'),
    (r'^cases/create$', views.create_case, {}, 'create_case'),
    (r'^cases/(\d+)/edit$', views.edit_case, {}, 'edit_case'),
    (r'^cases/(\d+)/add_observation$', views.add_observation, {}, 'add_observation'),
    (r'^cases/(\d+)/merge_with/(\d+)$', views.merge_case, {}, 'merge_case'),
    (r'^cases/search$', views.case_search, {}, 'case_search'),
    (r'^cases/by_year/now$', views.cases_by_year, {}, 'cases_this_year'),
    (r'^cases/by_year/(\d+)/$', views.cases_by_year, {}, 'cases_by_year'),

    (r'^observations/(\d+)/$', views.observation_detail, {}, 'observation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_observation, {}, 'edit_observation'),
)

# for backwards compatibility on old /incidents/ URLs
urlpatterns += patterns('cetacean_incidents.apps.entanglements.views',
    (r'^entanglement_report_form/$', 'entanglement_report_form', {}, 'entanglement_report_form'),
)
urlpatterns += patterns('cetacean_incidents.apps.shipstrikes.views',
    (r'^shipstrike_report_form/$', 'shipstrike_report_form', {}, 'shipstrike_report_form'),
)


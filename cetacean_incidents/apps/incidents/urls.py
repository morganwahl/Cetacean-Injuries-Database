from django.conf.urls.defaults import *

from cetacean_incidents.views import new_case

from models import (
    Animal,
    Case,
    Observation,
)
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

    (r'^cases/$', 'redirect_to', {'url': 'search'}, 'all_cases'),

    (r'^observations/$', 'object_list', observations_args, 'all_observations'),
)
urlpatterns += patterns('',
    (r'^animals/(?P<animal_id>\d+)/$', views.animal_detail, {}, 'animal_detail'),
    (r'^animals/create$', views.create_animal, {}, 'create_animal'),
    (r'^animals/(\d+)/edit$', views.edit_animal, {}, 'edit_animal'),
    (r'^animals/(\d+)/add_case$', new_case, {}, 'add_case'),
    (r'^animals/(?P<destination_id>\d+)/merge$', views.animal_merge, {}, 'animal_merge'),
    (r'^animals/(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.animal_merge, {}, 'animal_merge'),
    (r'^animals/search$', views.animal_search, {}, 'animal_search'),
    url(r'^animals/search_json$', views.animal_search_json, name='animal_search_json'),

    (r'^cases/(\d+)/$', views.case_detail, {}, 'case_detail'),
    # TODO redirect to new_case? how do we get it's URL from within a URL conf?
    (r'^cases/create$', new_case, {}, 'create_case'),
    (r'^cases/(\d+)/edit$', views.edit_case, {}, 'edit_case'),
    (r'^cases/(\d+)/edit_sinm_popup$', views.edit_sinm_popup, {}, 'edit_sinm_popup'),
    (r'^cases/(?P<case_id>\d+)/change_animal$', views.edit_case_animal, {}, 'edit_case_animal'),
    (r'^cases/(?P<case_id>\d+)/add_observation$', views.add_observation, {}, 'add_observation'),
    (r'^cases/(?P<destination_id>\d+)/merge$', views.case_merge, {}, 'case_merge'),
    (r'^cases/(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.case_merge, {}, 'case_merge'),
    (r'^cases/search$', views.case_search, {}, 'case_search'),
    (r'^cases/reports/create/(?P<report_type>[^/]+)$', views.case_report_create, {}, 'case_report_create'),
    (r'^cases/reports/(\d+)/edit$', views.case_report_edit, {}, 'case_report_edit'),
    (r'^cases/by_year/now$', views.cases_by_year, {}, 'cases_this_year'),
    (r'^cases/by_year/$', views.cases_by_year, {}, 'cases_by_year_get'),
    (r'^cases/by_year/(\d+)/$', views.cases_by_year, {}, 'cases_by_year'),

    (r'^observations/(\d+)/$', views.observation_detail, {}, 'observation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_observation, {}, 'edit_observation'),
    (r'^observations/(?P<destination_id>\d+)/merge$', views.observation_merge, {}, 'observation_merge'),
    (r'^observations/(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.observation_merge, {}, 'observation_merge'),
    (r'^observations/search$', views.observation_search, {}, 'observation_search'),
    (r'^observations/by_year/now$', views.observations_by_year, {}, 'observations_this_year'),
    (r'^observations/by_year/$', views.observations_by_year, {}, 'observations_by_year_get'),
    (r'^observations/by_year/(\d+)/$', views.observations_by_year, {}, 'observations_by_year'),
)


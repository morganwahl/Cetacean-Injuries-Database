from django.conf.urls.defaults import *
from models import Case, Observation, Animal

from cetacean_incidents.views import new_case

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
    (r'^cases/(?P<case_id>\d+)/add_observation$', views.add_observation, {}, 'add_observation'),
    (r'^cases/(\d+)/add_document$', views.add_casedocument, {}, 'add_casedocument'),
    (r'^cases/search$', views.case_search, {}, 'case_search'),
    (r'^cases/by_year/now$', views.cases_by_year, {}, 'cases_this_year'),
    (r'^cases/by_year/(\d+)/$', views.cases_by_year, {}, 'cases_by_year'),

    (r'^observations/(\d+)/$', views.observation_detail, {}, 'observation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_observation, {}, 'edit_observation'),
    (r'^observations/(\d+)/add_document$', views.add_observationdocument, {}, 'add_observationdocument'),
)


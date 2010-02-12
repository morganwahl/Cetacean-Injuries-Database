from django.conf.urls.defaults import *
from models import Case, Observation, Animal
import views

animal_args = {
    'queryset': Animal.objects.all(),
    'template_object_name': 'animal',
}
cases_args = {
    'queryset': Case.objects.all(),
    'template_object_name': 'case',
}
observations_args = {
    'queryset': Observation.objects.all(),
    'template_object_name': 'observation',
}

urlpatterns = patterns('django.views.generic.list_detail',
    url(r'animals/^$', 'object_list', animal_args, name='animal_list'),
    url(r'animals/^(?P<object_id>\d+)/$', 'object_detail', animal_args, name='animal_detail'),
    (r'^cases/$', 'object_list', cases_args, 'all_cases'),
    (r'^cases/(?P<object_id>\d+)/$', 'object_detail', cases_args, 'case_detail'),
    (r'^observations/$', 'object_list', observations_args, 'all_observations'),
    (r'^observations/(?P<object_id>\d+)/$', 'object_detail', observations_args, 'observation_detail'),
)
urlpatterns += patterns('',
    (r'^cases/create$', views.create_case, {}, 'create_case'),
    (r'^cases/(\d+)/edit$', views.edit_case, {}, 'edit_case'), 
    (r'^cases/(\d+)/add_observation', views.add_observation, {}, 'add_observation'),
)

from django.conf.urls.defaults import *
from models import Case, Visit
import views

cases_args = {
    'queryset': Case.objects.all(),
    'template_object_name': 'case',
}
visits_args = {
    'queryset': Visit.objects.all(),
    'template_object_name': 'visit',
}
urlpatterns = patterns('django.views.generic.list_detail',
    (r'^cases/$', 'object_list', cases_args, 'all_cases'),
    (r'^cases/(?P<object_id>\d+)/$', 'object_detail', cases_args, 'case_detail'),
    (r'^visits/$', 'object_list', visits_args, 'all_visits'),
    (r'^visits/(?P<object_id>\d+)/$', 'object_detail', visits_args, 'visit_detail'),
)
urlpatterns += patterns('',
    (r'^cases/create$', views.create_case, {}, 'create_case'),
    (r'^cases/(\d+)/edit$', views.edit_case, {}, 'edit_case'), 
    (r'^cases/(\d+)/add_visit', views.add_visit, {}, 'add_visit'),
)

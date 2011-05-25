from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^observations$', views.import_observations_csv),
    (r'^strandings$', views.import_stranding_csv, {}, 'import_strandings'),
    (r'^review/$', views.review_imports, {}, 'review_imports'),
)


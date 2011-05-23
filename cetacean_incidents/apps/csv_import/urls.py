from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^strandings$', views.import_stranding_csv, {}, 'import_strandings'),
    (r'^review/$', views.review_imports, {}, 'review_imports'),
)


from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^$', views.import_csv, {}, 'import_strandings'),
    (r'^review/$', views.review_imports, {}, 'review_imports'),
)

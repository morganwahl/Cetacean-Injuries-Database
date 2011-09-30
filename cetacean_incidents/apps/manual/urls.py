from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^$', views.view_manuals, {}, 'view_manuals'),
    (r'^download$', views.download_manual, {}, 'download_manual'),
    (r'^(\d+)/download$', views.download_manual, {}, 'download_manual'),
)


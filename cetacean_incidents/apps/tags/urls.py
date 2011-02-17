from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^(?P<tag_id>\d+)/delete$', views.delete_tag, {}, 'delete_tag'),
)


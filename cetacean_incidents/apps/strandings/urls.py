from django.conf.urls.defaults import *
from django.forms import Media
from django.conf import settings

import views

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'stranding_detail'),
)

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_stranding, {}, 'edit_stranding'),
    (r'^(?P<stranding_id>\d+)/add_observation$', views.add_strandingobservation, {}, 'add_strandingobservation'),

    (r'^observations/(\d+)/$', views.strandingobservation_detail, {}, 'strandingobservation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_strandingobservation, {}, 'edit_strandingobservation'),
)


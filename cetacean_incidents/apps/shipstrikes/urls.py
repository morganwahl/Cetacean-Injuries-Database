from django.conf.urls.defaults import *

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'shipstrike_detail'),
)

import views

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_shipstrike, {}, 'edit_shipstrike'),
    (r'^(?P<shipstrike_id>\d+)/add_observation$', views.add_shipstrikeobservation, {}, 'add_shipstrikeobservation'),
    (r'^observations/(\d+)/$', views.shipstrikeobservation_detail, {}, 'shipstrikeobservation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_shipstrikeobservation, {}, 'edit_shipstrikeobservation'),
)


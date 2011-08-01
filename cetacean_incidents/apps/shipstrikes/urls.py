from django.conf.urls.defaults import *

import views

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'shipstrike_detail'),
)

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_shipstrike, {}, 'edit_shipstrike'),
    (r'^(?P<shipstrike_id>\d+)/add_observation$', views.add_shipstrikeobservation, {}, 'add_shipstrikeobservation'),
    (r'^(?P<destination_id>\d+)/merge$', views.shipstrike_merge, {}, 'shipstrike_merge'),
    (r'^(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.shipstrike_merge, {}, 'shipstrike_merge'),

    (r'^search$', views.shipstrike_search, {}, 'shipstrike_search'),

    # TODO make a permanent redirect to generic observation detail
    # No longer makes sense now that ShipstrikeObservation is an ObservationExtension
    #(r'^observations/(\d+)/$', views.shipstrikeobservation_detail, {}, 'shipstrikeobservation_detail'),
    # TODO make a permanent redirect to generic observation detail
    # No longer makes sense now that ShipstrikeObservation is an ObservationExtension
    #(r'^observations/(\d+)/edit$', views.edit_shipstrikeobservation, {}, 'edit_shipstrikeobservation'),
)


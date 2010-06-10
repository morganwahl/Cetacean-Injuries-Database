from django.conf.urls.defaults import *

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'shipstrike_detail'),
)

import views

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_shipstrike, {}, 'edit_shipstrike'),
    (r'^observations/(\d+)/$', views.shipstrikeobservation_detail, {}, 'shipstrikeobservation_detail'),
    (r'^shipstrike_report_form/$', views.shipstrike_report_form, {}, 'shipstrike_report_form'),
)


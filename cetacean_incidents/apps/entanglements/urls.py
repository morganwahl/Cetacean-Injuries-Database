from django.conf.urls.defaults import *

import views

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'entanglement_detail'),
)

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_entanglement, {}, 'edit_entanglement'),
    (r'^(\d+)/add_observation$', views.add_entanglementobservation, {}, 'add_entanglementobservation'),
    (r'^(\d+)/add_gear_owner$', views.add_gear_owner, {}, 'add_gear_owner'),
    (r'^(\d+)/edit_gear_owner$', views.edit_gear_owner, {}, 'edit_gear_owner'),
    (r'^observations/(\d+)/$', views.entanglementobservation_detail, {}, 'entanglementobservation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_entanglementobservation, {}, 'edit_entanglementobservation'),
    (r'^entanglement_report_form/$', views.entanglement_report_form, {}, 'entanglement_report_form'),
)


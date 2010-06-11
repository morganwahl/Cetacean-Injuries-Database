from django.conf.urls.defaults import *

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    (r'^(\d+)/$', 'case_detail', {}, 'entanglement_detail'),
)

import views

urlpatterns += patterns('',
    (r'^(\d+)/edit$', views.edit_entanglement, {}, 'edit_entanglement'),
    (r'^(\d+)/add_observation$', views.add_entanglementobservation, {}, 'add_entanglementobservation'),
    (r'^observations/(\d+)/$', views.entanglementobservation_detail, {}, 'entanglementobservation_detail'),
    (r'^observations/(\d+)/edit$', views.edit_entanglementobservation, {}, 'edit_entanglementobservation'),
    (r'^entanglement_report_form/$', views.entanglement_report_form, {}, 'entanglement_report_form'),
)


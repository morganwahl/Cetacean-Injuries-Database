from django.conf.urls.defaults import *
from django.forms import Media

import views

urlpatterns = patterns('cetacean_incidents.apps.incidents.views',
    # entanglements use the location_details include template, which needs 
    # RadioHider
    (r'^(\d+)/$', 'case_detail', {
        'extra_context': {
            'media': Media(js=('jquery/jquery-1.3.2.min.js', 'radiohider.js',)),
         },
    }, 'entanglement_detail'),
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


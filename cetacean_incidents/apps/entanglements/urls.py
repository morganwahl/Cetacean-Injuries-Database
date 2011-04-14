from django.conf import settings
from django.conf.urls.defaults import *
from django.forms import Media

import views

urlpatterns = patterns('',
    (r'^(\d+)/$', views.entanglement_detail, {
        'extra_context': {
            'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js',)),
         },
    }, 'entanglement_detail'),
    (r'^(\d+)/edit$', views.edit_entanglement, {}, 'edit_entanglement'),
    (r'^(?P<entanglement_id>\d+)/add_observation$', views.add_entanglementobservation, {}, 'add_entanglementobservation'),
    (r'^(?P<destination_id>\d+)/merge$', views.entanglement_merge, {}, 'entanglement_merge'),
    (r'^(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.entanglement_merge, {}, 'entanglement_merge'),

    (r'^(\d+)/add_gear_owner$', views.edit_gear_owner, {}, 'add_gear_owner'),
    (r'^(\d+)/edit_gear_owner$', views.edit_gear_owner, {}, 'edit_gear_owner'),
    (r'^(\d+)/edit_gear_analysis_popup$', views.edit_gear_analysis_popup, {}, 'edit_gear_analysis_popup'),
    
    # TODO make a permanent redirect to generic observation detail
    #(r'^observations/(\d+)/$', views.entanglementobservation_detail, {}, 'entanglementobservation_detail'),
    # TODO make a permanent redirect to generic edit observation
    #(r'^observations/(\d+)/edit$', views.edit_entanglementobservation, {}, 'edit_entanglementobservation'),
)


from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    (r'^(\d+)/$', views.entanglement_detail, {}, 'entanglement_detail'),
    (r'^(\d+)/edit$', views.edit_entanglement, {}, 'edit_entanglement'),
    (r'^observations/(\d+)/$', views.entanglementobservation_detail, {}, 'entanglementobservation'),
    (r'^entanglement_report_form/$', views.entanglement_report_form, {}, 'entanglement_report_form'),
)


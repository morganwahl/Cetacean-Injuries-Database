from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    #(r'^(\d+)/$', views.shipstrike_detail, {}, 'shipstrike'),
    (r'^observations/(\d+)/$', views.shipstrikeobservation_detail, {}, 'shipstrikeobservation_detail'),
    (r'^shipstrike_report_form/$', views.shipstrike_report_form, {}, 'shipstrike_report_form'),
)


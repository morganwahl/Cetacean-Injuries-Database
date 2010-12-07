from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^(\d+)$', views.view_attachment, name='view_attachment'),
    url(r'^uploads/(\d+)$', views.view_uploadedfile, name='view_uploadedfile'),
)


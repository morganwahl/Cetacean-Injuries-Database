from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^(\d+)$', views.view_attachment, name='view_attachment'),
)


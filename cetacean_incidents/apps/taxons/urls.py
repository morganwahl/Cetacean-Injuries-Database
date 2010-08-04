from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^search$', views.taxon_search, name='taxon_search'),
)


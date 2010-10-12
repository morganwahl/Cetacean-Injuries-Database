from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^search$', views.taxon_search, name='taxon_search'),
    url(r'^import$', views.taxon_import, name='taxon_import'),
    url(r'^itis$', views.itis_search, name='itis'),
)


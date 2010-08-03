from django.conf.urls.defaults import *
import views
    url(r'^import$', views.taxon_import, name='taxon_import'),
    url(r'^itis$', views.itis_search, name='itis'),

urlpatterns = patterns('',
    url(r'^taxon_search$', views.taxon_search, name='taxon_search'),
)


from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^taxon_search$', views.taxon_search, name='taxon_search'),
    (r'^test$', views.testview),
)


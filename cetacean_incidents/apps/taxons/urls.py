from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^$', views.taxon_tree, name='taxon_list'),
    url(r'^(?P<root_id>\d+)/tree_node$', views.taxon_tree, name='taxon_tree'),
    url(r'^(?P<taxon_id>\d+)$', views.taxon_detail, name='taxon_detail'),
    (r'^(?P<destination_id>\d+)/merge$', views.taxon_merge, {}, 'merge_taxon'),
    (r'^(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.taxon_merge, {}, 'merge_taxon'),

    url(r'^search$', views.taxon_search, name='taxon_search'),
    url(r'^import$', views.import_search, name='taxon_import'),
    url(r'^import/(?P<tsn>\d+)$', views.import_tsn, name='taxon_import_tsn'),
    url(r'^itis$', views.itis_search, name='itis'),
)


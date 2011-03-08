from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    url(r'^documents/(\d+)$', views.view_document, name='view_document'),
    url(r'^documents/(\d+)/delete$', views.delete_document, name='delete_document'),
    url(r'^documents/(\d+)/edit$', views.edit_document, name='edit_document'),
    url(r'^uploads/(\d+)$', views.view_uploadedfile, name='view_uploadedfile'),
    url(r'^repo_files/(\d+)$', views.view_repositoryfile, name='view_repositoryfile'),
    
    url(r'^documentables/(\d+)/add_document', views.add_document, name='add_document'),
)


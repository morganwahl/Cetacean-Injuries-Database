from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    url(r'^(\d+)$', views.view_document, name='view_document'),
    url(r'^uploads/(\d+)$', views.view_uploadedfile, name='view_uploadedfile'),
    url(r'^repo_files/(\d+)$', views.view_repositoryfile, name='view_repositoryfile'),
)


from django.conf.urls.defaults import *
from models import Contact
import views

contacts_args = {
    'queryset': Contact.objects.all(),
    'template_object_name': 'contact',
}

urlpatterns = patterns('cetacean_incidents.generic_views',
    (r'^$', 'object_list', contacts_args, 'all_contacts'),
    (r'^(?P<object_id>\d+)/$', 'object_detail', contacts_args, 'contact_detail'),
)

urlpatterns += patterns('',
    (r'^create$', views.create_contact, {}, 'create_contact'),
    (r'^(\d+)/edit$', views.edit_contact, {}, 'edit_contact'),
    (r'^(?P<destination_id>\d+)/merge/(?P<source_id>\d+)$', views.merge_contact, {}, 'merge_contact'),
)


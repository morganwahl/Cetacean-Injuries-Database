from django.conf.urls.defaults import *
from models import Contact
import views

contacts_args = {
    'queryset': Contact.objects.all(),
    'template_object_name': 'contact',
}

urlpatterns = patterns('django.views.generic.list_detail',
    (r'^$', 'object_list', contacts_args, 'all_contacts'),
    (r'^(?P<object_id>\d+)/$', 'object_detail', contacts_args, 'contact_detail'),
)

urlpatterns += patterns('',
    (r'^contacts/create$', views.create_contact, {}, 'create_contact'),
    (r'^contacts/(\d+)/edit$', views.edit_contact, {}, 'edit_contact'),
)

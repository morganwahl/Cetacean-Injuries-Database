from django.conf import settings
from django.conf.urls.defaults import *

from django.contrib import admin

from reversion.models import Revision

from generic_views import direct_to_template
import views

admin.autodiscover()

urlpatterns = patterns('',
    # docs needs to come first, or else the admin site will match
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    
    (r'^contacts/', include('cetacean_incidents.apps.contacts.urls')),
    (r'^taxons/', include('cetacean_incidents.apps.taxons.urls')),
    (r'^documents/', include('cetacean_incidents.apps.documents.urls')),
    (r'^incidents/', include('cetacean_incidents.apps.incidents.urls')),
    (r'^csv_import/', include('cetacean_incidents.apps.csv_import.urls')),
    (r'^entanglements/', include('cetacean_incidents.apps.entanglements.urls')),
    (r'^shipstrikes/', include('cetacean_incidents.apps.shipstrikes.urls')),
    (r'^tags/', include('cetacean_incidents.apps.tags.urls')),
    
    (r'^manual/', include('cetacean_incidents.apps.manual.urls')),
    (r'^problems/', views.odd_entries, {}, 'odd_entries'),
 
    # strip the initial '/' from the login url
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', name='logout'),
    # the permission_required decorator redirects on bad permissions
    url(r'^not_allowed/$', direct_to_template, {'template': 'not_allowed.html'}, 'not_allowed'),
    
    (r'^clear_cache/', views.clear_cache, {}, 'clear_cache'),
    
    (r'^$', views.home, {}, "home")
)

all_revisions_args = {
    'queryset': Revision.objects.all().order_by('-date_created'),
    'template_object_name': 'rev',
}
recent_revisions_args = {
    'queryset': Revision.objects.all().order_by('-date_created')[:20],
    'template_object_name': 'rev',
}
urlpatterns += patterns('cetacean_incidents.generic_views',
    (r'^revisions/$', 'object_list', all_revisions_args, 'all_revisions'),
    (r'^revisions/recent$', 'object_list', recent_revisions_args, 'recent_revisions'),
)
urlpatterns += patterns('',
    (r'^new_case$', views.new_case, {}, 'new_case'),
    (r'^revisions/(?P<rev_id>\d+)/$', views.revision_detail, {}, 'revision_detail'),
    (r'^revisions/object_history/(?P<content_type_id>\d+)/$', views.object_history, {}, 'object_history'),
    (r'^revisions/object_history/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', views.object_history, {}, 'object_history'),
    
    (r'staff_tools/import_taxon$', views.import_taxon, {}, 'import_taxon'),
)

# name the MEDIA_URL for use in templates. also has django serve up media if
# the hosting webserver doesn't.
urlpatterns += patterns("django.views",
    # strip URL_PREFIX from MEDIA_URL
    url(r"^%s(?P<path>.*)$" % settings.MEDIA_URL[len(settings.URL_PREFIX):],
        "static.serve",
        {"document_root": settings.MEDIA_ROOT},
        name="site-media",
    ),
)

# we re-use some widgets from the admin interface which expect this
js_info_dict = {
    'packages': ('django.conf',),
}
urlpatterns += patterns('django.views',
    (r'^jsi18n/$', 'i18n.javascript_catalog', js_info_dict, 'jsi18n'),
)

from django.contrib import databrowse
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.incidents.models import Animal
from cetacean_incidents.apps.entanglements.models import Entanglement, EntanglementObservation

databrowse.site.register(Animal)
databrowse.site.register(Taxon)
databrowse.site.register(Entanglement)
databrowse.site.register(EntanglementObservation)

urlpatterns += patterns('',
    (r'^databrowse/(.*)', databrowse.site.root),
)


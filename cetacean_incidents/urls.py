from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    # docs needs to come first, or else the admin site will match
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    
    (r'^contacts/', include('cetacean_incidents.apps.contacts.urls')),
    (r'^taxons/', include('cetacean_incidents.apps.taxons.urls')),
    (r'^incidents/', include('cetacean_incidents.apps.incidents.urls')),
    
    url(r'^%s$' % settings.LOGIN_URL[1:], 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', name='logout'),
    
    (r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'home.html'}, "home")
)

# name the MEDIA_URL for use in templates.
urlpatterns += patterns("django.views",
    url(r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:],
        "static.serve",
        {"document_root": settings.MEDIA_ROOT},
        name="site-media",
    ),
)

# we re-use some widgets from the admin interface which expect this
js_info_dict = {
    'packages': ('django.conf',),
}
urlpatterns += patterns('',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict, 'jsi18n'),
)

from django.contrib import databrowse
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.incidents.models import Animal, Entanglement, EntanglementObservation

databrowse.site.register(Animal)
databrowse.site.register(Taxon)
databrowse.site.register(Entanglement)
databrowse.site.register(EntanglementObservation)

urlpatterns += patterns('',
    (r'^databrowse/(.*)', databrowse.site.root),
)



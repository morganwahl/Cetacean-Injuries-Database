from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    # docs needs to come first, or else the admin site will match
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    
    (r'^animals/', include('apps.animals.urls')),
    (r'^incidents/', include('apps.incidents.urls')),
    
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


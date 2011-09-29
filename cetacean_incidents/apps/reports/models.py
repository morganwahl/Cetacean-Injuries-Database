import cStringIO as StringIO
import xhtml2pdf.pisa as pisa

from os import path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.template import (
    Context,
    Template,
)

from django.contrib.auth.models import User

from cetacean_incidents.apps.documents.models import Specificable

# FIXME are we duplicateing settings.MEDIA_ROOT?
from cetacean_incidents.apps.documents.models import _storage_dir, _checkdir, _storage_dir_name

# FIXME are we duplicateing settings.MEDIA_ROOT?
_reports_dir_name = 'reports'
_reports_dir = path.join(_storage_dir, _reports_dir_name)
_checkdir(_reports_dir)
_reports_url = settings.MEDIA_URL + '{0}/{1}/'.format(_storage_dir_name, _reports_dir_name)
reports_storage = FileSystemStorage(
    location= _reports_dir,
    base_url= _reports_url,
)

class Report(Specificable):
    
    def render(self, context):
        t = self.template()
        if isinstance(context, dict):
            context = Context(context)
        return t.render(context)

    def render_to_pdf(self, context):
        contents = self.render(context)
        if self.format == 'text/html':
            result = StringIO.StringIO()
            pdf = pisa.pisaDocument(StringIO.StringIO(contents.encode("utf-8")), result)
            return result.getvalue()
        elif self.format == 'image/svg+xml':
            raise NotImplementedError
        return pdf_contents
    
    name = models.CharField(
        max_length= 256,
        unique= True,
    )

    #@property
    #def format(self):
    #    raise NotImplementedError
    
    def template(self):
        raise NotImplementedError

    def __unicode__(self):
        return self.name
        
class StringReport(Report):
    
    format = 'text/html'
    
    template_text = models.TextField()
    
    def template(self):
        return Template(self.template_text)

class FileReport(Report):

    template_file = models.FileField(
        storage= reports_storage,
        upload_to= '%Y/', # note that duplicates will have _<number> 
                          # appended by default so nothing gets overwritten
    )
    
    def template(self):
        contents = self.template_file.file.read()
        # turn off autoescaping
        # TODO better way to do this
        if self.format == 'text':
            contents = u"{# The template system assumes you want HTML escaping. Since we're not  generating HTML, turn it off. #}{% autoescape off %}" + contents + u"{% endautoescape %}"
            
        return Template(contents)

    format = models.CharField(
        max_length= 1000, # TODO just how long can a mimetype be?
        help_text= 'the type of the template\'s output',
        choices= (
            ('text', u'text'),
            ('text/html', u'HTML'),
            #('image/svg+xml', u'SVG'),
        ),
    )

    uploader = models.ForeignKey(
        User,
        editable=False,
    )

    upload_date = models.DateTimeField(
        auto_now_add= True,
    )


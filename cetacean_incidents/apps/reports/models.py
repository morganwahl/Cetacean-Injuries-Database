import cStringIO as StringIO
import xhtml2pdf.pisa as pisa

from os import path

from django.db import models
from django.template import (
    Context,
    Template,
)

from django.contrib.auth.models import User

from cetacean_incidents.apps.documents.models import Specificable

# FIXME are we duplicateing settings.MEDIA_ROOT?
from cetacean_incidents.apps.documents.models import _storage_dir

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
        upload_to= path.join(_storage_dir, u'reports', u'templates'),
    )
    
    def template(self):
        contents = self.template_file.file.read()
        return Template(contents)

    format = models.CharField(
        max_length= 1000, # TODO just how long can a mimetype be?
        help_text= 'the type of the template\'s output',
        choices= (
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


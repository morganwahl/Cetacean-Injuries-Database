import cStringIO as StringIO
import xhtml2pdf.pisa as pisa

from django.db import models
from django.template import (
    Context,
    Template,
)

from django.contrib.auth.models import User

class Report(models.Model):
    
    name = models.CharField(
        max_length= 256,
        unique= True,
    )
    template = models.FileField(
        upload_to= u'reports/templates',
    )
    format = models.CharField(
        max_length= 1000, # TODO just how long can a mimetype be?
        help_text= 'the type of the template\'s output',
        choices= (
            ('text/html', u'HTML'),
            ('image/svg+xml', u'SVG'),
        ),
    )
    uploader = models.ForeignKey(
        User,
        editable=False,
    )
    upload_date = models.DateTimeField(
        auto_now_add= True,
    )
    
    def render(self, context):
        contents = self.template.file.read()
        t = Template(contents)
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
    
    def __unicode__(self):
        return self.name


from django.db import models

from django.contrib.auth.models import User

from cetacean_incidents.apps.documents.models import Documentable

class Tag(models.Model):
    
    entry = models.ForeignKey(
        Documentable,
    )
    
    user = models.ForeignKey(
        User,
    )
    
    datetime_tagged = models.DateTimeField(
        auto_now_add=True,
    )
    
    tag_text = models.CharField(
        db_index=True,
        max_length=1024,
    )

    def __unicode__(self):
        return u"tag on %s: \u201c%s\u201d" % (self.entry.specific_instance(), self.tag_text)
    

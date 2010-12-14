from django.db import models

from cetacean_incidents.apps.documents.models import Document

from animal import Animal
from case import Case
from observation import Observation

class AttachedDocument(models.Model):
    
    document = models.OneToOneField(Document, primary_key=True)
    @property
    def attached_to(self):
        raise NotImplementedError("subclasses of Attachment must implement 'attached_to'")
        
    class Meta:
        app_label = 'incidents'
        abstract = True

class CaseDocument(AttachedDocument):
    
    attached_to = models.ForeignKey(Case)
    
    class Meta:
        app_label = 'incidents'

class ObservationDocument(AttachedDocument):

    attached_to = models.ForeignKey(Observation)
    
    class Meta:
        app_label = 'incidents'


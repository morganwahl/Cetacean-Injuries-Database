from django.db import models
from django.core.urlresolvers import reverse

from cetacean_incidents.apps.incidents.models import Case, Observation, _observation_post_save

class Stranding(Case):
    
    @models.permalink
    def get_absolute_url(self):
        return ('stranding_detail', [str(self.id)])

    def get_edit_url(self):
        return reverse('edit_stranding', args=[self.id])

class StrandingObservation(Observation):

    @models.permalink
    def get_absolute_url(self):
        return('strandingobservation_detail', [str(self.id)])
    
    def get_edit_url(self):
        return reverse('edit_strandingobservation', args=[self.id])

Stranding.observation_model = StrandingObservation

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=StrandingObservation)


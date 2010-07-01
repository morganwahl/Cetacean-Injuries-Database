from django.db import models

from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.dag.models import DAGEdge_factory, DAGNode_factory

class VesselType(DAGNode_factory(edge_model_name='VesselTypeRelation')):
    name = models.CharField(
        max_length= 512,
    )
    
    def __unicode__(self):
        return self.name

class VesselTypeRelation(DAGEdge_factory(node_model=VesselType)):
    pass

class VesselInfo(models.Model):
    '''\
    Note that this _isn't_ a model for individual vessels, but for a description
    of a vessel.
    '''

    contact = models.ForeignKey(
        Contact,
        related_name= "for_vessels",
        blank= True,
        null= True,
        help_text= "The contact for further details about the vessel, if necessary.",
    )
    imo_number = models.IntegerField(
        blank= True,
        null= True,
        verbose_name= "IMO number",
        help_text= "The International Maritime Organization number assigned to the ship. Should be a 7-digit number usually preceded with \"IMO\"."
        # Note that this most certainly _not_ unique, since we're just trying to
        # capture data for _one_ observatioin.
    )
    name = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "Vessel Name",
    )
    flag = models.ForeignKey(
        Country,
        blank= True,
        null= True,
    )
    description = models.TextField(
        blank= True,
    )
    def __unicode__(self):
        ret = 'unnamed vessel'
        if self.name:
            ret = "%s" % self.name
        ret += " (vessel %i" % self.id
        if self.flag:
            ret += ", %s" % self.flag.iso
        ret += ')'
        return ret



from django.db import models

from cetacean_incidents.apps.contacts.models import AbstractContact, Contact
from cetacean_incidents.apps.datetime.models import DateTime
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.incidents.models import Case, Observation, _observation_post_save
from cetacean_incidents.apps.dag.models import DAGEdge_factory, DAGNode_factory

class GearType(DAGNode_factory(edge_model_name='GearTypeRelation')):
    name= models.CharField(
        max_length= 512,
    )
    
    def __unicode__(self):
        return self.name    

class GearTypeRelation(DAGEdge_factory(node_model=GearType)):
    pass

class GearOwner(AbstractContact):
    '''\
    Everything in this table should be considered confidential!
    '''
    
    # TODO enforce view permissions at the model level!
    
    date_gear_set = models.OneToOneField(
        DateTime,
        blank= True,
        null= True,
        related_name= 'gear_set',
        verbose_name= 'date gear was set',
    )
    
    location_gear_set = models.OneToOneField(
        Location,
        blank= True,
        null= True,
        help_text= "please note depth as well"
    )    
        
    date_gear_missing = models.OneToOneField(
        DateTime,
        blank= True,
        null= True,
        related_name= 'gear_missing',
        verbose_name= 'date gear went missing',
    )

    missing_gear = models.TextField(
        blank= True,
        help_text= u"the owner's description of what gear they're missing",
        verbose_name= "missing gear description",
    )
    
    class Meta:
        permissions = (
            ("view_gear_owner", "Can view gear owner"),
        )

class Entanglement(Case):
    
    gear_fieldnumber = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        verbose_name= "Gear Field No.",
        help_text= "the gear-analysis-specific field no.",
    )
    
    @classmethod
    def _yes_no_unk_reduce(cls, thing1, thing2):
        '''\
        Given two items,
            - if either of them is True, return True
            - if both of them are False and not None, return False
            - otherwise, return None (for unknown)
        '''
        
        if bool(thing1) or bool(thing2):
            return True
        if thing1 is None or thing2 is None:
            return None
        return False
    
    @property
    def gear_retrieved(self):
        return reduce(
            self._yes_no_unk_reduce,
            map(
                lambda o: o.entanglementobservation.gear_retrieved,
                self.observation_set.all()
            )
        )
        
    # TODO does gear_analyzed imply gear_recovered?
    gear_analyzed = models.NullBooleanField(
        default= False,
        blank= True,
        null= True,
        verbose_name= "was gear analyzed?",
    )
    analyzed_date = models.DateField(
        blank= True,
        null= True,
        help_text= "please use YYYY-MM-DD",
    )
    analyzed_by = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
    )
    
    gear_types = models.ManyToManyField(
        'GearType',
        blank= True,
        null= True,
    )
    
    gear_owner_info = models.OneToOneField(
        'GearOwner',
        blank= True,
        null= True,
    )
    
    @property
    def implied_gear_types(self):
        if not self.gear_types.count():
            return set()
        implied_geartypes = set()
        for geartype in self.gear_types.all():
            implied_geartypes |= geartype.implied_supertypes
        return frozenset(implied_geartypes - set(self.gear_types.all()))
    
    @models.permalink
    def get_absolute_url(self):
        return ('entanglement_detail', [str(self.id)])

class EntanglementObservation(Observation):
    anchored = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "was the animal anchored?",
    )
    gear_description = models.TextField(
        blank= True,
        help_text= "describe physical characteristics of gear",
    )
    entanglement_details = models.TextField(
        blank= True,
        help_text= "details of how the animal was entangled",
    )
    gear_retrieved = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "was gear removed from the animal for later analysis?"
    )
    
    @models.permalink
    def get_absolute_url(self):
        return('entanglementobservation_detail', [str(self.id)])

Entanglement.observation_model = EntanglementObservation

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=EntanglementObservation)


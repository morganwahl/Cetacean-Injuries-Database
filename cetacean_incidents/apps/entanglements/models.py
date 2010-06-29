from django.db import models

from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.datetime.models import DateTime
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.incidents.models import Case, Observation, _observation_post_save


class GearTypeRelation(models.Model):
    '''\
    Intended to be used as the 'through' model in a ManyToManyField('self') 
    when implementing a Directed Acyclic Graph (DAG). Basically just does 
    cycle-checking when a new relation is added.
    '''
    
    class DAGException(Exception):
        '''\
        Exception thrown when a GearTypeRelation would violate the directed-
        acyclic-graph nature of GearTypes. E.g. when the subtype and supertype
        are the same.
        '''
        pass

    subtype = models.ForeignKey(
        'GearType',
        related_name= 'subtype_relations',
    )
    supertype = models.ForeignKey(
        'GearType',
        related_name= 'supertype_relations',
    )
    
    def save(self, *args, **kwargs):
        # check if this new relation would create a cycle in the DAG
        if self.subtype == self.supertype:
            raise self.DAGException(
                "%s can't be a supertype of itself!" % unicode(self.subtype),
            )
            
        if self.subtype in self.supertype.implied_supertypes:
            raise self.DAGException(
                # TODO determined what the cycle would be
                "%s can't be a supertype of %s, that would create a cycle!" % (
                    unicode(self.supertype),
                   unicode(self.subtype),
                )
            )

        return super(self.__class__, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return "%r -> %r" % (self.subtype, self.supertype)
    
    class Meta:
        unique_together = ('subtype', 'supertype')

class RootGearTypeManager(models.Manager):
    def get_query_set(self):
        qs = super(RootGearTypeManager, self).get_query_set()
        # filter out all GearTypes that are the subtype in a GearTypeRelation
        # TODO simplier way to query for that?
        return qs.annotate(supertypes_num=models.Count('supertypes')).filter(supertypes_num=0)

class GearType(models.Model):
    name= models.CharField(
        max_length= 512,
    )
    supertypes= models.ManyToManyField(
        'self',
        through= GearTypeRelation,
        symmetrical= False,
        blank= True,
        null= True,
        related_name= 'subtypes',
        help_text= 'what other types would be implied by this type?'
    )
    
    objects = models.Manager()
    roots = RootGearTypeManager()
    
    def _get_implied_supertypes_with_ignore(self, ignore_types):
        # The ignore_types arg is a set of GearTypes that won't be included in 
        # the results. It's used to prevent infinite loops in recursive calls.
        
        # be sure 'self' is in ignore_types.
        ignore_types |= set([self])
        # traverse supertypes and return a set of all GearTypes seen
        implied_supertypes = set(self.supertypes.all()) - ignore_types
        if len(implied_supertypes):
            to_traverse = implied_supertypes.copy()
            for supertype in to_traverse:
                implied_supertypes |= supertype._get_implied_supertypes_with_ignore(
                    ignore_types= ignore_types | implied_supertypes,
                )
        return frozenset(implied_supertypes)

    @property
    def implied_supertypes(self):
        return self._get_implied_supertypes_with_ignore(ignore_types=set())
    
    def __unicode__(self):
        return self.name    

class GearOwner(models.Model):
    '''\
    Everything in this table should be considered confidential!
    '''    
    
    # TODO enforce view permissions at the model level!
    
    owner_contact = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
    )
    
    date_gear_set = models.OneToOneField(
        DateTime,
        blank= True,
        null= True,
        related_name= 'gear_set',
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
    )

    missing_gear = models.TextField(
        blank= True,
        help_text= u"the owner's description of what gear they're missing",
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
        default= None,
        blank= True,
        null= True,
        help_text= "was the gear analyzed?",
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


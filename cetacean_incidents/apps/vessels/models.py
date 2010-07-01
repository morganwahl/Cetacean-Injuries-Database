from django.db import models

from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.contacts.models import Contact

# TODO entanglements.models.GearType and VesselType have a lot of common code

class VesselTypeRelation(models.Model):
    '''\
    Intended to be used as the 'through' model in a ManyToManyField('self') 
    when implementing a Directed Acyclic Graph (DAG). Basically just does 
    cycle-checking when a new relation is added.
    '''
    
    class DAGException(Exception):
        '''\
        Exception thrown when a VesselTypeRelation would violate the directed-
        acyclic-graph nature of VesselTypes. E.g. when the subtype and supertype
        are the same.
        '''
        pass

    subtype = models.ForeignKey(
        'VesselType',
        related_name= 'subtype_relations',
    )
    supertype = models.ForeignKey(
        'VesselType',
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

class RootVesselTypeManager(models.Manager):
    def get_query_set(self):
        qs = super(RootVesselTypeManager, self).get_query_set()
        # filter out all VesselTypes that are the subtype in a VesselTypeRelation
        # TODO simplier way to query for that?
        return qs.annotate(supertypes_num=models.Count('supertypes')).filter(supertypes_num=0)

class VesselType(models.Model):
    name= models.CharField(
        max_length= 512,
    )
    supertypes= models.ManyToManyField(
        'self',
        through= VesselTypeRelation,
        symmetrical= False,
        blank= True,
        null= True,
        related_name= 'subtypes',
        help_text= 'what other types would be implied by this type?'
    )
    
    objects = models.Manager()
    roots = RootVesselTypeManager()
    
    def _get_implied_supertypes_with_ignore(self, ignore_types):
        # The ignore_types arg is a set of VesselTypes that won't be included in 
        # the results. It's used to prevent infinite loops in recursive calls.
        
        # be sure 'self' is in ignore_types.
        ignore_types |= set([self])
        # traverse supertypes and return a set of all VesselTypes seen
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



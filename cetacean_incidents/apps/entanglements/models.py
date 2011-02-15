from django.db import models
from django.core.urlresolvers import reverse

from cetacean_incidents.apps.contacts.models import AbstractContact, Contact
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.incidents.models import Case, ObservationExtension
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
    
    datetime_set = UncertainDateTimeField(
        blank= True,
        null= True,
        verbose_name= 'date gear was set',
    )
    
    location_gear_set = models.OneToOneField(
        Location,
        blank= True,
        null= True,
        help_text= "please note depth as well"
    )    
        
    datetime_missing = UncertainDateTimeField(
        blank= True,
        null= True,
        verbose_name= 'date gear went missing',
    )

    missing_gear = models.TextField(
        blank= True,
        help_text= u"The owner's description of what gear they're missing.",
        verbose_name= "missing gear description",
    )
    
    class Meta:
        permissions = (
            ("view_gear_owner", "Can view gear owner"),
        )

class Entanglement(Case):
    
    nmfs_id = models.CharField(
        max_length= 255,
        unique= False, # in case a NMFS case corresponds to multiple cases in
                       # our database
        blank= True,
        verbose_name= "entanglement NMFS ID",
        help_text= "An entanglement-specific case ID.",
    )
    
    def _case_type_name(self):
        return self.nmfs_id
        
    gear_fieldnumber = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        verbose_name= "Gear Field No.",
        help_text= "The gear-analysis-specific case ID.",
    )
    
    @staticmethod
    def _yes_no_unk_reduce(thing1, thing2):
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
                lambda o: o.entanglements_entanglementobservation.gear_retrieved,
                self.observation_set.all()
            )
        )
        
    # TODO does gear_analyzed imply gear_recovered?
    gear_analyzed = models.NullBooleanField(
        default= False,
        blank= True,
        null= True,
        verbose_name= "Was the gear analyzed?",
    )
    analyzed_date = models.DateField(
        blank= True,
        null= True,
        help_text= "Date the gear was analyzed. Please use YYYY-MM-DD",
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
        help_text= "All the applicable gear types in the set of gear from this entanglement.",
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

    def get_edit_url(self):
        return reverse('edit_entanglement', args=[self.id])

class BodyLocation(models.Model):
    '''\
    Model for customizable/extensible classification of location on/in an
    animal's body.
    '''
    
    # future developement: add a reference to a Taxon field (or fields) whose
    # animals this location is defined for
    
    name = models.CharField(
        max_length= 512,
        unique=True,
    )
    
    definition = models.TextField(
        blank= True,
        null= True,
    )
    
    ordering = models.DecimalField(
        max_digits= 5,
        decimal_places = 5,
        default = '.5',
    )
    
    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('ordering', 'name')

class EntanglementObservation(ObservationExtension):
    
    anchored = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name= 'anchored?',
        help_text= "Was the animal anchored?",
    )
    gear_description = models.TextField(
        blank= True,
        help_text= """Unambiguous description of the physical characteristics of gear. E.g. "a green line over attached to a buoy with a black stripe". Avoid trying to guess the gear's function e.g. "6-inch mesh" is better than "fishing net". Describe the way the gear is on the animal in the 'entanglement details' field.""",
    )
    gear_body_location = models.ManyToManyField(
        'BodyLocation',
        through= 'GearBodyLocation',
        blank= True,
        null= True,
        help_text= "Where on the animal's body was gear seen or not seen?"
    )
    entanglement_details = models.TextField(
        blank= True,
        help_text= "Detailed description of how the animal was entangled.",
    )
    gear_retrieved = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name= 'gear retrieved?',
        help_text= "Was gear removed from the animal for later analysis?"
    )
    disentanglement_outcome = models.CharField(
        max_length= 4,
        choices= (
            ('entg', 'entangled'),
            ('shed', 'gear shed'),
            ('part', 'partial'),
            ('cmpl', 'complete'),
            ('mntr', 'monitor'),
        ),
        blank= True,
        help_text= "If there was a disentanglement attempted, what was the outcome?"
    )
    
    def get_gear_body_locations(self):
        body_locations = []
        for loc in BodyLocation.objects.all():
            gear_loc = GearBodyLocation.objects.filter(observation=self, location=loc)
            if gear_loc.exists():
                body_locations.append((loc, gear_loc[0]))
            else:
                body_locations.append((loc, None))

        return body_locations

    def get_observation_view_data(self):
        # avoid circular imports
        from views import get_entanglementobservation_view_data
        return get_entanglementobservation_view_data(self)

    @property
    def _extra_context(self):
        return {
            'gear_body_locations': self.get_gear_body_locations(),
        }

    class Meta:
        verbose_name = "Observation entanglement-data"
        verbose_name_plural = verbose_name

class GearBodyLocation(models.Model):
    observation = models.ForeignKey(EntanglementObservation)
    location = models.ForeignKey(BodyLocation)
    gear_seen_here = models.BooleanField()
    
    def __unicode__(self):
        return "%s of %s" % (self.observation, self.location)
    
    class Meta:
        unique_together = ('observation', 'location')


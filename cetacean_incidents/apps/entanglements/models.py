from django.core.urlresolvers import reverse
from django.db import models

from cetacean_incidents.apps.contacts.models import (
    AbstractContact,
    Contact,
)

from cetacean_incidents.apps.dag.models import (
    DAGEdge_factory,
    DAGNode_factory,
)

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.incidents.models import (
    Case,
    Observation,
    ObservationExtension,
)

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

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
            ("view_gearowner", "Can view gear owner"),
        )

guard_deletes(Location, GearOwner, 'location_gear_set')

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

guard_deletes(Contact, Entanglement, 'analyzed_by')
guard_deletes(GearOwner, Entanglement, 'gear_owner_info')

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
        max_digits= 6,
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
    disentanglement_attempted = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name= u'disentanglement attempted?',
        help_text= u'''Was a disentanglement attempt made (would be considered a take under permit), entangling gear altered, or the animal disentangled?''',
    )
    disentanglement_outcome = models.CharField(
        max_length= 4,
        choices= (
            #('',     'unknown'),
            ('shed', 'gear shed'),
            ('mntr', 'monitor'),
            ('entg', 'entangled'),
            ('part', 'partial'),
            ('cmpl', 'complete'),
        ),
        blank= True,
        verbose_name= "animal entanglement status", # ersatz name-change
        help_text= u"""\
            <em>What was the state of the animal's entanglement at the <u>end</u> of the observation?</em>
            <dl>
                <dt>gear shed</dt>
                <dd>No disentanglement was attempted since the animal had disentangled itself.</dd>
                <dt>monitor</dt>
                <dd>The entanglement was determined not to be severe enough to warrant a disentanglement attempt.</dd>
                <dt>entangled</dt>
                <dd>A disentanglement was deemed necessary but was unsuccessful, couldn't be attempted or had insufficient documentation to conclude entanglement status.</dd>
                <dt>partial</dt>
                <dd>A disentanglement was attempted and the gear was partly removed.</dd>
                <dt>complete</dt>
                <dd>A disentanglement was attempted and the gear was completely removed.</dd>
            </dl>
        """,
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

    def get_gear_body_locations_dict(self):
        result = {}
        for loc, gbl in self.get_gear_body_locations():
            if gbl is None:
                result[loc] = None
            else:
                result[loc] = gbl.gear_seen_here
        return result

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

# TODO generalize this for all ObservationExtensions
def add_entanglement_extension_handler(sender, **kwargs):
    # sender shoulde be Observation.cases.through
    action = kwargs['action']
    if action == 'post_add':
        reverse = kwargs['reverse']
        if not reverse:
            # observation.cases.add(<some cases>)
            # kwargs['instance'] is observation
            # kwargs['model'] is Case
            # kwargs['pk_set'] is a iterable of Case PK's
            obs = kwargs['instance']
            # do we already have an E.OE.
            try:
                obs.entanglements_entanglementobservation
                return
            except EntanglementObservation.DoesNotExist:
                # are any of the cases Entanglements
                if Entanglement.objects.filter(pk__in=kwargs['pk_set']):
                    # be sure not to overwrite an existing extension
                    try:
                        obs.entanglements_entanglementobservation
                    except EntanglementObservation.DoesNotExist:
                        EntanglementObservation.objects.create(
                            observation_ptr=obs,
                        )
        else:
            # entanglement.observation_set.add(<some observations>)
            # kwargs['instance'] is entanglement
            # kwargs['model'] is Observation
            # kwargs['pk_set'] is a iterable of Observation PK's
            case = kwargs['instance']
            if not isinstance(case, Entanglement):
                return
            # add E.OE. to any obs that don't already have them
            for o in Observation.objects.filter(pk__in=kwargs['pk_set']):
                # be sure not to overwrite an existing extension
                try:
                    o.entanglements_entanglementobservation
                except EntanglementObservation.DoesNotExist:
                    EntanglementObservation.objects.create(
                        observation_ptr=o,
                    )
    
models.signals.m2m_changed.connect(
    sender= Observation.cases.through,
    receiver= add_entanglement_extension_handler,
    dispatch_uid= 'observation_cases__add_entanglement_extension__m2m_changed',
)

class GearBodyLocation(models.Model):
    observation = models.ForeignKey(EntanglementObservation)
    location = models.ForeignKey(BodyLocation)
    gear_seen_here = models.BooleanField()
    
    def __unicode__(self):
        return "%s of %s" % (self.observation, self.location)
    
    class Meta:
        unique_together = ('observation', 'location')

guard_deletes(BodyLocation, GearBodyLocation, 'location')


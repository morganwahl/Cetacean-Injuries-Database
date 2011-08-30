import operator

from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.core.urlresolvers import reverse
from django.db import models

#from cetacean_incidents.apps.clean_cache import Smidgen

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

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

class GearType(DAGNode_factory(edge_model_name='GearTypeRelation')):
    name= models.CharField(
        max_length= 512,
    )
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'Gear Attribute (formerly Gear Type)'
        verbose_name_plural = 'Gear Attributes (formerly Gear Types)'

class GearTypeRelation(DAGEdge_factory(node_model=GearType)):
    
    class Meta:
        # TODO this ordering seems to cause problems on Oracle
        #ordering = ('supertype__name', 'subtype__name')
        verbose_name = 'Gear Attribute Implication (formerly Gear Type Relation)'
        verbose_name_plural = 'Gear Attribute Implications (formerly Gear Type Relations)'

class LocationGearSet(Location):
    '''\
    Everything in this table should be considered confidential!
    '''
    
    # TODO enforce view permissions at the model level!
    
    exempt_waters = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= u"Was the gear set in exempt waters?",
    )
    
    depth = models.DecimalField(
        blank= True,
        null= True,
        # 99,999.999 
        # the Mariana Trench is a bit over 10 km deep (possibly 11). 1
        # millimeter precision is probably all you can expect for a depth.
        max_digits= 8,
        decimal_places= 3,
        validators= [MinValueValidator(0)],
        help_text= u"""Depth the gear was set at, in meters.""",
    )
        
    depth_sigdigs = models.IntegerField(
        blank= True,
        null= True,
        validators= [
            MinValueValidator(1),
            MaxValueValidator(6), # should equal depth.max_digits
        ],
        verbose_name= '# of significant digits in the depth',
        help_text= u"""
            Defaults to # of digits in 'depth'. The depth is stored at
            millimeter precision; this is only used when rounding for display
            in different units.
        """,
    )
    
    bottom_type = models.CharField(
        max_length= 1024,
        blank= True,
        null= True,
    )
    
    @property
    def has_data(self):
        return reduce(operator.__or__, (
            super(LocationGearSet, self).has_data,
            self.exempt_waters is not None,
            self.depth is not None, # zero-depth is still data
            bool(self.bottom_type),
        ))

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
        LocationGearSet,
        blank= True,
        null= True,
    )    
        
    datetime_missing = UncertainDateTimeField(
        blank= True,
        null= True,
        verbose_name= 'date gear went missing',
    )

    class Meta:
        permissions = (
            ("view_gearowner", "Can view gear owner"),
        )

guard_deletes(Location, GearOwner, 'location_gear_set')

class GearAnalysis(models.Model):
    '''\
    Abstract class to hold the fields related to gear-analysis.
    '''
    
    gear_fieldnumber = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        verbose_name= "Gear Field No.",
        help_text= "The gear-analysis-specific case ID.",
    )
    
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
    
    num_gear_types = models.IntegerField(
        blank= True,
        null= True,
        validators= [MinValueValidator(0)],
        verbose_name= "# of gear types",
        help_text= "How many different kinds of gear were there?",
    )
    
    observed_gear_attributes = models.ManyToManyField(
        'GearType',
        blank= True,
        null= True,
        related_name= 'observed_in',
        verbose_name= 'observed gear attributes',
        help_text= "All the applicable gear attributes in the observed set of gear from this entanglement. This includes any gear on the animal as described in observations or otherwise documented.",
    )
    
    # would be called 'analyzed_gear_attributes', but isn't for backwards-compat
    gear_types = models.ManyToManyField(
        'GearType',
        blank= True,
        null= True,
        related_name= 'analyzed_in',
        verbose_name= 'analyzed gear attributes',
        help_text= "All the applicable gear attributes in the analyzed set of gear from this entanglement. This is only the gear that was brought in for analysis.",
    )
    
    gear_targets = models.ManyToManyField(
        Taxon,
        blank= True,
        null= True,
        related_name= 'targeted_by',
        verbose_name= 'target taxa', # not really verbose, just a name change
        help_text= "All the taxa that were intended to by caught by this gear.",
    )
    
    gear_description = models.TextField(
        blank= True,
        null= True,
        help_text= u"""Detailed description of the gear that was analyzed. If the gear owner is known and their description of the gear they're missing differs from what was analyzed, note it here. Keep in mind that this field is not confidential, unlike the gear owner info.""",
    )
    
    gear_regulated = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "gear regulated?",
        help_text= "Are there any regulations for the gear when and where it was set?",
    )
    
    gear_compliant = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "gear compliant?",
        help_text= "Was the gear compliant with regulations when and where it was set?",
    )
    
    gear_analysis_comments = models.TextField(
        blank= True,
        null= True,
    )
    
    gear_analysis_conclusions = models.TextField(
        blank= True,
        null= True,
    )
    
    gear_owner_info = models.OneToOneField(
        'GearOwner',
        blank= True,
        null= True,
    )
    
    # only makes sense if gear_analyzed = True
    gear_kept = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "was the gear kept after analysis?",
    )
    
    # only makes sense if gear_kept = True
    gear_kept_where = models.TextField(
        blank= True,
        null= True,
    )
    
    # TODO simpler way to do this?
    @staticmethod
    def gear_analysis_fieldnames():
        return GearAnalysis._meta.get_all_field_names()
    
    @property
    def implied_gear_types(self):
        if not self.gear_types.count():
            return set()
        implied_geartypes = set()
        for geartype in self.gear_types.all():
            implied_geartypes |= geartype.implied_supertypes
        return frozenset(implied_geartypes - set(self.gear_types.all()))
    
    @property
    def implied_observed_gear_attributes(self):
        if not self.observed_gear_attributes.count():
            return set()
        implied_attributes = set()
        for attrib in self.observed_gear_attributes.all():
            implied_attributes |= attrib.implied_supertypes
        return frozenset(implied_attributes - set(self.observed_gear_attributes.all()))

    class Meta:
        abstract = True

class Entanglement(Case, GearAnalysis):
    
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

    @models.permalink
    def get_absolute_url(self):
        return ('entanglement_detail', [str(self.id)])

    def get_edit_url(self):
        return reverse('edit_entanglement', args=[self.id])

# conceptually these go on GearAnalysis, but guard_deletes doesn't work with
# abstract models
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
    # TODO should be null if not gear_retrieved
    gear_retriever = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'retrieved_gear_during',
        help_text= "Who retrieved the gear?",
    )
    # TODO should be null if not gear_retrieved
    gear_given_date = models.DateField(
        blank= True,
        null= True,
        verbose_name= 'date gear recevied for analysis',
        help_text= "When was the gear retrived in this observation given to whoever analyzed it?"
    )
    # TODO should be null if not gear_retrieved
    gear_giver = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'gave_gear_from',
        verbose_name= 'gear received for analysis from',
        help_text= "Who gave the gear retrieved in this observation to whoever analyzed it?",
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

guard_deletes(Contact, EntanglementObservation, 'gear_retriever')
guard_deletes(Contact, EntanglementObservation, 'gear_giver')

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


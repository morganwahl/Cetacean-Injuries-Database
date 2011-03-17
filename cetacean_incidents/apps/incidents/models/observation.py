# -*- encoding: utf-8 -*-

import datetime
import pytz

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from cetacean_incidents.apps.vessels.models import VesselInfo

from animal import (
    Animal,
    GENDERS,
)
from imported import Importable

class ObservationManager(models.Manager):

    def observer_set(self):
        '''\
        Returns a list of observers (Contact instances) for these observations.
        '''
        
        observers = self.values_list('observer', flat=True)
        observers = frozenset(observers)
        observers = Contact.objects.filter(id__in=observers)
        
        return observers

class Observation(Documentable, Importable):
    '''\
    The heart of the database: observations. 
    
    An Observation is a source of data for an Animal. It has an observer and
    date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report.

    Many of the references to other tables (specifically, observer_vessel, and
    location) are one-to-one relationships; the other tables exist just to make
    programming easier, since they are logical sets of fields.
    '''
    
    animal = models.ForeignKey(
        'Animal',
        help_text= 'The animal observed.',
    )
    
    cases = models.ManyToManyField(
        'Case',
        help_text= 'The cases that this observation is relevant to.',
    )
    
    initial = models.BooleanField(
        default= False,
        verbose_name= u"is this an ‘initial observation’ on a Level A?",
        help_text= u"""Check if this observation corresponds to the ‘initial observation’ on a Level A form. If it does, the observation date should correspond to the "date of initial observation" on the Level A, and the condition should correspond to the "condition at initial observation".""",
    )
    exam = models.BooleanField(
        default= False,
        verbose_name= u"is this a ‘Level A Examination’?",
        help_text= u"""Check if this observation corresponds to the ‘level a examination’ on a Level A form. If it does, the observation date should correspond to the date of examination on the Level A, the condition should correspond to the "condition at examination", and the observer should correspond to the "examiner". Note that an observation can be both the ‘initial observation’ and the ‘examination’ (or neither).""",
    )
    
    narrative = models.TextField(
        blank= True,
        help_text= "A complete description of the observation. No limit as to length. Ideally, all the other fields for an observation could be filled in after reading this."
    )
    
    observer = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'Whoever actually saw the animal.', 
    )
    datetime_observed = UncertainDateTimeField(
        db_index=True,
        help_text= "When did the observer see it? (Strictly, when did the observation start?) The earliest observation date for a case's observations is the date used for the case itself, e.g. when assigning a case to a year.",
        verbose_name= 'observation date and time',
    )
    # TODO duration?

    location = models.OneToOneField(
        Location,
        blank= True,
        null= True,
        related_name= "observation",
        help_text= 'the observer\'s location at the time of observation. (strictly, where did the observation begin)',
    )
    observer_vessel = models.OneToOneField(
        VesselInfo,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    
    @property
    def firsthand(self):
        if self.reporter is None and self.observer is None:
            return None
        return self.reporter == self.observer

    reporter = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'reported',
        help_text= "This is who informed us of the observation. Same as observer if this is a firsthand report.",
    )
    datetime_reported = UncertainDateTimeField(
        db_index=True,
        help_text = 'When did we first heard about the observation?',
        verbose_name = 'report date and time',
    )
        
    @property
    def earliest_datetime(self):
        '''\
        The earliest that the observation _may_ have started.
        '''
        o = self.datetime_observed
        r = self.datetime_reported
        # if reportdatetime is before observation datetime (which doesn't make
        # sense, but don't count on it not happening) assume the actual
        # observation datetime is the same as the report datetime
        
        result = o.earliest
        
        # 'wrong' situation
        if r.latest < o.earliest:
            result = r.earliest
        
        return result
    
    @property
    def latest_datetime(self):
        '''\
        The latest that the observation _may_ have started.
        '''
        
        # don't return datetimes in the future
        # TODO timezones?
        now = datetime.datetime.now()
        return min(self.datetime_observed.latest, self.datetime_reported.latest, now)
    
    @property
    def observation_breadth(self):
        '''\
        The length of time the observation _may_ have started in.
        '''
        
        return self.latest_datetime - self.earliest_datetime

    taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= u"""The most specific taxon (e.g. a species) the animal is described as. Can be a vauge as an order or as specific as a subspecies or just unknown. Taxa are taken from the "Integrated Taxonomic Information System" (see itis.gov).""",
    )

    animal_length = models.DecimalField(
        blank= True,
        null= True,
        # 99.9999
        # blue whales get up 33 meters, so this gives us .1 millimeter-precision
        # on any animal
        max_digits= 6,
        decimal_places= 4,
        validators= [MinValueValidator(0)],
        help_text= u"""Length of the animal in meters, if measured.""",
    )
    
    animal_length_sigdigs = models.IntegerField(
        blank= True,
        null= True,
        validators= [
            MinValueValidator(1),
            MaxValueValidator(6), # should equal animal_length.max_digits
        ],
        verbose_name= '# of significant digits in animal_length',
        help_text= u"""defaults to # of non-zero digits in 'animal length'""",
    )

    age_class = models.CharField(
        max_length= 2,
        blank= True,
        choices= (
            ('ca', 'calf'),
            ('ju', 'juvenile'),
            ('ad', 'adult'),
        ),
        help_text= u"""Note that these are somewhat subjective, and their definitions, if any, certainly depend on the animal's species. In general, ‘pup’ is a synonym for ‘calf’ and ‘sub-adult’ for ‘juvenile’.""",
    )
    
    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The sex of this animal, if known.',
        verbose_name = 'sex', # yes, it's not really verbose, but this is easier
                              # than changing the name of the column in the 
                              # database for now.
    )
    
    animal_description = models.TextField(
        blank= True,
        help_text= u"""Anything that would help identify the individual animal or it's species or age or sex, etc. Even if those are specified above, please note what that was on the basis of.""",
    )
    
    ashore = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name= "ashore?",
        help_text= "Was the animal ashore? Pick 'yes' even if it came ashore during the observation.",
    )

    # numeric codes (except 0) are from stranding spreadsheet. they're kept to
    # allow sorting.
    condition = models.IntegerField(
        default= 0,
        choices= (
            (0, 'unknown'),
            (1, 'alive'),
            (6, 'dead, carcass condition unknown'),
            (2, 'fresh dead'),
            (3, 'moderate decomposition'),
            (4, 'advanced decomposition'),
            (5, 'skeletal'),
        ),
        verbose_name= "Condition (dead or alive?)",
        help_text= '''\
            <em>carcass condition definitions</em>:
            <dl>
                <dt>fresh dead</dt>
                <dd>
                    The carcass was in good condition (fresh/edible). Normal
                    appearance, usually with little scavenger damage; fresh
                    smell; minimal drying and wrinkling of skin, eyes and mucous
                    membranes; eyes clear; carcass not bloated, tongue and penis
                    not protruded; blubber firm and white; muscles firm, dark
                    red, well-defined; blood cells intact, able to settle in a
                    sample tube; serum unhemolyzed; viscera intact and
                    well-defined, gut contains little or no gas; brain firm with
                    no discoloration, surface features distinct, easily removed
                    intact.
                </dd>
                <dt>moderate decomposition</dt>
                <dd>
                    The carcass was in fair condition (decomposed, but organs
                    basically intact). Carcass intact, bloating evident (tongue
                    and penis protruded) and skin cracked and sloughing;
                    possible scavenger damage; characteristic mild odor; mucous
                    membranes dry, eyes sunken or missing; blubber blood-tinged
                    and oily; muscles soft and poorly defined; blood hemolyzed,
                    uniformly dark red; viscera soft, friable, mottled, but
                    still intact; gut dilated by gas; brain soft, surface
                    features distinct, dark reddish cast, fragile but can
                    usually be moved intact.  
                </dd>
                <dt>advanced decomposition</dt>
                <dd>
                    The carcass was in poor condition (advanced decomposition).
                    Carcass may be intact, but collapsed; skin sloughing;
                    epidermis of cetaceans may be entirely missing; often severe
                    scavenger damage; strong odor; blubber soft, often with
                    pockets of gas and pooled oil; muscles nearly liquefied and
                    easily torn, falling easily off bones; blood thin and black;
                    viscera often identifiable but friable, easily torn, and
                    difficult to dissect; gut gas-filled; brain soft, dark red,
                    containing gas pockets, pudding-like consistency.
                </dd>
                <dt>skeletal</dt>
                <dd>
                    Carcass was mummified or skeletal remains. Skin may be
                    draped over skeletal remains; any remaining tissues are
                    desiccated.
                </dd>
            </dl>
        ''',
    )
    
    indication_entanglement = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "Indication of Entanglement?",
        help_text= u"""Was there any indication the animal had been entangled? This includes scars and wounds likely due to entanglement, as well as gear present. Note that entanglement cases shouldn't be created unless there is actual gear on the animal.""",
    )
    
    indication_shipstrike = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "Indication of Shipstrike?",
        help_text= u"""Was there any indication the animal had been struck? Note that this may or may not fulfill the criterea for a shipstrike case.""",
    )

    # note that wounded is for injuries, 'wound_description' is for maladies in
    # general
    wounded = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        help_text= "were there any wounds? No means none were observered, Yes means they were, Unknown means we don't know whether any were observed or not.",
        verbose_name= "wounds observed?",
    )

    wound_description = models.TextField(
        blank= True,
        verbose_name= 'body condition and wounds description',
        help_text= "Note the general condition of the animal: is it emaciated, robust, where are there visible parasites, etc. Describe wounds, noting severity and location on the animal.",
    )

    documentation = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name= 'documentation?',
        help_text= "Were any photos or videos taken?",
    )
    
    tagged = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "Were any tags put on the animal? If so, please note the tag ID's in the narrative.",
        verbose_name= "was a tag put on the animal?",
    )
    
    biopsy = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "Were any biopsy samples taken?",
        verbose_name= "biopsy samples taken?",
    )
    
    genetic_sample = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "Were any genetic samples taken?",
        verbose_name= "genetic samples taken?",
    )
    
    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.id)]) 

    def get_edit_url(self):
        return reverse('edit_observation', args=[self.id])

    def __unicode__(self):
        ret = 'observation '
        if self.datetime_observed:
            ret += "at %s " % self.datetime_observed.to_unicode(unknown_char=None)
        if self.observer:
            ret += "by %s " % self.observer
        ret += ( "(#%06d)" % self.id if self.id else "(unsaved!)" )
        return ret
    
    objects = ObservationManager()
    
    def clean(self):
        if self.animal_length and not self.animal_length_sigdigs:
            sign, digits, exponent = self.animal_length.as_tuple()
            self.animal_length_sigdigs = len(digits)
    
    def get_observation_extensions(self):
        
        # TODO don't hard-code these names
        oe_fields = ('entanglements_entanglementobservation', 'shipstrikes_shipstrikeobservation')
        
        observation_extensions = []
        for oe_field in oe_fields:
            try:
                oe = getattr(self, oe_field)
                observation_extensions.append(oe)
            except ObjectDoesNotExist:
                pass
        
        return tuple(observation_extensions)

    class Meta:
        app_label = 'incidents'
        ordering = ['datetime_observed', 'datetime_reported', 'id']

# prevent deletes from cascading to an Observation
for m, rm, fn in (
    (Animal, Observation, 'animal'),
    (Contact, Observation, 'observer'),
    (Contact, Observation, 'reporter'),
    (Taxon, Observation, 'taxon'),
):
    guard_deletes(m, rm, fn)

class ObservationExtension(models.Model):
    '''\
    Classes that want to add sets of fields to Observations can subclass this.
    E.g. entanglement-specific fields (which will only be needed if an
    Observation is relevant to an Entanglement Case) can be put in a subclass of
    this. It doesn't make sense to subclass Observation for that, since an
    Observation instance may have multiple ObservationExtensions that go with
    it.
    '''
    
    # EntanglementObservation and ShipstrikeObservation used to be subclasses of 
    # Observation, but now that Observations can be for multiple cases, an
    # Observation could be for both an Entanglement and a Shipstrike. But we
    # keep the field Django generated for multitable inheritance so the database
    # schema doesn't change.
    observation_ptr = models.OneToOneField(
        Observation,
        primary_key= True,
        editable= False,
        related_name= '%(app_label)s_%(class)s',
    )
    
    _extra_context = {}
    
    def get_observation_view_data(self):
        return {}
    
    def __unicode__(self):
        return "additional data for %s" % (self.observation_ptr)
    
    class Meta:
        abstract = True


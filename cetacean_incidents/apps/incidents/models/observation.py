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

from cetacean_incidents.apps.clean_cache import (
    CacheDependency,
    TestList,
)

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
    
    def _get_next_or_previous(self, is_next, **kwargs):
        qs = self.__class__.objects.filter(**kwargs)
        
        # 'gt' and 'lt' don't make sense on UncertainDateTime fields, so we 
        # need to use 'gte' and 'lte'
        if is_next:
            op = 'gte'
            order = ''
        else:
            op = 'lte'
            order = '-'
        try:
            for f in ('datetime_observed', 'datetime_reported', 'pk'):
                qs = qs.filter(**{f + '__' + op: getattr(self, f)}).order_by(order + f)
                candidate = qs[1] # 0 will be self
                if getattr(candidate, f) != getattr(self, f):
                    return candidate

        except IndexError:
            raise self.DoesNotExist("%s matching query does not exist." % self.__class__._meta.object_name)
    
    def get_next(self, **kwargs):
        return self._get_next_or_previous(is_next=True, **kwargs)

    def get_previous(self, **kwargs):
        return self._get_next_or_previous(is_next=False, **kwargs)
    
    # some predefined kwargs for use with templates
    def get_animal_next(self, **kwargs):
        kwargs['animal'] = self.animal
        return self._get_next_or_previous(is_next=True, **kwargs)
    
    def get_animal_previous(self, **kwargs):
        kwargs['animal'] = self.animal
        return self._get_next_or_previous(is_next=False, **kwargs)
    
    def get_case_next(self, case, **kwargs):
        if not self.cases.filter(pk=case.pk).exists():
            raise ValueError("this observation isn't for case %s" % case)
        kwargs['cases'] = case
        return self.get_next(**kwargs)
    
    def get_case_previous(self, case, **kwargs):
        if not self.cases.filter(pk=case.pk).exists():
            raise ValueError("this observation isn't for case %s" % case)
        kwargs['cases'] = case
        return self.get_previous(**kwargs)

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
        verbose_name= '# of significant digits in animal length',
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
        help_text= u"""Anything that would help identify the individual animal or its species or age or sex, etc. Even if those are specified above, please note what that was on the basis of.""",
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
            **carcass condition definitions**:

                fresh dead
                    The carcass was in good condition (fresh/edible). Normal
                    appearance, usually with little scavenger damage; fresh
                    smell; minimal drying and wrinkling of skin, eyes and mucous
                    membranes; eyes clear; carcass not bloated, tongue and penis
                    not protruded; blubber firm and white; muscles firm, dark
                    red, well\u2010defined; blood cells intact, able to settle
                    in a sample tube; serum unhemolyzed; viscera intact and
                    well\u2010defined, gut contains little or no gas; brain firm
                    with no discoloration, surface features distinct, easily
                    removed intact.

                moderate decomposition
                    The carcass was in fair condition (decomposed, but organs
                    basically intact). Carcass intact, bloating evident (tongue
                    and penis protruded) and skin cracked and sloughing;
                    possible scavenger damage; characteristic mild odor; mucous
                    membranes dry, eyes sunken or missing; blubber
                    blood\u2010tinged and oily; muscles soft and poorly defined;
                    blood hemolyzed, uniformly dark red; viscera soft, friable,
                    mottled, but still intact; gut dilated by gas; brain soft,
                    surface features distinct, dark reddish cast, fragile but
                    can usually be moved intact.

                advanced decomposition
                    The carcass was in poor condition (advanced decomposition).
                    Carcass may be intact, but collapsed; skin sloughing;
                    epidermis of cetaceans may be entirely missing; often severe
                    scavenger damage; strong odor; blubber soft, often with
                    pockets of gas and pooled oil; muscles nearly liquefied and
                    easily torn, falling easily off bones; blood thin and black;
                    viscera often identifiable but friable, easily torn, and
                    difficult to dissect; gut gas\u2010filled; brain soft, dark
                    red, containing gas pockets, pudding\u2010like consistency.

                skeletal
                    Carcass was mummified or skeletal remains. Skin may be
                    draped over skeletal remains; any remaining tissues are
                    desiccated.
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
    
    gear_present = models.NullBooleanField(
        blank= True,
        null= True,
        default= None,
        verbose_name= "Gear present?",
        help_text= u"""Was there any gear on the animal at any time during the observation?""",
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
    
    def get_html_options(self):
        options = super(Observation, self).get_html_options()

        options['template'] = 'observation.html'
        
        if not 'context' in options:
            options['context'] = {}
        dead = self.animal.determined_dead_before
        if not dead is None:
            start = self.earliest_datetime.date()
            end = self.latest_datetime.date()
            options['context']['dead'] = (dead <= end)
            options['context']['dead_during'] = (dead >= start and dead <= end)
        
        # dead depends on animal.detertermined_dead_before,
        # earliest_datetime.date(), and latest_datetime.date()
        # also, __unicode__ depends on datetime_observed, observer, and id
        if not 'cache_deps' in options:
            options['cache_deps'] = CacheDependency()
        deps = CacheDependency(
            update= {
                self: TestList([True]),
                self.animal: TestList([True]),
                self.observer: TestList([True]),
            },
            delete= {
                self: TestList([True]),
                self.animal: TestList([True]),
                self.observer: TestList([True]),
            },
        )
        options['cache_deps'] |= deps
        
        return options
    
    def __unicode__(self):
        ret = 'observation '
        if self.datetime_observed:
            ret += "at %s " % self.datetime_observed.to_unicode(unknown_char=None)
        # using a reference to another model in the unicode representation of
        # this one is a bit risky, so be cautious of inconsistent databases.
        try:
            if self.observer:
                ret += "by %s " % self.observer
        except Contact.DoesNotExist:
            ret += "by <non\u2010existant observer>"
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
    (Location, Observation, 'location'),
    (VesselInfo, Observation, 'observer_vessel'),
):
    guard_deletes(m, rm, fn)

class ObservationExtension(models.Model):
    '''\
    Classes that want to add sets of fields to Observations can subclass this.
    E.g. entanglement\u2010specific fields (which will only be needed if an
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
    
    class Meta:
        abstract = True


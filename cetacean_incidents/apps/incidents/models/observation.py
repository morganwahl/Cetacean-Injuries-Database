# -*- encoding: utf-8 -*-

import datetime
import pytz

from django.core.urlresolvers import reverse
from django.db import models

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.vessels.models import VesselInfo

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from animal import GENDERS

class ObservationManager(models.Manager):

    def observer_set(self):
        '''\
        Returns a list of observers (Contact instances) for these observations.
        '''
        
        observers = self.values_list('observer', flat=True)
        observers = frozenset(observers)
        observers = Contact.objects.filter(id__in=observers)
        
        return observers

class Observation(Documentable):
    '''\
    The heart of the database: observations. 
    
    An Obsevation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report.

    Many of the references to other tables (specifically, observer_vessel, and
    location) are one-to-one relationships; the other tables exist just to make
    programming easier, since they are logical sets of fields.
    '''
    
    @property
    def relevant_observation(self):
        return self

    case = models.ForeignKey(
        'Case',
        help_text= 'the case that this observation is part of',
    )
    @property
    def relevant_case(self):
        return self.case
    
    initial = models.BooleanField(
        default= False,
        verbose_name= u"is this an \u2018initial observation\u2019 on a Level A?",
        help_text= u"Check if this observation corresponds to the \u2018initial observation\u2019 on a Level A form. If it does, the obeservation date should correspond to the \"date of initial observation\" on the Level A, and the condition should correspond to the \"condition at initial observation\".",
    )
    exam = models.BooleanField(
        default= False,
        verbose_name= u"is this a \u2018Level A Examination\u2019?",
        help_text= u"Check if this observation corresponds to the \u2018level a examination\u2019 on a Level A form. If it does, the observation date should correspond to the date of examination on the Level A, the codition should correspond to the \"condition at examination\", and the observer should correspond to the \"examiner\". Note that an observation can be both the \u2018initial observation\u2019 and the \u2018examination\u2019 (or neither).",
    )
    
    observer = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'who actually saw the animal'
    )
    observer_vessel = models.OneToOneField(
        VesselInfo,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    datetime_observed = UncertainDateTimeField(
        help_text= "When did the observer see it? (Strictly, when did the observation start?) This earliest datetime_observed for a case's observations  is the one used for the case itself, e.g. when assigning a case to a year.",
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
    
    ashore = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "Was the animal ashore? Pick 'yes' even if it came ashore during the observation.",
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
        help_text = 'when we first heard about the observation',
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
        now = datetime.datetime.now(pytz.utc)
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
        help_text= 'The most specific taxon (e.g. a species) the animal is described as.',
    )

    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The gender of this animal, if known.',
        verbose_name = 'sex', # yes, it's not really verbose, but this is easier
                              # than changing the name of the column in the 
                              # database for now.
    )
    
    age_class = models.CharField(
        max_length= 2,
        blank= True,
        choices= (
            ('ca', 'calf'),
            ('ju', 'juvenile'),
            ('ad', 'adult'),
        ),
        help_text= u"""\
            Note that these are somewhat subjective, and their definitions, if
            any, certainly depend on the animal's species. In general,
            \u2018pup\u2019 is a synonym for \u2018calf\u2019 and
            \u2018sub-adult\u2019 for \u2018juvenile\u2019.
        """,
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
    
    animal_description = models.TextField(
        blank= True,
        help_text= """\
            Please note anything that would help identify the individual animal
            or it's species or gender, etc. Even if you've indicated those
            already, please indicate what that was on the basis of.
        """,
    )
    
    documentation = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any photos or videos taken?",
    )
    
    biopsy = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any biopsy samples taken?",
        verbose_name= "biopsy samples taken?",
    )
    
    genetic_sample = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any genetic samples taken?",
        verbose_name= "genetic samples taken?",
    )
    
    tagged = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any tags put on the animal?",
        verbose_name= "was a tag put on the animal?",
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
    
    narrative = models.TextField(
        blank= True,
        help_text= "complete description of the observation."
    )
    
    import_notes = models.TextField(
        blank= True,
        #editable= False, # note that this only means it's not editable in the admin interface
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.id)]) 

    def get_edit_url(self):
        return reverse('edit_observation', args=[self.id])

    def __unicode__(self):
        ret = 'observation '
        if self.datetime_observed:
            ret += "at %s " % self.datetime_observed.__unicode__(unknown_char=None)
        if self.observer:
            ret += "by %s " % self.observer
        ret += ( "(#%06d)" % self.id if self.id else "(unsaved!)" )
        return ret
    
    objects = ObservationManager()
    
    class Meta:
        app_label = 'incidents'
        ordering = ['datetime_observed', 'datetime_reported', 'id']


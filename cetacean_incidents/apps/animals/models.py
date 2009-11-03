import operator

from django.db import models
from cetacean_incidents.apps.people.models import Person, Organization
from cetacean_incidents.apps.vessels.models import Vessel
from cetacean_incidents.apps.locations.models import Location
from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import USStateField
from utils import probable_gender, probable_taxon

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class Taxon(models.Model):
    '''\
    A taxon is a generic term for a grouping of organisms made by a taxonimist.
    Whether it's a genus or a species (or a subspecies or a infragenus, etc.) is
    somewhat arbitrary, although a standardized system is the goal of the ICZN.
    For our purposes, we have taxons with very well-accepted ranks (basically
    just genus and species).
    '''
    
    MAIN_RANKS = (
        ('O', 'order'),
        ('F', 'family'),
        ('G', 'genus'),
        ('S', 'species'),
    )
    # generate the super-, sub-, and infra-, ranks
    # note that this function takes a pair and returns a 4-tuple of pairs
    expand = lambda r : (
        ('u' + r[0], 'super' + r[1]),
        r,
        ('b' + r[0], 'sub'   + r[1]),
        ('i' + r[0], 'infra' + r[1]),
    )
    ALL_RANKS = map(expand, MAIN_RANKS)
    # ALL_RANKS is now a list of 4-tuples of pairs
    ALL_RANKS = reduce( lambda t1, t2: t1 + t2, ALL_RANKS )
    # ALL_RANKS is now a list of pairs
    ALL_RANKS = tuple(ALL_RANKS)
    
    name = models.CharField(
        max_length= 255,
        help_text= 'The scientific name for this taxon (i.e. the one in Latin).',
        verbose_name= 'scientific name',
    )
    common_name = models.CharField(
        max_length = 255,
        blank= True,
        help_text= "a comma-delimited list of common English name(s) for " + 
                   'this taxon (e.g. "humpback whale" or "dolphins, ' +
                   'porpises").',
    )
    supertaxon = models.ForeignKey(
        'self',
        null= True,
        blank= True,
        related_name='subtaxons',
        help_text="The smallest taxon that contains this one",
    )
    rank = models.CharField(max_length=2, choices= ALL_RANKS)
    
    class Meta:
        ordering = ['name']
        #order_with_respect_to = 'supertaxon'
        verbose_name = 'taxon'
        verbose_name_plural = 'taxa'
        
    def __unicode__(self):
        if self.rank == 'S':
            genus = self
            while genus.rank != 'G' and genus.supertaxon is not None:
                genus = genus.supertaxon
            if genus.rank == 'G':
                return u'%s. %s' % (genus.name[0], self.name)
        return u'%s %s' % (self.name, self.get_rank_display())

class Animal(models.Model):
    name = models.CharField(
        max_length= 255,
        help_text= 'The name given to this particular animal (e.g. "Kingfisher"). Not an ID number.'
    )
    
    def _get_probable_gender(self):
        return probable_gender(self.observation_set)
    probable_gender = property(_get_probable_gender)
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific events',
    )
    
    def _get_probable_taxon(self):
        return probable_taxon(self.observation_set)
    probable_taxon = property(_get_probable_taxon)
    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'as determined from the taxa indicated in specific events',
    )
    
    def _get_possible_parents(self):
        # observations where this Animal is in the offspring relationship
        child_obvs = self.child_of.all()
        
        # observations of this Animal where something is in the parents 
        # relationship
        parent_obvs = self.observation_set.filter(parents__isnull=False)
        # TODO merge the two above queries into one big one
        return frozenset( 
            map(lambda obv: obv.animal, child_obvs)
            + reduce(
                operator.add, 
                map(lambda obv: list(obv.parents.all()), parent_obvs),
                [],
            )
        )
    parents = property(_get_possible_parents)
    
    def _get_possible_mothers(self):
        '''\
        Returns a set of Animals that _may_ be parents of this one and are 
        possibly female.
        '''
        return frozenset(filter(
            lambda animal: animal.possibly_female,
            self.parents,
        ))
    possible_mothers = property(_get_possible_mothers)
    def _get_probable_mothers(self):
        '''\
        Returns a set of Animals that _may_ be parents of this one and are 
        probably female.
        '''
        return frozenset(filter(
            lambda animal: animal.probably_female,
            self.parents,
        ))
    probable_mothers = property(_get_probable_mothers)
    
    def __unicode__(self):
        if self.name:
            return self.name
        return "animal %s" % self.pk
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 

class Tag(models.Model):
    id_number = models.CharField(
        max_length= 255,
        blank= True,
    )
    color = models.CharField(
        max_length= 255,
        blank= True,
    )
    type = models.CharField(
        max_length= 255,
        blank= True,
    )
    frequency = models.FloatField(
        blank= True,
        null= True,
    )
    PLACEMENTS = (
        ('D', 'dorsal'),
        ('DF', 'dorsal fin'),
        ('L', 'lateral body'),
        ('LF', 'left front'),
        ('LR', 'left rear'),
        ('RF', 'right front'),
        ('RR', 'right rear'),
    )
    placement = models.CharField(
        max_length= 2,
        choices = PLACEMENTS,
        blank= True,
    )
    
    def __unicode__(self):
        if self.id_number:
            return unicode(self.id_number)
        parts = []
        desc = ''
        if self.pk:
            parts.append(unicode(self.pk))
        if self.color:
            parts.append(unicode(self.color))
        if self.placement:
            parts.append(self.get_placement_display())
        if self.type:
            parts.append(unicode(self.type))
        return u' '.join(parts + [u'tag'])

class TagObservation(models.Model):
    tag = models.ForeignKey(Tag)
    observation = models.ForeignKey('Observation')
    added = models.BooleanField(
        verbose_name= 'was it added during this observation?',
    )
    tagging_person = models.ForeignKey(Person, blank=True, null=True)
    tagging_org = models.ForeignKey(Organization, blank=True, null=True)
    tagging_date = models.DateField(blank=True)

class Observation(models.Model):
    '''\
    An observation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken.
    '''
    
    date = models.DateField(
        blank= True,
        null= True,
    )
    time = models.TimeField(
        blank= True,
        null= True,
    )
    observer = models.ForeignKey(
        Person,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    observer_comments = models.TextField(
        blank= True,
        help_text= "any additional observations about the animal?"
    )
    vessel = models.ForeignKey(
        Vessel,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    firsthand = models.BooleanField(
        blank= True,
        help_text= 'Is this a firsthand report?',
    )
    
    location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
        related_name= "observed_here",
    )
    
    animal_movement = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        help_text= "i.e. anchored, stranded, traveling",
    )
    animal_heading = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        help_text= "i.e. north, southwest, circling, random, unknown",
    )
    
    video_taken = models.NullBooleanField(
        blank= True,
    )
    photos_taken = models.NullBooleanField(
        blank= True,
    )
    media_taken = models.BooleanField(
        blank= True,
        verbose_name = "Photos / Videos taken",
    )
    media_taker = models.CharField(
        max_length = 255,
        blank= True,
    )
    media_loc = models.CharField(
        max_length= 1023,
        blank= True,
        verbose_name = "Photos / Videos disposition",
    ) # TODO implies media_taken
    
    animal = models.ForeignKey('Animal')
    reported_name = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "The identification orginally made by the observer. Noted " +
            "here in case it turns out to be incorrect."
    )
    taxon = models.ForeignKey(
        Taxon,
        help_text= 'The most specific taxon that can be applied to this ' +
            'animal. (e.g. a species)',
    )
    TAXON_METHODS=(
        ("p", "photo(s)"),
        ("v", "video(s)"),
        ("g", "genetics"),
        ("m", "morphology"),
    )
    taxon_method = models.CharField(
        "How was the species determined?",
        max_length= 1,
        choices= TAXON_METHODS,
        blank= True,
        help_text= 'leave blank if unknown'
    )

    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The gender of this animal, if known.'
    )
    GENDER_METHODS = (
        ('p', 'physical exam'),
        ('g', 'genetics'),
        ('c', 'presence of calf'),
        ('o', 'visual observation'),
    )
    gender_method = models.CharField(
        "Method for determining gender",
        max_length= '1',
        choices= GENDER_METHODS,
        blank= True,
        help_text= "leave blank if unknown",
    )
    
    # use ints so they're orderable
    AGE_GROUPS = (
        (1, 'pup / calf'),
        (2, 'yearling'),
        (3, 'subadult'),
        (4, 'adult'),
    )
    age_group = models.SmallIntegerField(
        "Age-group",
        choices= AGE_GROUPS,
        blank= True,
        null= True,
        help_text= "leave blank if unknown",
    )
    AGE_METHODS = (
        ('b', "biopsy"),
        ('o', "visual observation"),
        ('p', "photo(s)"),
        ('v', "video(s)"),
    )
    age_method = models.CharField(
        "Method for determining age-group",
        max_length= 1,
        choices= AGE_METHODS,
        blank= True,
        help_text= "leave blank if unknown",
    )
    
    length = models.FloatField(
        "Estimated length in meters",
        blank= True,
        null= True,
        help_text= "leave blank if no estimation was made",
    )
    LENGTH_METHODS = (
        ('o', "visual observation"),
        ('p', "photo(s)"),
        ('v', "video(s)"),
    )
    length_method = models.CharField(
        max_length= 1,
        choices = LENGTH_METHODS,
        blank= True,
        help_text= "leave blank if no estimation was made",
    )
    
    weight = models.FloatField(
        "weight in kilograms",
        blank= True,
        null= True,
        help_text= "leave blank if no estimation was made",
    )
    WEIGHT_METHODS = (
        ('o', 'visual observation'),
        ('s', 'a big scale'),
    )
    weight_method = models.CharField(
        max_length= 1,
        choices = WEIGHT_METHODS,
        blank= True,
        help_text= "how was the weight measured, if at all",
    )
    
    animal_description = models.TextField(
        blank= True,
    )
    
    # TODO can't be same as animal
    # TODO better related name.
    offspring = models.ManyToManyField(
        'Animal',
        blank= True,
        null= True,
        related_name= 'child_of',
    )
    # TODO at most 2 parents. can't be same as animal
    # TODO better related name.
    parents = models.ManyToManyField(
        'Animal',
        blank= True,
        null= True,
        related_name= 'parent_of',
        help_text= "if another animal was determined to be one of it's parents"
    )
    associates = models.ManyToManyField(
        'Animal',
        blank= True,
        null= True,
        related_name= 'associated_of',
        help_text= 'seen in association with',
    )

    # tag data
    # see django ticket #999 for why this fields can't be 'tags'
    tags_seen = models.ManyToManyField(
        'Tag',
        through='TagObservation',
        blank= True,
        null= True,
    )
    
    def __unicode__(self):
        ret = "visit of %s" % self.animal
        if self.date:
            ret += " on %s" % self.date
        if self.observer:
            ret += " by %s" % self.date
        ret += " (%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['date', 'time', 'animal']

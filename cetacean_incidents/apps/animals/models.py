import operator

from django.db import models
from cetacean_incidents.apps.contacts.models import Contact, Organization
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
    _expand = lambda r : (
        ('u' + r[0], 'super' + r[1]),
        r,
        ('b' + r[0], 'sub'   + r[1]),
        ('i' + r[0], 'infra' + r[1]),
    )
    ALL_RANKS = map(_expand, MAIN_RANKS)
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
        if self.get_rank_display() == 'species':
            genus = self
            while genus.get_rank_display() != 'genus' and genus.supertaxon is not None:
                genus = genus.supertaxon
            if genus.get_rank_display() == 'genus':
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
    
    def __unicode__(self):
        if self.name:
            return self.name
        return "animal %s" % self.pk
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 

class Observation(models.Model):
    '''\
    An observation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report.
    '''

    observer = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    observer_vessel = models.ForeignKey(
        Vessel,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    date = models.DateField(
        blank= True,
        null= True,
        help_text= 'the date that (start of) the observation took place',
    )
    time = models.TimeField(
        blank= True,
        null= True,
        help_text= 'the time of the beginning of the observation',
    )
    # TODO duration?

    def _is_firsthand(self):
        return self.reporter == self.observer
    firsthand = property(_is_firsthand)
    reporter = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'reported',
        help_text= '''\
            Same as observer if this is a firsthand report. If not, this is the
            person who either created this entry in the database, or filled out
            the form that was then imported into the database.
        ''',
    )
    date_reported = models.DateField(
        blank= True,
        null= True,
    )
    time_reported = models.TimeField(
        blank= True,
        null= True,
    )

    location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
        related_name= "observed_here",
    )
    
    taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'The most specific taxon that can be applied to this ' +
            'animal. (e.g. a species)',
    )

    gender = models.CharField(
        max_length= 1,
        choices= GENDERS,
        blank= True,
        help_text= 'The gender of this animal, if known.'
    )
    
    animal = models.ForeignKey(Animal)
    
    animal_description = models.TextField(
        blank= True,
        help_text= """\
        Please note anything that would help identify the individual animal or
        it's species or gender, etc. Even if you've determined those already,
        please indicate what that was on the basis of.
        """
    )
    
    def __unicode__(self):
        ret = "visit"
        if self.date:
            ret += " on %s" % self.date
        if self.observer:
            ret += " by %s" % self.observer
        ret += " (%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['date', 'time', 'id']
class Media(models.Model):
    
    observation = models.ForeignKey(Observation)
    media_type = models.CharField(
        max_length= 1,
        choices = (
            ('p', 'photos'),
            ('v', 'video'),
        ),
    )
    contact = models.ManyToManyField(
        Contact,
        blank= True,
        null= True,
        help_text= "Who should be contacted for copies of the media?",
    )


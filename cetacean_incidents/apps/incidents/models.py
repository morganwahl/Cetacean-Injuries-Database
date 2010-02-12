from django.db import models
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon
from cetacean_incidents.apps.contacts.models import Contact, Organization
from cetacean_incidents.apps.datetime.models import DateTime
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.vessels.models import VesselInfo, StrikingVesselInfo
from utils import probable_gender

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class Animal(models.Model):
    name = models.CharField(
        blank= True,
        null= True,
        max_length= 255,
        help_text= 'The name given to this particular animal (e.g. "Kingfisher"). Not an ID number.'
    )
    
    determined_dead_before = models.DateField(
        blank= True,
        null= True,
        help_text= "A date when the animal was certainly dead, as determined from the observations of this animal. Useful for error-checking (i.e. if an animal is marked as not dead in an observation after this date, a warning will be displayed.)"
    )
    necropsy = models.BooleanField(
        default= False,
        help_text= "if this animal is dead, has a necropsy been performed on it?",
    )
    
    def _get_probable_gender(self):
        return probable_gender(self.observation_set)
    probable_gender = property(_get_probable_gender)
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific observations',
    )
    
    def _get_probable_taxon(self):
        return probable_taxon(self.observation_set)
    probable_taxon = property(_get_probable_taxon)
    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'as determined from the taxa indicated in specific observations',
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
    An Obsevation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report. It's an
    abstract model for the common fields between different types of Observations.
    '''

    case = models.ForeignKey('Case')
    
    observer = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'observed',
    )
    observer_vessel = models.ForeignKey(
        VesselInfo,
        blank= True,
        null= True,
        unique= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    observation_datetime = models.ForeignKey(
        DateTime,
        unique = True,
        help_text= 'the start of the observation',
        related_name= 'observation',
    )
    # TODO duration?
    location = models.ForeignKey(
        Location,
        blank= True,
        null= True,
        unique= True,
        related_name= "observation",
    )

    def _is_firsthand(self):
        return self.reporter == self.observer
    firsthand = property(_is_firsthand)
    reporter = models.ForeignKey(
        Contact,
        blank= True,
        null= True,
        related_name= 'reported',
        help_text= '''\
            Same as observer if this is a firsthand report. If not, this is who
        informed us of the incidents.
        ''',
    )
    report_datetime = models.ForeignKey(
        DateTime,
        unique = True,
        help_text = 'when we first heard about the observation',
        related_name = 'report',
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
    
    animal_description = models.TextField(
        blank= True,
        help_text= """\
        Please note anything that would help identify the individual animal or
        it's species or gender, etc. Even if you've determined those already,
        please indicate what that was on the basis of.
        """
    )
    
    biopsy = models.BooleanField(
        default= False,
        help_text= "where any biopsy samples taken?",
    )
    
    wounded = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were there any wounds?"
    )
    wound_description = models.TextField(
        blank= True,
        help_text= "describe wounds, noting severity and location on the animal.",
    )

    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.id)]) 

    def __unicode__(self):
        ret = "observation on %s" % self.observation_datetime
        if self.observer:
            ret += " by %s" % self.observer
        ret += " (%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['observation_datetime', 'report_datetime', 'id']


class CaseManager(models.Manager):
    def cases_in_year(self, year):
        # case.date isn't acutally in the database; it the observation.report_datetime
        # of the observation with the earilest report_datetime. A simple approach here
        # is to get all the cases that have _any_ observation in the year, then prune
        # the one's whose date's aren't actually in the year
        cases = Case.objects.filter(observation__report_datetime__year__exact=year).distinct()
        return filter(lambda c: c.date.year == year, cases)

class Case(models.Model):
    '''\
    A Case is has all the data for _one_ incident of _one_ animal (i.e. a single strike of a ship, a single entanglement of an animal in a particular set of gear). Hypothetically the incident has a single datetime and place that it occurs, although that's almost never actually known. Cases keep most of their information in the form of a list of observations. They also serve to connect individual observations to animal entries.
    '''
    
    observation_model = Observation
    
    animal = models.ForeignKey(
        Animal,
    )

    ole_investigation = models.BooleanField(
        blank= True,
        verbose_name= "OLE Investigation",
        help_text= "Is there a corresponding Office of Law Enforcement investigation?",
    )
    
    yearly_number = models.IntegerField(
        blank= True,
        null= True,
        editable= False,
        help_text= "A number that's unique within cases whose case-dates have the same year. Note that this number can't be assigned until the case-date is defined, which doesn't happen until the a Observation is associated with it."
    )
    names = models.CharField(
        max_length= 2048,
        blank= False,
        editable= False,
        help_text= "Comma-separated list of autogenerated names with the format"
            + "<year>#<case # in year> (<date>) <type> of <taxon>"
    )
    def _get_names_set(self):
        names = filter(lambda x: x != '', self.names.split(','))
        return frozenset(names)
    def _put_names_set(self, new_names):
        # TODO should the names-set be the union of the one passed and the
        # current one? This makes sense because once assigned, names should
        # never be removed. But, do we want to enforce that at this level?
        self.names = ','.join(new_names)
    names_set = property(_get_names_set,_put_names_set)

    def _get_current_name(self):
        # Cases with no Observations yet don't get names
        if not self.observation_set.count():
            return None
        s = {}
        s['year'] = unicode(self.date.year)
        s['yearly_number'] = self.yearly_number
        s['date'] = unicode(self.date)
        taxon = self.probable_taxon
        if not taxon is None:
            s['taxon'] = unicode(taxon)
        else:
            s['taxon'] = u'Unknown taxon'
        s['type'] = self.case_type
        return u"%(year)s#%(yearly_number)i (%(date)s) %(type)s of %(taxon)s" % s
        
    current_name = property(_get_current_name)

    def _get_past_names_set(self):
        return self.names_set - set([self.current_name])
    past_names_set = property(_get_past_names_set)

    def _get_first_observation_date(self):
        return self.observation_set.order_by('observation_datetime')[0].observation_datetime
    first_observation_date = property(_get_first_observation_date)
    def _get_first_report_date(self):
        return self.observation_set.order_by('report_datetime')[0].report_datetime
    first_report_date = property(_get_first_report_date)
    def _get_case_date(self):
        if not self.observation_set.count():
            return None
        # TODO more specific dates should override less specific ones
        return self.first_report_date
    date = property(_get_case_date)

    def save(self, *args, **kwargs):
        # if we don't have a yearly_number, set one if possible
        if self.yearly_number is None and (not self.date is None):
            year = self.date.year
            # TODO more efficient way
            highest_so_far = 0
            for c in Case.objects.cases_in_year(year):
                if c.yearly_number:
                    highest_so_far = max(highest_so_far, c.yearly_number)
            self.yearly_number = highest_so_far + 1

        # add the current_name to the names set, if necessary
        if not self.current_name is None:
            if not self.current_name in self.names_set:
                self.names_set |= frozenset([self.current_name])

        return super(Case, self).save(*args, **kwargs)

    # TODO there's probably a way to get a list of all the subclasses,
    # but for now we'll just add them one-by-one.
    _subclasses = set()
    @classmethod
    def register_subclass(clas, subclass):
        clas._subclasses.add(subclass)
    detailed_classes = property(lambda : frozenset(_subclasses))
    def _get_detailed_instance(self):
        '''Get the more specific instance of this Case, if any.'''
        for clas in self._subclasses:
            subcases = clas.objects.filter(case_ptr= self.id)
            if subcases.count():
                return subcases.all()[0]
        return self
    def _get_detailed_class_name(self):
        return self._get_detailed_instance().__class__.__name__
    detailed = property(_get_detailed_instance)
    detailed_class_name = property(_get_detailed_class_name) 
    case_type = detailed_class_name
    
    def _get_probable_taxon(self):
        return probable_taxon(self.observation_set)
    probable_taxon = property(_get_probable_taxon)
    
    def _get_probable_gender(self):
        return probable_gender(self.observation_set)
    probable_gender = property(_get_probable_gender)
    
    def __unicode__(self):
        if self.current_name is None:
            if self.id:
                return u"Case %i" % self.id
            else:
                return u"<new case>"
        return self.current_name

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 
    
    objects = CaseManager()
    
# since adding a new Observation whose case is this could change things like
# case.date or even assign yearly_number, we need to listen for Observation
# saves
def _observation_post_save(sender, **kwargs):
    observation = kwargs['instance']
    observation.case.save()
models.signals.post_save.connect(_observation_post_save, sender=Observation)

class EntanglementObservation(Observation):
    outcome = models.TextField(
        blank= True,
        help_text= "What was the situation at the end of this Observation? was the animal disentangled? Was it determined to be non-life-threatening? etc.",
    )

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=EntanglementObservation)

class Entanglement(Case):
    observation_model = EntanglementObservation

Case.register_subclass(Entanglement)

class ShipstrikeObservation(Observation):
    striking_vessel = models.ForeignKey(
        StrikingVesselInfo,
        blank= True,
        null= True,
    )

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=ShipstrikeObservation)

class Shipstrike(Case):
    observation_model = ShipstrikeObservation

Case.register_subclass(Shipstrike)


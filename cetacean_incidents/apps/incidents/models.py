# -*- encoding: utf-8 -*-

from django.db import models
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon
from cetacean_incidents.apps.contacts.models import Contact, Organization
from cetacean_incidents.apps.datetime.models import DateTime
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.vessels.models import VesselInfo, StrikingVesselInfo
from utils import probable_gender
import re

import reversion

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class Animal(models.Model):
    name = models.CharField(
        blank= True,
        null= True,
        max_length= 255,
        help_text= 'Name(s) given to this particular animal. E.g. “Kingfisher”, “RW #2427”.'
    )
    
    determined_dead_before = models.DateField(
        blank= True,
        null= True,
        help_text= "A date when the animal was certainly dead, as determined from the observations of this animal. Useful for error-checking; e.g. if an animal is marked as not dead in an observation after this date, a warning will be displayed."
    )
    necropsy = models.BooleanField(
        default= False,
        help_text= "if this animal is dead, has a necropsy been performed on it?",
    )
    
    def _get_observation_set(self):
        return Observation.objects.filter(case__animal=self)
    observation_set = property(_get_observation_set)
    
    def _get_probable_gender(self):
        return probable_gender(self.observation_set)
    probable_gender = property(_get_probable_gender)
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific observations',
    )
    def get_probable_gender_display(self):
        if self.probable_gender is None:
            return None
        return [g[1] for g in GENDERS if g[0] == self.probable_gender][0]
    
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
            return "%06d %s" % (self.id, self.name)
        return "%06d" % self.id
    
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
    observer_vessel = models.OneToOneField(
        VesselInfo,
        blank= True,
        null= True,
        related_name= 'observed',
        help_text= 'the vessel the observer was on, if any',
    )
    observation_datetime = models.OneToOneField(
        DateTime,
        blank= True,
        null= True,
        help_text= 'the start of the observation',
        related_name= 'observation',
    )
    # TODO duration?
    location = models.OneToOneField(
        Location,
        blank= True,
        null= True,
        related_name= "observation",
    )

    def _is_firsthand(self):
        if self.reporter is None and self.observer is None:
            return None
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
    report_datetime = models.OneToOneField(
        DateTime,
        help_text = 'when we first heard about the observation',
        related_name = 'report',
    )
        
    taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'The most specific taxon (e.g. a species) that can be applied to this animal.',
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
    
    documentation = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any photos or videos taken?",
    )
    
    biopsy = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "where any biopsy samples taken?",
    )
    
    tagged = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any tags put on the animal?",
    )
    
    wounded = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were there any wounds? False means none were observered, True means they were, Null means we don't know whether any were observed or not."
    )
    wound_description = models.TextField(
        blank= True,
        help_text= "describe wounds, noting severity and location on the animal.",
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

    def __unicode__(self):
        ret = 'observation '
        if self.observation_datetime:
            ret += "on %s " % self.observation_datetime
        if self.observer:
            ret += "by %s " % self.observer
        ret += "(%d)" % self.id
        return ret
    
    class Meta:
        ordering = ['observation_datetime', 'report_datetime', 'id']

# have revisions follow the OneToOne fields
reversion.register(Observation, 
    follow= [
        f.name for f in filter(
            lambda x: isinstance(x, models.OneToOneField),
            Observation._meta.fields
        )
    ],
)

class CaseManager(models.Manager):
    def cases_in_year(self, year):
        # case.date isn't acutally in the database; it the observation.report_datetime
        # of the observation with the earilest report_datetime. A simple approach here
        # is to get all the cases that have _any_ observation in the year, then prune
        # the one's whose date's aren't actually in the year
        cases = Case.objects.filter(observation__report_datetime__year__exact=year).distinct()
        return filter(lambda c: c.date.year == year, cases)

class YearCaseNumber(models.Model):
    '''\
    A little table to do the bookkeeping when assigning yearly-numbers cases. 
    'year' is a year, 'case' is a case, 'number' is any yearly_number
    held by that case for that year, including it's current one.
    
    Assigning unique numbers to each case in a year is complicated; once a 
    case-number in a given year has been assigned to a case, it mustn't ever
    be assigned to a different one, even if that case is changed to a different
    year or merged with another case. Ideally, if a case was assigned, say, 
    2003#67 and then it's date was changed to 2004, it would be assigned the
    next unused yearly_number for 2004. If it was then changed back to 2003,
    it would be assigned #67 again. Thus, this table stores all past and current
    year-case-yearly_number combinations. Current numbers are marked
    accordingly.
    '''
    
    year = models.IntegerField()
    case = models.ForeignKey('Case')
    number = models.IntegerField()
    current = models.BooleanField()
    
    class Meta:
        ordering = ('year', 'number')

class Case(models.Model):
    '''\
    A Case is has all the data for _one_ incident of _one_ animal (i.e. a single strike of a ship, a single entanglement of an animal in a particular set of gear). Hypothetically the incident has a single datetime and place that it occurs, although that's almost never actually known. Cases keep most of their information in the form of a list of observations. They also serve to connect individual observations to animal entries.
    '''
    
    observation_model = Observation
    
    animal = models.ForeignKey(
        Animal,
    )
    
    valid = models.IntegerField(
        choices= (
            (0, 'invalid'),
            (1, 'suspected'),
            (2, 'confirmed'),
        ),
        default= 1,
        verbose_name= 'Validity',
        help_text= "Invalid cases don't count towards year-totals."
    )
    
    ole_investigation = models.NullBooleanField(
        blank= True,
        null= True,
        default= False,
        verbose_name= "OLE Investigation",
        help_text= "Is there a corresponding Office of Law Enforcement investigation?",
    )
    
    #yearly_number = models.IntegerField(
    #    blank= True,
    #    null= True,
    #    editable= False,
    #    help_text= "A number that's unique within cases whose case-dates have the same year. Note that this number can't be assigned until the case-date is defined, which doesn't happen until the a Observation is associated with it."
    #)
    def _get_yearly_number(self):
        try:
            number = YearCaseNumber.objects.get(case=self, current=True).number
        except YearCaseNumber.DoesNotExist:
            number = None
        return number
    yearly_number = property(_get_yearly_number)
    
    names = models.TextField(
        #max_length= 2048,
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
        return u"%(year)s#%(yearly_number)d (%(date)s) %(type)s of %(taxon)s" % s
        
    current_name = property(_get_current_name)

    def _get_past_names_set(self):
        return self.names_set - set([self.current_name])
    past_names_set = property(_get_past_names_set)

    def _get_first_observation_date(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by('observation_datetime')[0].observation_datetime
    first_observation_date = property(_get_first_observation_date)
    def _get_first_report_date(self):
        if not self.observation_set.count():
            return None
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
        if self.date:
            def _next_number_in_year(year):
                this_year = YearCaseNumber.objects.filter(year=year)
                if this_year.count():
                    return this_year.order_by('-number')[0].number + 1
                else:
                    return 1
        
            # do we have a newly assigned date and no yearly-number?
            try:
                current_year_case_number = YearCaseNumber.objects.get(case=self, current=True)
                # is our current year different from the one in our current
                # yearly_number assignment
                if self.date.year != current_year_case_number.year:
                    current_year_case_number.current = False
                    current_year_case_number.save()
                    try:
                        # do we have a previous assignment for our current year?
                        new_year_case_number = YearCaseNumber.objects.get(case=self, year=self.date.year)
                        new_year_case_number.current = True
                    except YearCaseNumber.DoesNotExist:
                        # add a new entry for this year-case combo
                        new_year_case_number = YearCaseNumber(
                            case=self,
                            year=self.date.year,
                            number= _next_number_in_year(self.date.year),
                            current=True,
                        )
                    new_year_case_number.save()
            except YearCaseNumber.DoesNotExist:
                # assign a new number
                # find the highest number assigned in our year so far.
                new_year_case_number = YearCaseNumber(
                    case=self,
                    year=self.date.year,
                    number= _next_number_in_year(self.date.year),
                    current=True,
                )
                new_year_case_number.save()

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

def _get_observation_dates(contact):
    return DateTime.objects.filter(observation__observer=contact)
Contact.observation_dates = property(_get_observation_dates)
def _get_report_dates(contact):
    return DateTime.objects.filter(report__reporter=contact)
Contact.report_dates = property(_get_report_dates)

# since adding a new Observation whose case is this could change things like
# case.date or even assign yearly_number, we need to listen for Observation
# saves
def _observation_post_save(sender, **kwargs):
    observation = kwargs['instance']
    observation.case.save()
models.signals.post_save.connect(_observation_post_save, sender=Observation)

class EntanglementObservation(Observation):
    anchored = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "was the animal anchored?",
    )
    gear_description = models.TextField(
        blank= True,
        help_text= "describe the entangling gear",
    )
    entanglement_details = models.TextField(
        blank= True,
        help_text= "details of how the animal was entangled",
    )

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=EntanglementObservation)

class Entanglement(Case):
    observation_model = EntanglementObservation

    gear_fieldnumber = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        verbose_name= "Gear Field No.",
        help_text= "the gear-analysis-specific field no.",
    )

    gear_recovered = models.NullBooleanField(
        default= None,
        blank= True,
        null= True,
        help_text= "was any gear recovered?",
    )
    
    # TODO does gear_analyzed imply gear_recovered
    gear_analyzed = models.NullBooleanField(
        default= None,
        blank= True,
        null= True,
        help_text= "was the gear analyzed?",
    )
    analyzed_datetime = models.DateField(
        blank= True,
        null= True,
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
    )
    
    def _get_implied_geartypes(self):
        if not self.gear_types.count():
            return set()
        implied_geartypes = set()
        for geartype in self.gear_types.all():
            implied_geartypes |= geartype.implied_supertypes
        return frozenset(implied_geartypes - set(self.gear_types.all()))
    implied_gear_types = property(_get_implied_geartypes)

Case.register_subclass(Entanglement)

class GearTypeRelation(models.Model):
    '''\
    Intended to be used as the 'through' model in a ManyToManyField('self') 
    when implementing a Directed Acyclic Graph (DAG). Basically just does 
    cycle-checking when a new relation is added.
    '''
    
    class DAGException(Exception):
        '''\
        Exception thrown when a GearTypeRelation would violate the directed-
        acyclic-graph nature of GearTypes. E.g. when the subtype and supertype
        are the same.
        '''
        pass

    subtype = models.ForeignKey(
        'GearType',
        related_name= 'subtype_relations',
    )
    supertype = models.ForeignKey(
        'GearType',
        related_name= 'supertype_relations',
    )
    
    def save(self, *args, **kwargs):
        
        # check if this new relation would create a cycle in the DAG
        if self.subtype == self.supertype:
            raise self.DAGException(
                "\"%r\" can't be a supertype of itself!" % unicode(self.subtype),
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

class GearType(models.Model):
    name= models.CharField(
        max_length= 512,
    )
    supertypes= models.ManyToManyField(
        'self',
        through= GearTypeRelation,
        symmetrical= False,
        blank= True,
        null= True,
        related_name= 'subtypes',
        help_text= 'what other types would be implied by this type?'
    )
    
    def _get_implied_supertypes_with_ignore(self, ignore_types):
        # The ignore_types arg is a set of GearTypes that won't be included in 
        # the results. It's used to prevent infinite loops in recursive calls.
        
        # be sure 'self' is in ignore_types.
        ignore_types |= set([self])
        # traverse supertypes and return a set of all GearTypes seen
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
    
    # TODO cycle-check in get_attribute for supertypes, since you could change
    # the supertypes of an instance w/o saving it.
    
    def _cyclecheck(self):
        # check for cycles in supertypes!
        if self in self.supertypes.all():
            raise GearType.DAGException(
                "%s can't be a supertype of itself!" % unicode(self),
            )
        # assume no other instances in the database contain cycles. If so, 
        # there can only be a cycle if this instance is in the all_supertypes 
        # property of one of the GearTypes in its supertypes.
        checked_so_far = set([])
        for proposed_supertype in self.supertypes.all():
            to_check = proposed_supertype._get_implied_supertypes(
                ignore_types= checked_so_far,
            )
            if self in to_check:
                raise GearType.DAGException(
                    # TODO determined what the cycle would be
                    "%s can't be a supertype of %s, that would create a cycle!" % (
                        unicode(proposed_supertype),
                        unicode(self),
                    )
                )
            checked_so_far |= to_check # not strictly necessary, but makes 
                                       # things more efficient. TODO: it's 
                                       # still sub- optimal.

    
    def __unicode__(self):
        return self.name    

class ShipstrikeObservation(Observation):
    striking_vessel = models.OneToOneField(
        StrikingVesselInfo,
        blank= True,
        null= True,
    )

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=ShipstrikeObservation)

class Shipstrike(Case):
    observation_model = ShipstrikeObservation

Case.register_subclass(Shipstrike)


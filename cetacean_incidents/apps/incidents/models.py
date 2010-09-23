# -*- encoding: utf-8 -*-

import datetime
import pytz

from django.db import models
from cetacean_incidents.apps.contacts.models import Contact, Organization
from cetacean_incidents.apps.datetime.models import DateTime
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon
from cetacean_incidents.apps.vessels.models import VesselInfo
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
        help_text= 'Name(s) given to this particular animal. E.g. “Kingfisher”, “RW #2427”.'
    )
    
    determined_dead_before = models.DateField(
        blank= True,
        null= True,
        verbose_name= "determined dead on", # no, not really verbose, but it's
                                            # easier to change this than to
                                            # alter the fieldname in the schema
        help_text= '''\
            A date when the animal was certainly dead, as determined from the 
            observations of this animal. If you're unsure of an exact date, just
            put something certainly after it; e.g. if you know it was dead
            sometime in July of 2008, just put 2008-07-31 (or 2008-08-01). If
            you're totally unsure, just put the current date. Any animal with a
            date before today is considered currently dead. This field is useful
            for error-checking; e.g. if an animal is described as not dead in an
            observation after this date, something's not right.
        '''
    )
    
    # TODO timezone?
    @property
    def dead(self):
        return (not self.determined_dead_before is None) and self.determined_dead_before <= datetime.date.today()
    
    necropsy = models.BooleanField(
        default= False,
        verbose_name= "necropsied?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "if this animal is dead, has a necropsy been performed on it?",
    )
    
    @property
    def observation_set(self):
        return Observation.objects.filter(case__animal=self)
    
    @property
    def first_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by(
            'observation_datetime',
            'report_datetime',
        )[0]
    
    @property
    def last_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by(
            '-observation_datetime',
            '-report_datetime',
        )[0]

    @property
    def probable_gender(self):
        return probable_gender(self.observation_set)
    def get_probable_gender_display(self):
        if self.probable_gender is None:
            return None
        return [g[1] for g in GENDERS if g[0] == self.probable_gender][0]
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific observations',
    )

    @property
    def gender(self):
        if self.determined_gender:
            return self.determined_gender
        if self.probable_gender:
            return self.probable_gender
        return None

    @property
    def probable_taxon(self):
        return probable_taxon(self.observation_set)
    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'as determined from the taxa indicated in specific observations',
    )
    
    @property
    def taxon(self):
        if self.determined_taxon:
            return self.determined_taxon
        if self.probable_taxon:
            return self.probable_taxon
        return None
    
    def clean(self):
        if self.necropsy and not self.determined_dead_before:
            self.determined_dead_before = datetime.date.today()

    def __unicode__(self):
        if self.name:
            return "%06d %s" % (self.id, self.name)
        return "%06d" % self.id
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 

class CaseManager(models.Manager):
    def cases_in_year(self, year):
        # case.date isn't acutally in the database; it the observation.report_datetime
        # of the observation with the earilest report_datetime. A simple approach here
        # is to get all the cases that have _any_ observation in the year, then prune
        # the one's whose date's aren't actually in the year
        # TODO initially fetch cases with an observation whose report _or_ 
        # observation dates are in the year we're looking for.
        # TODO use YearCaseNumber ?
        cases = self.filter(observation__observation_datetime__year__exact=year).distinct()
        return filter(lambda c: c.date.year == year, cases)
    
    def same_timeframe(self, case):
        '''\
        Returns cases that _may_ have been happening at the same time as the one
        given. Takes into account the potential vagueness of observation dates.
        '''
        
        # Observation.observation__datetime only stores the _start_ of the
        # observation, so use a 2-day fudge-factor for assumed observation
        # length
        assumed_max_obs_length = datetime.timedelta(days=2)

        # cut down our query by year. the +-1 bits are to catch cases that fall
        # within our fudge-factor (see below)
        min_year = case.earliest_datetime.year - 1
        max_year = case.latest_datetime.year + 1
        same_year = self.filter(observation__observation_datetime__year__gte=min_year).filter(observation__observation_datetime__year__lte=max_year)
        result = set()
        for c in same_year:
            # find overlapping observations. 
            if not ( c.latest_datetime + assumed_max_obs_length < case.earliest_datetime 
                   or c.earliest_datetime > case.latest_datetime + assumed_max_obs_length ):
                result.add(c)
        
        # be careful here since an Entanglement isn't considered equal to it's
        # corresponding Case
        result = set(filter(lambda c: c.id != case.id, result))

        return result
    
    def associated_cases(self, case):
        '''\
        Given a case, return a list of _other_ cases that may be relevant to it.
        This includes cases in the same timeframe that are either for the same
        animal or have nearby coordinates.
        '''
        
        result = set()
        
        same_timeframe = self.same_timeframe(case)
        same_timeframe_ids = map(lambda c: c.id, same_timeframe)
        same_animal = self.filter(animal=case.animal, id__in=same_timeframe_ids)
        
        result |= set(same_animal)
        
        # TODO nearby coords
        
        return result

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
    
    def __unicode__(self):
        return "%04d #%03d <%s>" % (
            self.year,
            self.number,
            unicode(self.case),
        )
    
    class Meta:
        ordering = ('year', 'number')

# TODO there's probably a way to get a list of all the subclasses,
# but for now we'll just collected them ourselves.
class CaseMeta(models.Model.__metaclass__):
    
    case_class = None
    
    # TODO should probably do a check if the passed classdef has this as a 
    # metaclass, to handle all the various inheritance edge cases this doesn't.
    # For now though, our inheritance DAG is just a 2-level tree with Case as
    # the root...
    def __new__(self, name, bases, dict):
        the_class = super(CaseMeta, self).__new__(self, name, bases, dict)
        if self.case_class is None and name == 'Case':
            self.case_class = the_class
            self.case_class._subclasses = set()
            self.case_class.detailed_classes = frozenset(self.case_class._subclasses)
        elif self.case_class in bases:
            self.case_class._subclasses.add(the_class)
            self.case_class.detailed_classes = frozenset(self.case_class._subclasses)
        return the_class

class Case(models.Model):
    '''\
    A Case is has all the data for _one_ incident of _one_ animal (i.e. a single strike of a ship, a single entanglement of an animal in a particular set of gear). Hypothetically the incident has a single datetime and place that it occurs, although that's almost never actually known. Cases keep most of their information in the form of a list of observations. They also serve to connect individual observations to animal entries.
    '''
    
    __metaclass__ = CaseMeta
    
    nmfs_id = models.CharField(
        max_length= 255,
        blank= True,
        null= True,
        verbose_name= "NMFS case number",
    )
    
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
    
    ## serious injury and mortality determination ##
    si_n_m_fieldnames = []

    review_1_date = models.DateField(
        blank= True,
        null= True,
        verbose_name = "1st reviewer date",
    )
    si_n_m_fieldnames.append('review_1_date')

    review_1_inits = models.CharField(
        max_length= 5,
        blank= True,
        null= True,
        verbose_name = "1st reviewer initials",
    )
    si_n_m_fieldnames.append('review_1_inits')

    review_2_date = models.DateField(
        blank= True,
        null= True,
        verbose_name = "2nd reviewer date",
    )
    si_n_m_fieldnames.append('review_2_date')

    review_2_inits = models.CharField(
        max_length= 5,
        blank= True,

        null= True,
        verbose_name = "2nd reviewer initials",
    )
    si_n_m_fieldnames.append('review_2_inits')

    case_confirm_criteria = models.IntegerField(
        blank= True,
        null= True,
        verbose_name = "criteria for case confirmation",
        help_text= "a number in one of the ranges 11-14, 21-24, or 31-34",
    )
    si_n_m_fieldnames.append('case_confirm_criteria')

    animal_fate = models.CharField(
        max_length= 2,
        choices = (
            ('mt', 'mortality'),
            ('si', 'serious injury'),
            ('ns', 'non-serious injury'),
            ('no', 'no injury from human interaction'),
            ('un', 'unknown'),
        ),
        default= 'un',
        blank= True,
    )
    si_n_m_fieldnames.append('animal_fate')
    
    fate_cause = models.CharField(
        max_length= 1,
        choices = (
            ('y', 'yes'),
            ('m', 'can\'t be ruled out'),
            ('n', 'no'),
            ('-', 'not applicable'),
        ),
        default= '-',
        blank= True,
        help_text= "Did the injury this case is concerned with lead to the animal's fate above? If the fate was 'no injury' or 'unknown' this should be 'not applicable'",
    )
    si_n_m_fieldnames.append('fate_cause')
    
    fate_cause_indications = models.IntegerField(
        blank= True,
        null= True,
        verbose_name= "indications of fate cause",
        help_text= "a number in one of the ranges 41-44, 51-54, or 61-66",
    )
    si_n_m_fieldnames.append('fate_cause_indications')

    si_prevented = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name = "serious injury warranted if no intervention?",
    )
    si_n_m_fieldnames.append('si_prevented')

    included_in_sar = models.NullBooleanField(
        blank= True,
        null= True,
        verbose_name = "included in SAR?"
    )
    si_n_m_fieldnames.append('included_in_sar')

    review_1_notes = models.TextField(
        blank= True,
        null= True,
        verbose_name = "1st reviewer notes",
    )
    si_n_m_fieldnames.append('review_1_notes')

    review_2_notes = models.TextField(
        blank= True,
        null= True,
        verbose_name = "2st reviewer notes",
    )
    si_n_m_fieldnames.append('review_2_notes')

    @property
    def si_n_m_info(self):
        def is_default(fieldname):
            value = getattr(self, fieldname)
            # first check if there's a default value
            default = self._meta.get_field(fieldname).default
            if default != models.fields.NOT_PROVIDED:
                if value == default:
                    return True
                return False
            
            # just consider None or the empty string to be the default otherwise
            if value is None:
                return True
            
            if value == '':
                return True
            
            return False
                
        return reduce(lambda so_far, fieldname: so_far or not is_default(fieldname), self.si_n_m_fieldnames, False)

    #yearly_number = models.IntegerField(
    #    blank= True,
    #    null= True,
    #    editable= False,
    #    help_text= "A number that's unique within cases whose case-dates have the same year. Note that this number can't be assigned until the case-date is defined, which doesn't happen until the a Observation is associated with it."
    #)
    @property
    def yearly_number(self):
        if self.current_yearnumber:
            return self.current_yearnumber.number
        else:
            return None
    
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

    @property
    def current_name(self):
        # Cases with no Observations yet don't get names
        if not self.observation_set.count():
            return None
        s = {}
        s['year'] = unicode(self.date.year)
        s['yearly_number'] = self.yearly_number
        if self.yearly_number is None:
            s['yearly_number'] = -1
        # trim off anything beyond a day
        s['date'] = "%04d" % self.date.year
        if self.date.month:
            s['date'] += '-%02d' % self.date.month
            if self.date.day:
                s['date'] += '-%02d' % self.date.day
        taxon = self.probable_taxon
        if not taxon is None:
            s['taxon'] = unicode(taxon)
        else:
            s['taxon'] = u'Unknown taxon'
        s['type'] = self.case_type
        name = u"%(year)s#%(yearly_number)d (%(date)s) %(type)s of %(taxon)s" % s

        # add the current_name to the names set, if necessary
        if not name in self.names_set:
            self.names_set |= frozenset([name])
            self.save()
        
        return name
    
    @property
    def past_names_set(self):
        return self.names_set - set([self.current_name])

    @property
    def first_observation_date(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by('observation_datetime')[0].observation_datetime

    @property
    def first_report_date(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by('report_datetime')[0].report_datetime
    
    @property
    def date(self):
        if not self.observation_set.count():
            return None
        # TODO more specific dates should override less specific ones?
        return self.first_observation_date
    
    @property
    def earliest_datetime(self):
        if not self.observation_set.count():
            return None
        return min([o.earliest_datetime for o in self.observation_set.all()])

    @property
    def latest_datetime(self):
        '''\
        The latest that one of this case's observations _may_ have _started.
        '''
        if not self.observation_set.count():
            return None
        return max([o.latest_datetime for o in self.observation_set.all()])
    
    @property
    def breadth(self):
        if not self.observation_set.count():
            return None
        return self.latest_datetime - self.earliest_datetime
    
    @property
    def associated_cases(self):
        return Case.objects.associated_cases(self)

    # this should always be the YearCaseNumber with case matching self.id and
    # year matching self.date.year . But, it's here so we can order by it in
    # the database.
    current_yearnumber = models.ForeignKey(
        YearCaseNumber,
        editable=False,
        null=True,
        related_name='current',
    )
    
    def clean(self):
        # if we don't have a yearly_number, set one if possible
        if self.date:
            def _next_number_in_year(year):
                this_year = YearCaseNumber.objects.filter(year=year)
                if this_year.count():
                    return this_year.order_by('-number')[0].number + 1
                else:
                    return 1
            def _new_yearcasenumber():
                year = self.date.year
                return YearCaseNumber.objects.create(
                    case=self,
                    year=year,
                    number= _next_number_in_year(year),
                )
        
            # do we have a newly assigned date and no yearly-number?
            if self.current_yearnumber:
                # is our current year different from the one in our current
                # yearly_number assignment
                if self.date.year != self.current_yearnumber.year:
                    try:
                        # do we have a previous assignment for our current year?
                        new_year_case_number = YearCaseNumber.objects.get(case=self, year=self.date.year)
                    except YearCaseNumber.DoesNotExist:
                        # add a new entry for this year-case combo
                        new_year_case_number = _new_yearcasenumber()
                    self.current_yearnumber = new_year_case_number
            else:
                # assign a new number
                self.current_yearnumber = _new_yearcasenumber()

    @property
    def detailed(self):
        '''Get the more specific instance of this Case, if any.'''
        for clas in self._subclasses:
            subcases = clas.objects.filter(case_ptr= self.id)
            if subcases.count():
                return subcases.all()[0]
        return self

    @property
    def detailed_class_name(self):
        return self.detailed.__class__.__name__

    case_type = detailed_class_name
    
    @property
    def probable_taxon(self):
        return probable_taxon(self.observation_set)
    
    @property
    def probable_gender(self):
        return probable_gender(self.observation_set)
    
    def __unicode__(self):
        if self.current_name is None:
            if self.id:
                return u"%s (%i)" % (self.detailed_class_name, self.id)
            else:
                return u"<new case>"
        return self.current_name

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 
    
    objects = CaseManager()

    class Meta:
        ordering = ('current_yearnumber__year', 'current_yearnumber__number', 'id')
    
class Observation(models.Model):
    '''\
    An Obsevation is a source of data for an Animal. It has an observer and
    and date/time and details of how the observations were taken. Note that the
    observer data may be scanty if this isn't a firsthand report. It's an
    abstract model for the common fields between different types of Observations.
    '''

    @property
    def relevant_observation(self):
        return self

    case = models.ForeignKey('Case')
    @property
    def relevant_case(self):
        return self.case

    @property
    def detailed(self):
        if self.case.detailed.observation_model.__name__ == self.__class__.__name__:
            return self
        # TODO this assumes the case's observation model is always a direct
        # subclass of Observation
        return self.case.detailed.observation_model.objects.get(observation_ptr=self.id)
    
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
        verbose_name= 'observation date and time',
    )
    # TODO duration?
    location = models.OneToOneField(
        Location,
        blank= True,
        null= True,
        related_name= "observation",
        help_text= 'the observer\'s location at the time of observation',
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
        help_text= '''\
        Same as observer if this is a firsthand report. If not, this is who
        informed us of the incidents.
        ''',
    )
    report_datetime = models.OneToOneField(
        DateTime,
        help_text = 'when we first heard about the observation',
        related_name = 'report',
        verbose_name = 'report date and time',
    )
        
    @property
    def earliest_datetime(self):
        '''\
        The earliest that the observation _may_ have started.
        '''
        o = self.observation_datetime
        r = self.report_datetime
        # if reportdatetime is before observation datetime (which doesn't make
        # sense, but don't count on it not happening) assume the actual
        # observation datetime is the same as the report datetime
        
        # 'wrong' case
        if r.latest < o.earliest:
            return r.earliest
        
        return o.earliest
    
    @property
    def latest_datetime(self):
        '''\
        The latest that the observation _may_ have started.
        '''
        
        # don't return datetimes in the future
        now = datetime.datetime.now(pytz.utc)
        return min(self.observation_datetime.latest, self.report_datetime.latest, now)
    
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
        help_text= 'The most specific taxon (e.g. a species) that can be applied to this animal.',
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
        help_text= "were any biopsy samples taken?",
        verbose_name= "biopsy samples taken?",
    )
    
    tagged = models.NullBooleanField(
        blank= True,
        null= True,
        help_text= "were any tags put on the animal?",
        verbose_name= "was a tag put on the animal?",
    )
    
    # TODO is this needed? surely a wound description would suffice...
    wounded = models.NullBooleanField(
        blank= True,
        null= True,
        default= True,
        help_text= "were there any wounds? No means none were observered, Yes means they were, Unknown means we don't know whether any were observed or not.",
        verbose_name= "wounds observed?",
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

Case.observation_model = Observation
    
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
    observation.case.clean()
    observation.case.save()
models.signals.post_save.connect(_observation_post_save, sender=Observation)


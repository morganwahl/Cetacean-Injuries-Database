# -*- encoding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon

from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from ..utils import probable_gender

from animal import Animal
from imported import Importable
from observation import Observation

# TODO there's probably a way to get a list of all the subclasses,
# but for now we'll just collected them ourselves.
class CaseMeta(models.Model.__metaclass__):
    
    case_class = None
    
    # TODO should probably do a check if the passed classdef has this as a 
    # metaclass, to handle all the various inheritance edge cases this doesn't.
    # For now though, our inheritance DAG is just a 2-level tree with Case as
    # the root...
    def __new__(self, name, bases, dict):
    
        if self.case_class is None and name == 'Case':
            the_class = super(CaseMeta, self).__new__(self, name, bases, dict)
            self.case_class = the_class
            self.case_class.detailed_classes = {name: the_class}

        elif self.case_class in bases:
            # modify the save method to set the case_type field

            if 'save' in dict.keys():
                def save_wrapper(old_save):
                    def new_save(inst, *args, **kwargs):
                        isnt.case_type = name
                        return old_save(inst, *args, **kwargs)
                    return new_save
                dict['save'] = save_wrapper(dict['save'])
            else:
                def new_save(inst, *args, **kwargs):
                    inst.case_type = name
                    return self.case_class.save(inst, *args, **kwargs)
                dict['save'] = new_save

            the_class = super(CaseMeta, self).__new__(self, name, bases, dict)
            self.case_class.detailed_classes[name] = the_class

        return the_class

class SeriousInjuryAndMortality(models.Model):
    '''\
    Abstract class to collect together all the Serious Injury and Mortality
    fields.
    '''
    
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
            
            # consider None or empty string to be defaults as well
            if value is None:
                return True
            
            if value == '':
                return True
            
            return False
                
        return reduce(lambda so_far, fieldname: so_far or not is_default(fieldname), self.si_n_m_fieldnames, False)

    class Meta:
        abstract = True

class Case(Documentable, SeriousInjuryAndMortality, Importable):
    '''\
    A case has all the data for _one_ incident of _one_ animal (i.e. a single strike of a ship, a single entanglement of an animal in a particular set of gear). Hypothetically the incident has a single datetime and place that it occurs, although that's almost never actually known.
    
    Much of the information on a case is in the set of observations marked as relevant to it. Cases also serve to connect observations with the animals they're of.
    '''
    
    __metaclass__ = CaseMeta
    
    animal = models.ForeignKey(
        Animal,
        help_text= "The animal this case concerns."
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
    
    happened_after = models.DateField(
        blank= True,
        null= True,
        help_text= "Please use '<year>-<month>-<day>'. Injuring incidents themselves are rarely observed, so this is a day whose start is definitely _before_ the incident. For entanglements, this is the 'last seen unentangled' date. For shipstrikes this would usually be the date of the last observation without the relevant scar or wound. In those cases were the date of the incident is known, put it here. (You should also add an observation for that day to indicate the actual incident was observed.) For uncertain dates, put a date at the begining of the range of possible ones, i.e. if you know the animal was seen uninjured in July of 2009, put '2009-07-01'.",
        verbose_name= 'incident was on or after',
    )
    
    human_interaction = models.CharField(
        max_length= 3,
        choices= (
            ('unk', 'not yet determined'),
            ('yes', 'yes'),
            ('no' , 'no'),
            ('cbd', 'can\'t be determined'),
        ),
        default= 'unk',
        verbose_name= "Human Interaction?",
        help_text= "Was the incident due to human interaction?"
    )
    
    ole_investigation = models.NullBooleanField(
        blank= True,
        null= True,
        default= False,
        verbose_name= "OLE Investigation",
        help_text= "Is there a corresponding Office of Law Enforcement investigation?",
    )
    
    # this should always be the YearCaseNumber with case matching self.id and
    # year matching self.date.year . But, it's here so we can order by it in
    # the database.
    current_yearnumber = models.ForeignKey(
        'YearCaseNumber',
        editable=False,
        null=True,
        related_name='current',
    )
    
    @property
    def yearly_number(self):
        "A number that's unique within cases whose case-dates have the same year. Note that this number can't be assigned until the case-date is defined, which doesn't happen until the a Observation is associated with it."
        if self.current_yearnumber:
            return self.current_yearnumber.number
        else:
            return None
    
    names = models.TextField(
        blank= False,
        editable= False,
        verbose_name= "past names",
        help_text= "Comma-separated list of autogenerated names with the format \"<year>#<case # in year> (<date>) <type> of <taxon>\", where <year> and <date> are determined by the earliest datetime_observed of it's observations, <type> is 'Entanglement' for all entanglements, and <taxon> is the most general one that includes all the ones mentioned in observations. Note that a case may have multiple names because many of these elements could change as observations are added or updated, however each Case name should always refer to a specific case. The last name in the list is the current name.",
    )
    
    def _case_type_name(self):
        '''\
        Subclasses can override this method to add something to the case names.
        '''
        return u""
    
    def _current_name(self):
        if not self.id:
            return None
        
        obs = self.observation_set
        # Cases with no observations yet don't get names
        if not obs.exists():
            return None

        date = self.date(obs)

        s = {}
        
        # otherwise use our YearCaseNumber IDs
        if self.current_yearnumber:
            s['year'] = unicode(self.current_yearnumber.year)
            s['yearly_number'] = self.current_yearnumber.number
            if self.yearly_number is None:
                s['yearly_number'] = -1
            
            s['case_id'] = "%(year)s#%(yearly_number)d" % s
        else:
            s['case_id'] = "#%06d" % self.id
        
        s['date'] = date.to_unicode(unknown_char=None, time=False)
        
        case_type = self.case_type
        extension = self.specific_instance()._case_type_name()
        if extension:
            case_type += (' ' + extension)
        s['case_type'] = case_type
        
        taxon = self.animal.taxon()
        if not taxon is None:
            s['taxon'] = taxon.scientific_name()
        else:
            s['taxon'] = u'Unknown taxon'
            
        name = u"%(case_id)s (%(date)s) %(case_type)s of %(taxon)s" % s
        
        if self.animal.field_number:
            name += ' %s' % self.animal.field_number
        
        # ensure the name doesn't contain commas
        name = name.replace(',',';')
        
        return name
    
    # names_list is intentially read-only, so that it can only be modified via
    # update_names
    def _get_names_list(self):
        if self.names is None:
            return []
        return filter(lambda x: x != '', self.names.split(','))
    names_list = property(_get_names_list)

    # name is intentially read-only, so that it can only be modified via
    # update_names
    def _get_name(self):
        if self.names_list:
            return self.names_list[-1]
        return None
    #def _set_name(self, new_name):
    #    if new_name != self.name:
    #        if self.names is None or self.names == '':
    #            self.names = new_name
    #        else:
    #            self.names += ',' + new_name

    name = property(_get_name)
    
    # names_set is intentially read-only, so that it can only be modified via
    # _set_name
    def _get_names_set(self):
        return frozenset(self._get_names_list())
    names_set = property(_get_names_set)
    
    def update_names(self):
        #print "called update_names"
        # don't do anything if the case hasn't been saved yet
        if not self.id:
            return
        
        new_name = self._current_name()
        if not new_name is None and new_name != self.name:
            if self.names is None or self.names == '':
                self.names = new_name
            else:
                self.names += ',' + new_name

        return
    
    ### NOTE! none of these handler account for changes to case.animal,
    # obsevation.cases or observation.animal
    
    # Taxon fields that can affect Case._current_name
    # Taxon.name -> Taxon.scientific_name -> Animal.taxon.scientific_name
    # Taxon.rank -> Taxon.scientific_name -> "
    # Taxon.supertaxon -> Taxon.scientific_name -> "
    # Taxon.supertaxon -> Animal.probable_taxon -> Animal.taxon
    @staticmethod
    def _taxon_post_save_update_name_handler(sender, **kwargs):
        # sender should be Taxon
        
        if kwargs['created']:
            # a newly-created taxon can't have any references to it, so we don't
            # need to update anything
            return
        
        # any other change may have altered the taxon tree, which could change 
        # Animal.probable_taxon, which could change Animal.taxon. Since we don't 
        # know what the saved taxon's old supertaxon value was, we can't
        # determine what cases need to have their names updated. Thus, check all
        # cases for name updates
        
        for c in Case.objects.all():
            c.save()
   
    @staticmethod
    def _taxon_post_delete_update_name_handler(sender, **kwargs):
        # sender should be Taxon
        
        # same problem detecting changes to the taxon tree as in taxon saves.
        # just have to check every case
        
        for c in Case.objects.all():
            c.save()
    
    # Animal fields that can affect Case._current_name
    # Animal.determined_taxon
    # Animal.field_number
    @staticmethod
    def _animal_post_save_update_name_handler(sender, **kwargs):
        # sender should be Animal
        
        if kwargs['created']:
            # a newly-created animal can't have any references to it, so we
            # don't need to update anything
            return
        
        # an animal's determined_taxon may have changed, which could change
        # Animal.taxon, which would change Case.animal.taxon for all cases
        # in Animal.case_set
        a = kwargs['instance']
        #print "Animal post_save"
        for c in a.case_set.all():
            c.save()
        
    # Case fields that can affect Case._current_name
    # Case.nmfs_id
    # Case.current_yearnumber
    # Case.id
    # Case.case_type
    # Case.animal
    # updating a Case's name on save is handled in Case.save()
    
    #@staticmethod
    #def _case_post_save_update_name_handler(sender, **kwargs):
    #    # sender should be Case
    #    
    #    c = kwargs['instance']
    #    c._update_name()

    # TODO We don't need to listen to changes in YearCaseNumber, since that's
    # all handled withing Case.save(), right?
    # YearCaseNumber fields that can affect Case._current_name
    # YearCaseNumber.year -> Case.current_yearnumber.year
    # YearCaseNumber.number -> Case.current_yearnumber.number
    #@staticmethod
    #def _yearcasenumber_post_save_update_name_handler(sender, **kwargs):
    #    # sender should be YearCaseNumber
    #
    #    if kwargs['created']:
    #        # a newly-created animal can't have any references to it, so we
    #        # don't need to update anything
    #        return
    #    
    #    ycn = kwargs['instance']
    #    # ycn.current should only have one case in it, but we'll loop over it
    #    # just in case
    #    print "YearCaseNumber post_save"
    #    for c in ycn.current.all():
    #       c.save()
    
    # Observation fields that can affect Case._current_name
    # Observation.case  # ManyToManyField!
    # Observation.animal -> Animal.observation_set -> Animal.probable_taxon
    # Observation.taxon -> Observation.animal.probable_taxon
    # Observation.datetime_observed -> Case.date
    @staticmethod
    def _observation_post_save_update_name_handler(sender, **kwargs):
        # sender should be Observation
        
        #if kwargs['created']:
            #print "Observation post_save"
        
            cases = set()
            o = kwargs['instance']
            
            # the probable_taxon of the observation's animal may have changed,
            # which could change the name of any case for the animal
            
            cases.update(o.animal.case_set.all())
            
            # the Case.date of any cases this observation is associated with
            # may have changed
            cases.update(o.cases.all())
            
            for c in cases:
                c.save()
            
        #else:
            # since the observation may previously been for any animal,
            # and we don't know which one, any animal's probable_taxon may
            # have changed, and we have to check every case
            #for c in Case.objects.all():
            #    c.save()

    @staticmethod
    def _observation_post_delete_update_name_handler(sender, **kwargs):
        # sender should be Observation
        
        # the probable_taxon of the observation's animal may have changed,
        # which could change the name of any case for the animal
        
        #print "Observation post_delete"

        cases = set()
        o = kwargs['instance']
        
        cases.update(o.animal.case_set.all())
        
        # the Case.date of any cases this observation is associated with
        # may have changed
        cases.update(o.cases.all())

        for c in cases:
            c.save()
    
    @staticmethod
    def _observation_cases_m2m_changed_update_name_handler(sender, **kwargs):  
        # sender should be Observation.cases.through
        action, reverse = kwargs['action'], kwargs['reverse']
        if action in ('post_add', 'post_remove') and not reverse:
            #print "Observation.cases change add/remove"
            # cases were added to or removed from an observation
            case_ids = kwargs['pk_set']
            for c in Case.objects.filter(id__in=case_ids):
                c.save()
        if action == 'post_clear' and not reverse:
            #print "Observation.cases change clear"
            o = kwargs['instance']
            for c in o.animal.case_set.all():
                c.save()

        if action in ('post_add', 'post_remove', 'post_clear') and reverse:
            #print "Observation.cases change reverse"
            # observations were added to or removed from a case or a case's
            # observations were cleared
            case = kwargs['instance']
            case.save()

    def date(self, obs=None):
        '''\
        obs is a queryset of observations. it defaults to this case's
        observations.
        '''
        if obs is None:
            obs = self.observation_set

        if not obs.exists():
            return None
        return obs.order_by('datetime_observed')[0].datetime_observed
    
    def earliest_observation(self):
        if not self.observation_set.exists():
            return None
        return self.observation_set.order_by('datetime_observed')[0]
    
    def latest_observation(self):
        if not self.observation_set.exists():
            return None
        return self.observation_set.order_by('-datetime_observed')[0]

    def earliest_datetime(self):
        if not self.observation_set.exists():
            return None
        return min([o.earliest_datetime for o in self.observation_set.all()])

    def latest_datetime(self):
        '''\
        The latest that one of this case's observations _may_ have _started.
        '''
        if not self.observation_set.exists():
            return None
        return max([o.latest_datetime for o in self.observation_set.all()])
    
    def breadth(self):
        if not self.observation_set.exists():
            return None
        return self.latest_datetime() - self.earliest_datetime()
    
    def save(self, force_insert=False, force_update=False, using=None):
        super(Case, self).save(force_insert, force_update, using)
        
        date = self.date()
        if date:
            def _next_number_in_year(year):
                this_year = YearCaseNumber.objects.filter(year=year)
                if this_year.count():
                    return this_year.order_by('-number')[0].number + 1
                else:
                    return 1
            def _new_yearcasenumber():
                year = date.year
                return YearCaseNumber.objects.create(
                    case=self,
                    year=year,
                    number= _next_number_in_year(year),
                )
        
            # do we have a newly assigned date and no yearly-number?
            if self.current_yearnumber:
                # is our current year different from the one in our current
                # yearly_number assignment
                if date.year != self.current_yearnumber.year:
                    try:
                        # do we have a previous assignment for our current year?
                        # note that there may be multiple yearly number
                        # assignments for the same year and case if another
                        # case has been merged into this one.
                        new_year_case_number = YearCaseNumber.objects.filter(case=self, year=date.year).order_by('number')[0]
                    except YearCaseNumber.DoesNotExist:
                        # add a new entry for this year-case combo
                        new_year_case_number = _new_yearcasenumber()
                    self.current_yearnumber = new_year_case_number
                    super(Case, self).save(using=using)
            else:
                # assign a new number
                self.current_yearnumber = _new_yearcasenumber()
                super(Case, self).save(using=using)
        
        self.update_names()

    save.alters_data = True

    case_type = models.CharField(
        max_length= 512,
        default= 'Case',
        editable= False, # note that this only means it's not editable in the admin interface
        null= False,
        help_text= "A required field to be filled in by subclasses. Avoids using a database lookup just to determine the type of a case"
    )
    
    def __unicode__(self):
        try:
            if self.name:
                return self.name
        except:
            pass

        if self.id:
            return u"%s #%06d" % (self._meta.verbose_name.capitalize(), self.id)
        else:
            return u"<new %s>" % (self._meta.verbose_name,)

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 
    
    def get_edit_url(self):
        return reverse('edit_case', args=[self.id])

    class Meta:
        app_label = 'incidents'
        ordering = ('current_yearnumber__year', 'current_yearnumber__number', 'id')

class YearCaseNumber(models.Model):
    '''\
    A little table to do the bookkeeping when assigning yearly-numbers to cases.
    'year' is a year, 'case' is a case, 'number' is any yearly_number held by
    that case for that year, including it's current one.
    
    Assigning unique numbers to each case in a year is complicated; once a
    case-number in a given year has been assigned to a case, it mustn't ever be
    assigned to a different one, even if that case is changed to a different
    year or merged with another case. Ideally, if a case was assigned, say,
    2003#67 and then it's date was changed to 2004, it would be assigned the
    next unused yearly_number for 2004. If it was then changed back to 2003, it
    would be assigned #67 again. Thus, this table stores all past and current
    year-case-yearly_number combinations.
    '''
    
    year = models.IntegerField(db_index= True)
    case = models.ForeignKey(Case)
    number = models.IntegerField(db_index= True)
    
    def __unicode__(self):
        return "%04d #%03d <%s>" % (
            self.year,
            self.number,
            unicode(self.case),
        )
    
    class Meta:
        app_label = 'incidents'
        ordering = ('year', 'number')

models.signals.post_save.connect(
    sender= Taxon,
    receiver= Case._taxon_post_save_update_name_handler,
    dispatch_uid= 'case__update_name__taxon__post_save',
)
models.signals.post_delete.connect(
    sender= Taxon,
    receiver= Case._taxon_post_delete_update_name_handler,
    dispatch_uid= 'case__update_name__taxon__post_delete',
)
models.signals.post_save.connect(
    sender= Animal,
    receiver= Case._animal_post_save_update_name_handler,
    dispatch_uid= 'case__update_name__animal__post_save',
)
# see comment above Case._yearcasenumber_post_save_update_name_handler
#models.signals.post_save.connect(
#    sender= YearCaseNumber,
#    receiver= Case._yearcasenumber_post_save_update_name_handler,
#    dispatch_uid= 'case__update_name__yearcasenumber__post_save',
#)
models.signals.post_save.connect(
    sender= Observation,
    receiver= Case._observation_post_save_update_name_handler,
    dispatch_uid= 'case__update_name__observation__post_save',
)
models.signals.post_delete.connect(
    sender= Observation,
    receiver= Case._observation_post_delete_update_name_handler,
    dispatch_uid= 'case__update_name__observation__post_delete',
)
models.signals.m2m_changed.connect(
    sender= Observation.cases.through,
    receiver= Case._observation_cases_m2m_changed_update_name_handler,
    dispatch_uid= 'case__update_name__observation__m2m_changed',
)


from django.db import models
from cetacean_incidents.apps.animals.models import Animal, Observation, GENDERS, Taxon
from cetacean_incidents.apps.animals.utils import probable_gender, probable_taxon
from cetacean_incidents.apps.people.models import Person, Organization
from cetacean_incidents.apps.vessels.models import Vessel

from django.contrib.auth.models import User

from datetime import datetime

class Visit(Observation):
    '''\
    A Visit is one interaction with an animal that deals with a Case. It's an
    abstract model for the common fields between different types of Cases.
    '''

    case = models.ForeignKey('Case')
    date_reported = models.DateField(
        blank= True,
        null= True,
    )
    time_reported = models.TimeField(
        blank= True,
        null= True,
    )
    
    imported_from = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "The database this was imported from, or the name of the " +
            "form if from paper."
    )
    imported_by = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "If this was imported from another database, the person " +
            "program that imported it."
    )
    
    # for supporting Level A reports. if examination_observation or
    # able_to_examine is set, this is the initial observation part of a Level A.
    # if initial_observation is set this is the examination part.
    part_of_level_a = models.BooleanField(
        verbose_name= "part of a Level A",
        help_text= "set to True if this is the initial observation or the examination for a Level A",
    )
    examination_observation = models.OneToOneField('self',
        blank= True,
        null= True,
        help_text="if unable to examine, leave this blank."
    )
    filer = models.ForeignKey(Person,
        blank= True,
        null= True,
        help_text= "corresponds to a Level-A 'Examiner', i.e. the person who " +
            "filled out the form, not necessarily the one who performed the " +
            "examination.",
    )
    letterholder = models.ForeignKey(
        Organization,
        blank= True,
        null= True,
    )

    first_observed = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "e.g. 'floating', 'beached'",
    )
    condition = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "e.g. 'mummified/skeletal'",
    )
    
    cow_or_calf_half = models.BooleanField(
        default= False,
        help_text= "for compatibility with Level A forms only. Please use " +
                   "the parent / offspring fields for new cases"
    )
        
    # occurrence details
    boat_strike = models.BooleanField()
    shot = models.BooleanField()
    fishery_interaction = models.BooleanField()
    other_human_interaction = models.CharField(
        max_length= 1023,
        blank= True,
    )
    interaction_determined = models.TextField(
        blank= True,
        help_text= "describe how human interactions were determined",
    )
    gear_collected = models.BooleanField()
    gear_disposition = models.TextField(
        blank= True,
    )
    illness = models.BooleanField()
    injury = models.BooleanField()
    other_findings = models.TextField(
        blank= True,
    )
    findings_determined = models.TextField(
        blank= True,
        help_text="describe how other findings were determined",
    )
    
    # initial live animal disposition
    left_at_site = models.BooleanField()
    immediate_release = models.BooleanField(
        verbose_name= "Immediate Release at Site",
    )
    relocated = models.BooleanField()
    disentangled = models.BooleanField()
    died_at_site = models.BooleanField() # TODO implies died at site
    euthanized_at_site = models.BooleanField()
    transferred = models.BooleanField(
        verbose_name = "Transferred to Rehabilitation",
    )
    died_in_transport = models.BooleanField() # TODO implies died in transport
    euthanized_in_transport = models.BooleanField()
    other_initial_disposition = models.BooleanField()
    
    # condition / determination
    # sick and injured are covered by illness and injury fields
    out_of_habitat = models.BooleanField()
    deemed_healthy = models.BooleanField()
    abandoned = models.BooleanField(
        verbose_name = "Abandoned / Orphaned",
    )
    inaccessible = models.BooleanField()
    haz_loc_animal = models.BooleanField(
        verbose_name= "Location Hazardous to Animal",
    )
    haz_loc_public = models.BooleanField(
        verbose_name= "Location Hazardous to Public",
    )
    unknown = models.BooleanField(
        verbose_name= "Unknown / CBD",
    )
    other_determination = models.BooleanField()
    intital_disposition_comment = models.CharField(
        max_length= 1023,
        blank= True,
    )
    first_impression = models.CharField(
        max_length= 1023,
        blank= True,
    )
    skin_condition = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "i.e. peeling, color, whale lice, etc.",
    )
    wounds = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "obvious bleeding or wounds.",
    )
    wound_age = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "i.e. fresh, healing, uncertain",
    )
    weight_health = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "i.e. robust, emaciated, uncertain",
    )
    behaviour_description = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "general description of behaviour",
    )
    can_breath = models.NullBooleanField()
    breathing = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "pattern, sounds, smells?"
    )
    fluking = models.NullBooleanField()
    head_out = models.NullBooleanField()
    dive_duration = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "in minutes"
    )
    
    @models.permalink
    def get_absolute_url(self):
        return ('visit_detail', [str(self.id)]) 

    class Meta:
        ordering = ['date', 'time']

class Case(models.Model):
    '''\
    A Case is an ongoing situation for an Animal that involves Visits. Case is
    an abstract model for the common fields between Entanglements, Shipstrikes,
    and Strandings.
    '''
    
    visit_model = Visit
    
    field_id = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "A unique identifier for a case assigned by some agency.",
    )
    regional_id = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "The regional ID# assigned in the NMFS's National Marine " +
                   "Mammal Stranding Database", 
    )
    national_id = models.CharField(
        max_length= 255,
        blank= True,
        help_text= "The national ID# assigned in the NMFS's National Marine " +
                   "Mammal Stranding Database",
    )
    status = models.CharField(
        max_length= 1,
        blank= True,
        help_text= 'leave blank for unknown',
    )
    
    ole_investigation = models.BooleanField(
        blank= True,
        verbose_name= "OLE Investigation",
        help_text= "Is there a corresponding Office of Law Enforcement investigation?",
    )
    
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
    
    date_opened = models.DateField(blank=True, null=True, default= datetime.today())
    date_closed = models.DateField(blank=True, null=True)
    def _get_visit_date(self, order):
        visits = self.visit_set.order_by(order)
        if len(visits):
            return visits[0].date
        else:
            return None
    def _get_first_visit_date(self):
        return self._get_visit_date(order='date')
    first_visit_date = property(_get_first_visit_date)
    def _get_last_visit_date(self):
        return self._get_visit_date(order='-date')
    last_visit_date = property(_get_last_visit_date)
    
    def _get_animals(self):
        animals = []
        for visit in self.visit_set.all():
            animals.append(visit.animal)
        return frozenset(animals)
    animals = property(_get_animals)
    def _get_animal(self):
        '''Resolve the list of animals into just one. TODO'''
        if self.animals:
            return self.animals[-1]
        return None
    animal = property(_get_animal)
    animal_names = property(lambda self: frozenset(map(unicode, self.animals)))
    
    def _get_probable_taxon(self):
        return probable_taxon(self.visit_set)
    probable_taxon = property(_get_probable_taxon)
    
    def _get_probable_gender(self):
        return probable_gender(self.visit_set)
    probable_gender = property(_get_probable_gender)
    
    def __unicode__(self):
        if self.animals:
            return "%s of %s" % (self.detailed_class_name, ' or '.join(self.animal_names))
        return "%s %s" % (self.detailed_class_name, self.pk)

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 

class CaseGroup(models.Model):
    '''\
    A CaseGroup simply groups together cases that differ only in their Animals.
    In other words, when multiple animals are stranded at once, a Case 
    represents the stranding of just one of the animals. To tie those cases
    together they are added to a CaseGroup. Note that this corresponds to the
    "Group Events" in the NMFS database.
    '''
    
    def _get_animals(self):
        '''\
        returns a set of the 'animals' properties of all the cases. 
        '''
        animalses = []
        for c in self.cases:
            animalses.append(c.animals)
        return frozenset(animalses)
    
    def _is_cow_calf(self):
        '''\
        Does this CaseGroup involve a cow/calf pair? Returns None for 'maybe',
        True or False otherwise.
        '''
        # a list of tuples of the form (animal, set(ca
        cows_and_calves = []
        for animal_list in self._get_animals():
            pass
    
    group_event_id = models.CharField(
        max_length= 255,
        blank= True,
    )
    cases = models.ManyToManyField(
        Case,
        related_name= "case_group",
    )
    case_num_estimate = models.IntegerField(
        blank= True,
        null= True,
        verbose_name= "estimated number of animals",
        help_text= "note that a case may not exist for every animal",
    )
    
    
class EntanglementVisit(Visit):
    time_with = models.CharField(
        max_length= 1023,
        blank= True,
    )
    # gear types
    lobster_gear = models.NullBooleanField()
    free_pot_warp_gear = models.NullBooleanField(
        verbose_name= "pot warp (free)",
    )
    unknown_gillnet = models.NullBooleanField()
    sink_gillnet = models.NullBooleanField()
    surface_gillnet = models.NullBooleanField()
    tiedown_gillnet = models.NullBooleanField(verbose_name="tie-down gillnet")
    swordfish_gillnet = models.NullBooleanField()
    driftnet = models.NullBooleanField()
    stopseine_net = models.NullBooleanField(verbose_name="stop seine net")
    purseseine_net = models.NullBooleanField(verbose_name="purse seine net")
    trawl_gear = models.NullBooleanField(verbose_name="trawl")
    longline_gear = models.NullBooleanField(verbose_name="longline")
    tuna_gear = models.NullBooleanField()
    weir_gear = models.NullBooleanField(verbose_name="weir")
    monofiliment = models.NullBooleanField()
    mooring_gear = models.NullBooleanField(verbose_name="mooring / anchor")
    other_gear = models.NullBooleanField()
    gear_description = models.TextField(
        blank= True,
    )
    line_type = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "type of line (diameter, color, material, etc.)" 
    )
    visible_mesh = models.NullBooleanField(
        help_text= "Is mesh visible?",
    )
    visible_floats = models.NullBooleanField(
        help_text= "Are floats or other gear trailing?",
    )
    body_part_entangled = models.CharField(
        max_length= 255,
        blank= True,
    )
    wraps = models.CharField(
        max_length= 255,
        blank= True,
    )
    life_threatening = models.NullBooleanField()
    effects_on_movement = models.CharField(
        max_length= 255,
        blank= True,
    )
    
    comments = models.TextField(blank=True)
    
    rescue = models.NullBooleanField()
    ccs_rescue_id = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "CCS rescue ID #",
    )
    biopsy_id = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "biopsy #",
    )
    
    class Meta:
        ordering = ['date', 'time']

class Entanglement(Case):
    visit_model = EntanglementVisit
Case.register_subclass(Entanglement)


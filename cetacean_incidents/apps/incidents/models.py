from django.db import models
from cetacean_incidents.apps.animals.models import Animal, Observation, GENDERS, Taxon
from cetacean_incidents.apps.animals.utils import probable_gender, probable_taxon
from cetacean_incidents.apps.contacts.models import Contact, Organization
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.datetime.models import DateTime

from django.contrib.auth.models import User

from datetime import datetime

class Visit(Observation):
    '''\
    A Visit is one interaction with an animal that deals with a Case. It's an
    abstract model for the common fields between different types of Visits.
    Visits are referred to as 'Events' in the UI.
    '''

    case = models.ForeignKey('Case')
    
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
        return ('visit_detail', [str(self.id)]) 

    class Meta:
        ordering = ['report_datetime', 'observation_datetime', 'id']

class Case(models.Model):
    '''\
    A Case is an ongoing situation for an Animal that involves Visits. Case is
    an abstract model for the common fields between Entanglements, Shipstrikes,
    and Strandings.
    '''
    
    visit_model = Visit
    
    animal = models.ForeignKey(
        Animal,
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
    
    def _get_probable_taxon(self):
        return probable_taxon(self.visit_set)
    probable_taxon = property(_get_probable_taxon)
    
    def _get_probable_gender(self):
        return probable_gender(self.visit_set)
    probable_gender = property(_get_probable_gender)
    
    def __unicode__(self):
            if self.id:
                return u"Case %i" % self.id
            else:
                return u"<new case>"

    @models.permalink
    def get_absolute_url(self):
        return ('case_detail', [str(self.id)]) 

class EntanglementVisit(Visit):
    entanglement_status = models.CharField(
        choices= (
            ('n', 'non life-threatening'),
            ('t', 'life-threatening'),
            ('d', 'disentangled'),
            ('e', 'remains entangled'),
        ),
        max_length= 1,
        blank= True,
    )

class Entanglement(Case):
    pass
Case.register_subclass(Entanglement)


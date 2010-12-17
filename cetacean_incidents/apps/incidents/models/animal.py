# -*- encoding: utf-8 -*-

import datetime

from django.core.exceptions import ValidationError
from django.db import models

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.taxons.utils import probable_taxon

from ..utils import probable_gender

GENDERS = (
    ("f", "female"),
    ("m", "male"),
)

class AnimalManager(models.Manager):
    
    def animals_under_taxon(self, taxon):
        '''\
        Returns a queryset of animals determined to be either in the taxon given
        or in a subtaxon of it.
        '''
        return self.filter(determined_taxon__in=Taxon.objects.descendants_ids(taxon))

class Animal(Documentable):
    name = models.CharField(
        blank= True,
        unique= False, # Names aren't assigned by us, so leave open the
                       # posibility for duplicates
        max_length= 255,
        help_text= u'Name(s) given to this particular animal. E.g. “Kingfisher”, “RW #2427”.'
    )
    
    field_number = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "stranding field number",
        help_text= "the field number assigned to this animal by the stranding network",
    )
    
    determined_dead_before = models.DateField(
        blank= True,
        null= True,
        verbose_name= "dead on or before", # no, not really verbose, but it's easier to 
                                 # change this than to alter the fieldname in 
                                 # the schema
        help_text= '''\
            A date when the animal was certainly dead, as determined from the
            observations of this animal. If you're unsure of an exact date, just
            put something certainly after it; e.g. if you know it was dead
            sometime in July of 2008, just put 2008-07-31 (or 2008-08-01). If
            you're totally unsure, just put the current date. Any animal with a
            date before today is considered currently dead.
        '''
    )
    
    # TODO timezone?
    @property
    def dead(self):
        return (not self.determined_dead_before is None) and self.determined_dead_before <= datetime.date.today()
    
    partial_necropsy = models.BooleanField(
        default= False,
        verbose_name= "partially necropsied?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "if this animal is dead, has a partial necropsy been performed on it?",
    )
    
    necropsy = models.BooleanField(
        default= False,
        verbose_name= "necropsied?", # yeah, not very verbose, but you can't have a question mark in a fieldname
        help_text= "if this animal is dead, has a necropsy been performed on it?",
    )
    
    cause_of_death = models.CharField(
        max_length = 1023,
        blank= True,
        verbose_name= "probable cause of mortality",
        help_text= "if this animal is dead, what (if any) probable cause of mortality has been determined?",
    )
    
    @property
    def observation_set(self):
        # TODO more elegant way to avoid circular imports here
        from observation import Observation
        return Observation.objects.filter(case__animal=self)
    
    def first_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by(
            'datetime_observed',
            'datetime_reported',
        )[0]
    
    def last_observation(self):
        if not self.observation_set.count():
            return None
        return self.observation_set.order_by(
            '-datetime_observed',
            '-datetime_reported',
        )[0]

    def probable_gender(self):
        return probable_gender(self.observation_set)
    def get_probable_gender_display(self):
        gender = self.probable_gender()
        if gender is None:
            return None
        return [g[1] for g in GENDERS if g[0] == gender][0]
    determined_gender = models.CharField(
        max_length= 1,
        blank= True,
        choices= GENDERS,
        help_text= 'as determined from the genders indicated in specific observations',
    )

    def gender(self):
        if self.determined_gender:
            return self.determined_gender
        probable_gender = self.probable_gender()
        if probable_gender:
            return probable_gender
        return None

    def probable_taxon(self):
        return probable_taxon(self.observation_set)
    determined_taxon = models.ForeignKey(
        Taxon,
        blank= True,
        null= True,
        help_text= 'as determined from the taxa indicated in specific observations',
    )
    
    def taxon(self):
        if self.determined_taxon:
            return self.determined_taxon
        probable_taxon = self.probable_taxon()
        if probable_taxon:
            return probable_taxon
        return None
    
    def clean(self):
        if not self.name is None and self.name != '':
            # check that an existing animal doesn't already have this name
            animals = Animal.objects.filter(name=self.name)
            if self.id:
                animals = animals.exclude(id=self.id)
            if animals.count() > 0:
                raise ValidationError("name '%s' is already in use by animal '%s'" % (self.name, unicode(animals[0])))

        if self.necropsy and not self.determined_dead_before:
            self.determined_dead_before = datetime.date.today()

    def __unicode__(self):
        if self.name:
            return self.name
        return "unnamed animal #%06d" % self.id
    
    @models.permalink
    def get_absolute_url(self):
        return ('animal_detail', [str(self.id)]) 
    
    objects = AnimalManager()
    
    class Meta:
        app_label = 'incidents'
        ordering = ('name', 'id')


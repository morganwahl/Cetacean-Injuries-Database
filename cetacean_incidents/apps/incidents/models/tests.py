from django.test import TestCase

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.taxons.models import Taxon

from animal import Animal
from case import Case
from observation import Observation

class CaseTestCase(TestCase):
    def setUp(self):
        self.animal = Animal.objects.create()
    
    def test_instantiation(self):
        c = Case.objects.create(animal=self.animal)
        c = Case(animal=self.animal)
        c.clean()
        c.save()

        self.assertEquals(c.animal, self.animal)

        c.animal = Animal.objects.create()
        c.clean()
        c.save()
        
        self.assertNotEquals(c.animal, self.animal)
    
    def test_names(self):
        c = Case.objects.create(animal=self.animal)
        
        self.assertEquals(c.names, '')
        self.assertEquals(c.name, None)
        self.assertEquals(c.names_list, [])
        self.assertEquals(c.names_set, set())
        
        n = 'new name!'
        c.name = n
        self.assertEquals(c.names, n)
        self.assertEquals(c.name, n)
        self.assertEquals(c.names_list, [n])
        self.assertEquals(c.names_set, set([n]))

        c.names = 'Yadda, yodda, yudda'
        self.assertEquals(c.name, ' yudda')
        self.assertEquals(c.names_list, ['Yadda', ' yodda', ' yudda'])
        self.assertEquals(c.names_set, set(['Yadda', ' yodda', ' yudda']))
        
        c.names = ',' * 5
        self.assertEquals(c.name, None)
        self.assertEquals(c.names_list, [])
        self.assertEquals(c.names_set, set([]))
        
        c.names = 'one,two,two,three,two'
        self.assertEquals(c.name, 'two')
        self.assertEquals(c.names_list, ['one', 'two', 'two', 'three', 'two'])
        self.assertEquals(c.names_set, set(['one', 'two', 'three']))
        
        c.name = '5'
        self.assertEquals(c.name, '5')
        self.assertEquals(c.names_list, ['one', 'two', 'two', 'three', 'two', '5'])
        self.assertEquals(c.names_set, set(['one', 'two', 'three', '5']))
        
        c.names = ''

        self.assertEquals(c._current_name(), None)
        
        c.save()
        self.assertEquals(c.name, c._current_name())
        
        obs = Observation.objects.create(
            animal = c.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        obs.cases.add(c)
        # update c
        c = Case.objects.get(id=c.id)
        
        self.assertEquals(c._current_name(), '2011#%d (2011) Case of Unknown taxon' % c.current_yearnumber.number)
        self.assertEquals(c.name, c._current_name())
        
        obs.datetime_observed = UncertainDateTime(2011, 7)
        obs.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c._current_name(), '2011#%d (2011-07) Case of Unknown taxon' % c.current_yearnumber.number)
        self.assertEquals(c.name, c._current_name())
        
        c.nmfs_id = 'NFMS 234'
        self.assertEquals(c._current_name(), 'NFMS 234 (2011-07) Case of Unknown taxon')
        c.save()
        self.assertEquals(c.name, c._current_name())
        
        c.case_type = 'Balh'
        self.assertEquals(c._current_name(), 'NFMS 234 (2011-07) Case (Balh) of Unknown taxon')
        c.save()
        self.assertEquals(c.name, c._current_name())
        
        t = Taxon.objects.create(
            rank= 0,
            name= 'Gensusis',
        )
        c.animal.determined_taxon = t
        self.assertEquals(c._current_name(), 'NFMS 234 (2011-07) Case (Balh) of %s' % t.scientific_name())
        c.animal.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c.name, c._current_name())
        
        c.animal.field_number = '2008 E45RW'
        self.assertEquals(c._current_name(), 'NFMS 234 (2011-07) Case (Balh) of %s 2008 E45RW' % t.scientific_name())
        c.animal.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c.name, c._current_name())
        

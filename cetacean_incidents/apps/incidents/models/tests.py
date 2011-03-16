from datetime import (
    datetime,
    timedelta,
)

from django.test import TestCase

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

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
    
    def test_yearnumbers(self):
        c = Case(animal=self.animal)
        self.assertEquals(c.current_yearnumber, None)
        c.save()
        self.assertEquals(c.current_yearnumber, None)
    
        obs = Observation.objects.create(
            animal = c.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        obs.cases.add(c)
        # update c
        c = Case.objects.get(id=c.id)
        self.assertNotEquals(c.current_yearnumber, None)

    def test_names(self):
        c = Case.objects.create(animal=self.animal)
        
        self.assertEquals(c.names, '')
        self.assertEquals(c.name, None)
        self.assertEquals(c.names_list, [])
        self.assertEquals(c.names_set, set())
        
        n = 'new name!'
        c.names = n
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
        
        c.names = ''

        self.assertEquals(c._current_name(), None)
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
        
        # removing an obs still leaves behind the old name
        obs.cases.remove(c)
        self.assertEquals(c._current_name(), None)
        self.assertEquals(c.name, '2011#%d (2011) Case of Unknown taxon' % c.current_yearnumber.number)
        
        obs.datetime_observed = UncertainDateTime(2010)
        obs.save()
        obs.cases.add(c)
        # update c
        c = Case.objects.get(id=c.id)
        self.assertEquals(c._current_name(), '2010#%d (2010) Case of Unknown taxon' % c.current_yearnumber.number)
        self.assertEquals(c.name, c._current_name())
        
        obs.datetime_observed = UncertainDateTime(2011, 7)
        obs.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c._current_name(), '2011#%d (2011-07) Case of Unknown taxon' % c.current_yearnumber.number)
        self.assertEquals(c.name, c._current_name())
        
        c.case_type = 'Balh'
        self.assertEquals(c._current_name(), '2011#%d (2011-07) Balh of Unknown taxon' % c.current_yearnumber.number)
        c.save()
        self.assertEquals(c.name, c._current_name())
        
        t = Taxon.objects.create(
            rank= 0,
            name= 'Gensusis',
        )
        c.animal.determined_taxon = t
        self.assertEquals(c._current_name(), '2011#%d (2011-07) Balh of %s' % (c.current_yearnumber.number, t.scientific_name()))
        c.animal.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c.name, c._current_name())
        
        c.animal.field_number = '2008 E45RW'
        self.assertEquals(c._current_name(), '2011#%d (2011-07) Balh of %s 2008 E45RW' % (c.current_yearnumber.number, t.scientific_name()))
        c.animal.save()
        c = Case.objects.get(id=c.id)
        self.assertEquals(c.name, c._current_name())

class ObservationTestCase(TestCase):
    
    def setUp(self):
        self.animal = Animal.objects.create()
        self.case = Case.objects.create(animal=self.animal)
    
    def test_earliest(self):
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2011, 3, 8, 9, 38),
                datetime_observed= UncertainDateTime(2011),
            ).earliest_datetime,
            datetime(2011,1,1,0,0),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2011),
                datetime_observed= UncertainDateTime(2011, 3, 8, 9, 38),
            ).earliest_datetime,
            datetime(2011,3,8,9,38),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(3011),
                datetime_observed= UncertainDateTime(3011, 3, 8, 9, 38),
            ).earliest_datetime,
            datetime(3011,3,8,9,38),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2010),
                datetime_observed= UncertainDateTime(2011, 3, 8, 9, 38),
            ).earliest_datetime,
            datetime(2010,1,1,0,0),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_observed= UncertainDateTime(2010),
                datetime_reported= UncertainDateTime(2011, 3, 8, 9, 38),
            ).earliest_datetime,
            datetime(2010,1,1,0,0),
        )
        
    def test_latest(self):
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2011, 3, 8, 9, 38),
                datetime_observed= UncertainDateTime(2011),
            ).latest_datetime,
            datetime(2011,3,8,9,39),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2011),
                datetime_observed= UncertainDateTime(2011, 3, 8, 9, 38),
            ).latest_datetime,
            datetime(2011,3,8,9,39),
        )
        # the two different calls to now() will be off by a few seconds
        now = datetime.now()
        latest = Observation(
            animal= self.animal,
            # this test will eventually fail...
            datetime_reported= UncertainDateTime(3011),
            datetime_observed= UncertainDateTime(3011, 3, 8, 9, 38),
        ).latest_datetime
        self.assertTrue(latest - now < timedelta(hours=1))
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_reported= UncertainDateTime(2010),
                datetime_observed= UncertainDateTime(2011, 3, 8, 9, 38),
            ).latest_datetime,
            datetime(2011,1,1,0,0),
        )
        self.assertEqual(
            Observation(
                animal= self.animal,
                datetime_observed= UncertainDateTime(2010),
                datetime_reported= UncertainDateTime(2011, 3, 8, 9, 38),
            ).latest_datetime,
            datetime(2011,1,1,0,0),
        )
    
    def test_get_oes(self):
        
        no_ext = Observation.objects.create(
            animal = self.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        no_ext.cases.add(self.case)
        self.assertEqual(no_ext.get_observation_extensions(), tuple())
        
        from cetacean_incidents.apps.entanglements.models import EntanglementObservation
        ent_ext = Observation.objects.create(
            animal = self.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        ent_ext.cases.add(self.case)
        ent_oe = EntanglementObservation.objects.create(observation_ptr=ent_ext)
        self.assertEqual(ent_ext.get_observation_extensions(), (ent_oe,))
        
        from cetacean_incidents.apps.shipstrikes.models import ShipstrikeObservation
        ss_ext = Observation.objects.create(
            animal = self.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        ss_ext.cases.add(self.case)
        ss_oe = ShipstrikeObservation.objects.create(observation_ptr=ss_ext)
        self.assertEqual(ss_ext.get_observation_extensions(), (ss_oe,))

        both_ext = Observation.objects.create(
            animal = self.animal,
            datetime_observed= UncertainDateTime(2011),
            datetime_reported= UncertainDateTime(2011),
        )
        both_ext.cases.add(self.case)
        both_ent_oe = EntanglementObservation.objects.create(observation_ptr=both_ext)
        both_ss_oe = ShipstrikeObservation.objects.create(observation_ptr=both_ext)
        self.assertEqual(set(both_ext.get_observation_extensions()), set((both_ent_oe, both_ss_oe)))
        

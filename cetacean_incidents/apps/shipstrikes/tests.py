from django.test import TestCase

from cetacean_incidents.apps.incidents.models import (
    Animal,
    Observation,
)
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTime

from models import (
    Shipstrike,
    ShipstrikeObservation,
)

class ShipstrikeObservationTestCase(TestCase):
    
    def setUp(self):
        self.o = Observation.objects.create(
            animal= Animal.objects.create(),
            datetime_observed= UncertainDateTime(2010),
            datetime_reported= UncertainDateTime(2010),
        )
        
    def test_basics(self):
        
        self.assertRaises(ShipstrikeObservation.DoesNotExist, getattr, self.o, 'shipstrikes_shipstrikeobservation')
        
        eo = ShipstrikeObservation.objects.create(
            observation_ptr= self.o,
        )
        
        self.assertEqual(self.o.shipstrikes_shipstrikeobservation, eo)
        
    def test_add_shipstrike_extension_handler(self):
        a = Animal.objects.create()
        ss = Shipstrike.objects.create(
            animal= a
        )
        o1 = Observation.objects.create(
            animal= a,
            datetime_observed= UncertainDateTime(2009),
            datetime_reported= UncertainDateTime(2009),
        )
        self.assertRaises(ShipstrikeObservation.DoesNotExist, getattr, o1, 'shipstrikes_shipstrikeobservation')
        o1.cases.add(ss)
        o1.shipstrikes_shipstrikeobservation
        
        o2 = Observation.objects.create(
            animal= a,
            datetime_observed= UncertainDateTime(2008),
            datetime_reported= UncertainDateTime(2008),
        )
        self.assertRaises(ShipstrikeObservation.DoesNotExist, getattr, o2, 'shipstrikes_shipstrikeobservation')
        print "adding obs to case"
        ss.observation_set.add(o2)
        # reload o2
        o2 = Observation.objects.get(pk=o2.pk)
        o2.shipstrikes_shipstrikeobservation


from django.test import TestCase

from cetacean_incidents.apps.uncertain_datetimes.models import DateTime
from cetacean_incidents.apps.incidents.models import Animal

from models import Entanglement, GearType, GearTypeRelation, EntanglementObservation

class GearTypeTestCase(TestCase):
    def setUp(self):
        pass

    def test_implied_supertypes(self):
        line = GearType.objects.create(name='line')
        self.assertEqual(line.implied_supertypes, frozenset())

        long_line = GearType.objects.create(name='long line')
        GearTypeRelation(supertype=line, subtype=long_line).save()
        self.assertEqual(long_line.implied_supertypes, frozenset([line]))

        longer_line = GearType.objects.create(name='longer line')
        GearTypeRelation(supertype=long_line, subtype=longer_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line])
        )
        
        red = GearType.objects.create(name='red')
        GearTypeRelation(supertype=red, subtype=long_line).save()
        self.assertEqual(
            longer_line.implied_supertypes,
            frozenset([line, long_line, red])
        )

    def test_cyclecheck(self):
        line = GearType.objects.create(name='line')
        long_line = GearType.objects.create(name='long line')
        # no cycles to begin with, so this shouldn't raise exceptions
        try:
            GearTypeRelation(supertype=line, subtype=long_line).save()
        except GearTypeRelation.DAGException as (message):
            self.fail(message)
        
        # create a self-cycle
        self.assertRaises(
            GearTypeRelation.DAGException,
            GearTypeRelation(subtype=line, supertype=line).save,
        )
        
        # create a 3-node cycle
        longer_line = GearType.objects.create(name='longer line')
        GearTypeRelation(supertype=long_line, subtype=longer_line).save()
        self.assertRaises(
            GearTypeRelation.DAGException,
            GearTypeRelation(subtype=line, supertype=long_line).save,
        )

class EntanglementTestCase(TestCase):
    def test_geartypes(self):
        e = Entanglement.objects.create(animal=Animal.objects.create())

        line = GearType.objects.create(name='line')

        long_line = GearType.objects.create(name='long line')
        GearTypeRelation(supertype=line, subtype=long_line).save()

        longer_line = GearType.objects.create(name='longer line')
        GearTypeRelation(supertype=long_line, subtype=longer_line).save()
        
        self.assertEqual(
            set(e.gear_types.all()),
            set(),
        )
        self.assertEqual(
            set(e.implied_gear_types),
            set(),
        )
        
        e.gear_types.add(long_line)
        self.assertEqual(
            set(e.gear_types.all()),
            set([long_line]),
        )
        self.assertEqual(
            set(e.implied_gear_types),
            set([line]),
        )
        
        e.gear_types.add(longer_line)
        self.assertEqual(
            set(e.gear_types.all()),
            set([long_line, longer_line]),
        )
        self.assertEqual(
            set(e.implied_gear_types),
            set([line]),
        )

    def test_gear_recovered(self):
        e = Entanglement.objects.create(animal=Animal.objects.create())
        true_obv = EntanglementObservation.objects.create(
            case= e,
            observation_datetime= DateTime.objects.create(year=2000),
            report_datetime= DateTime.objects.create(year=2000),
            gear_retrieved= True,
        )
        false_obv = EntanglementObservation.objects.create(
            case= e,
            observation_datetime= DateTime.objects.create(year=2000),
            report_datetime= DateTime.objects.create(year=2000),
            gear_retrieved= False,
        )
        none_obv = EntanglementObservation.objects.create(
            case= e,
            observation_datetime= DateTime.objects.create(year=2000),
            report_datetime= DateTime.objects.create(year=2000),
            gear_retrieved= None,
        )
        self.assertEqual(
            e.gear_retrieved,
            True,
        )
        true_obv.gear_retrieved = False
        true_obv.save()
        self.assertEqual(
            e.gear_retrieved,
            None,
        )
        none_obv.gear_retrieved = False
        none_obv.save()
        self.assertEqual(
            e.gear_retrieved,
            False,
        )


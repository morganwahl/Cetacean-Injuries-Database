import unittest
from models import GearType

class GearTypeTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_cyclecheck(self):
        line = GearType(name='line')
        line.save()
        long_line = GearType(name='long line')
        long_line.save()
        long_line.supertypes = [line]
        
        # no cycles to begin with, so these shouldn't raise exceptions
        try:
            line._cyclecheck()
            long_line._cyclecheck()
        except GearType.DAGException as (message):
            self.fail(message)
        
        # create a self-cycle
        line.supertypes = [line]
        self.assertRaises(GearType.DAGException, line._cyclecheck)
        line.supertypes = []
        try:
            line._cyclecheck()
        except GearType.DAGException as (message):
            self.fail(message)
        
        # create a multi-node cycle
        longer_line = GearType(name='longer line')
        longer_line.save()
        longer_line.supertypes = [long_line]
        line.supertypes = [longer_line]
        self.assertRaises(GearType.DAGException, line._cyclecheck)
        self.assertRaises(GearType.DAGException, long_line._cyclecheck)
        self.assertRaises(GearType.DAGException, longer_line._cyclecheck)
        line.supertypes = []

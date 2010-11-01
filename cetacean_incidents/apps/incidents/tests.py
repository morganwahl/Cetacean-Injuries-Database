from django.test import TestCase

from cetacean_incidents.apps.uncertain_datetimes.models import DateTime
from models import Animal, Case, Observation

class CaseManagerTestCase(TestCase):
    
    fixtures = ['case-date-test']
    
    def test_same_timeframe(self):
        for (case_id, result_ids) in {
            1: (2,3,4),
            2: (1,3,4,5),
            3: (1,2,4),
            4: (1,2,3),
            5: (2,),
            6: [],
        }.items():
            self.assertEqual(
                Case.objects.same_timeframe(Case.objects.get(id=case_id)),
                set(Case.objects.filter(id__in=result_ids)),
            )
        
    def test_associated_cases(self):
        for (case_id, result_ids) in {
            1: (2,3),
            2: (1,3,5),
            3: (1,2),
            4: [],
            5: (2,),
            6: [],
        }.items():
            self.assertEqual(
                Case.objects.associated_cases(Case.objects.get(id=case_id)),
                set(Case.objects.filter(id__in=result_ids)),
            )
        

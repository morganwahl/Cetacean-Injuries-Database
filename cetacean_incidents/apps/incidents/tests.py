from django.test import TestCase

from forms import DateWidget

from cetacean_incidents.apps.datetime.models import DateTime
from models import Animal, Case, Observation

class FormsTestCase(TestCase):
    def setUp(self):
        pass

    def test_DateWidget(self):
        dw = DateWidget()
        # not sure how variable the exact HTML put out by the Django Media class
        # is. The most robust way to testing would use BeautifulSoup to actually
        # parse the HTML, but that means an extra dependency just for testing.
        
        # for now, assume one script per line of output.
        js_string = unicode(dw.media['js'])
        js_lines = len(js_string.split("\n"))
        self.assertEqual(js_lines, 4)

class CaseManagerTestCase(TestCase):
    
    fixtures = ['case-date-test']
    
    def test_cases_in_year(self):
        for (year, case_ids) in {
            1982: [],
            1992: (6,),
            2008: (5,),
            2009: (2,),
            2010: (1,3,4),
        }.items():
            cases = Case.objects.filter(id__in=case_ids)
            self.assertEqual(set(Case.objects.cases_in_year(year)), set(cases))
    
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


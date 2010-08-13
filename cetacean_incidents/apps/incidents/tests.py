from django.test import TestCase

from forms import DateWidget

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


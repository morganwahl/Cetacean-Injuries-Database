from django.test import TestCase

from forms import ContactForm

class ContactFormTestCase(TestCase):
    def setUp(self):
        pass

    def test_instantiation(self):
        f = ContactForm()
        

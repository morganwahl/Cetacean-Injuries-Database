from django.test import TestCase

from models import VesselInfo

from forms import VesselInfoForm

class VesselInfoTestCase(TestCase):
    def test_instantiation(self):
        vi = VesselInfo()
        vi.save()

class VesselInfoFormTestCase(TestCase):
    def test_instantiation(self):
        f = VesselInfoForm()
    
    def test_contact_choice(self):
        f = VesselInfoForm()
        self.assertEqual(tuple(f['contact_choice'].field.choices), tuple(f.contact_choices))


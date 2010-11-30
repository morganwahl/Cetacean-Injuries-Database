from django.test import TestCase

from models import VesselInfo

from forms import NiceVesselInfoForm, ObserverVesselInfoForm

class VesselInfoTestCase(TestCase):
    def test_instantiation(self):
        vi = VesselInfo()
        vi.save()

class NiceVesselInfoFormTestCase(TestCase):
    def test_instantiation(self):
        f = NiceVesselInfoForm()
    
    def test_contact_choice(self):
        f = NiceVesselInfoForm()
        self.assertEqual(tuple(f['contact_choice'].field.choices), tuple(f.contact_choices))

class ObserverVesselInfoFormTestCase(TestCase):
    def test_instantiation(self):
        f = ObserverVesselInfoForm()

    def test_contact_choice(self):
        f = ObserverVesselInfoForm()
        self.assertEqual(tuple(f['contact_choice'].field.choices), tuple(f.contact_choices))


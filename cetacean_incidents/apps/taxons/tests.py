import unittest

from models import Taxon

class TaxonManagerTestCase(unittest.TestCase):
    def setUp(self):
        # even though there's a fixture for cetacean taxa, it's better to have
        # taxa with known properties for testing.
        
        # The Great Apes
        self.apes = []
        for (name, rank, super_name) in (
            ('Hominidae', 1, '',),
            ('Ponginae', .8, 'Hominidae'),
            ('Pongo', 0, 'Ponginae'),
            ('pygmaeus', -1, 'Pongo'),
            ('abelii', -1, 'Pongo'),
            ('Homininae', .8, 'Hominidae'),
            ('Gorilla', 0, 'Homininae'),
            ('gorilla', -1, 'Gorilla'),
            ('gorilla', -1.2, 'gorilla'),
            ('diehli', -1.2, 'gorilla'),
            ('beringei', -1, 'Gorilla'),
            ('beringei', -1.2, 'beringei'),
            ('graueri', -1.2, 'beringei'),
            ('Pan', 0, 'Homininae'),
            ('troglodytes', -1, 'Pan'),
            ('paniscus', -1, 'Pan'),
            ('Homo', 0, 'Homininae'),
            ('sapiens', -1, 'Homo'),
        ):
            supertaxon = None
            if super_name:
                supertaxon = Taxon.objects.get(name=super_name, rank__gt=rank)
            self.apes.append(Taxon.objects.create(name=name, rank=rank, supertaxon=supertaxon))

        self.homo = Taxon.objects.get(name='Homo', rank=0)
        self.humans = Taxon.objects.get(name='sapiens', rank=-1, supertaxon=self.homo)
        self.orang = Taxon.objects.get(name='Ponginae', rank=.8)

    def tearDown(self):
        for t in self.apes:
            Taxon.delete(t)

    def test_descendants(self):
        self.assertEqual(Taxon.objects.descendants(self.humans), tuple())
        self.assertEqual(Taxon.objects.descendants(self.homo), (self.humans,))
        orangs = tuple(self.orang.subtaxons.all())
        orangs += tuple(orangs[0].subtaxons.all())
        self.assertEqual(Taxon.objects.descendants(self.orang), orangs)
    
    def test_with_descendants(self):
        self.assertEqual(Taxon.objects.with_descendants(self.humans), (self.humans,))
        self.assertEqual(Taxon.objects.with_descendants(self.homo), (self.homo, self.humans))
        orangs = (self.orang,)
        orangs += tuple(self.orang.subtaxons.all())
        orangs += tuple(orangs[1].subtaxons.all())
        self.assertEqual(Taxon.objects.with_descendants(self.orang), orangs)


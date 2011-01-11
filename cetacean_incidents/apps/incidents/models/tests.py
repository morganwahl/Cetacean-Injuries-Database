from django.test import TestCase

from animal import Animal
from case import Case

class CaseTestCase(TestCase):
    def setUp(self):
        self.animal = Animal.objects.create()
    
    def test_instantiation(self):
        c = Case.objects.create(animal=self.animal)
        c = Case(animal=self.animal)
        c.clean()
        c.save()

        self.assertEquals(c.animal, self.animal)

        c.animal = Animal.objects.create()
        c.clean()
        c.save()
        
        self.assertNotEquals(c.animal, self.animal)
    
    def test_names(self):
        c = Case.objects.create(animal=self.animal)
        
        self.assertEquals(c.names, '')
        self.assertEquals(c.name, None)
        self.assertEquals(c.names_list, [])
        self.assertEquals(c.names_set, set())
        
        n = 'new name!'
        c.name = n
        self.assertEquals(c.names, n)
        self.assertEquals(c.name, n)
        self.assertEquals(c.names_list, [n])
        self.assertEquals(c.names_set, set([n]))

        c.names = 'Yadda, yodda, yudda'
        self.assertEquals(c.name, ' yudda')
        self.assertEquals(c.names_list, ['Yadda', ' yodda', ' yudda'])
        self.assertEquals(c.names_set, set(['Yadda', ' yodda', ' yudda']))
        
        c.names = ',' * 5
        self.assertEquals(c.name, None)
        self.assertEquals(c.names_list, [])
        self.assertEquals(c.names_set, set([]))
        
        c.names = 'one,two,two,three,two'
        self.assertEquals(c.name, 'two')
        self.assertEquals(c.names_list, ['one', 'two', 'two', 'three', 'two'])
        self.assertEquals(c.names_set, set(['one', 'two', 'three']))
        

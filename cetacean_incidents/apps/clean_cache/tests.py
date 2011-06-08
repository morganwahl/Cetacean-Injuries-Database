from pprint import pprint

from django.test import TestCase

from django.contrib.auth.models import User

from django.contrib.contenttypes.models import ContentType

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.tags.models import Tag

from cetacean_incidents.apps.vessels.models import VesselInfo

from . import Smidgen, State

class SmidgenTestCase(TestCase):
    
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(Contact)
        self.kp = 'clean_cache__contacts__contact__%(pk)s'
    
    def test_non_existant_object(self):
        print "\nnon existant object"
        cid = 10000
        # TODO make sure there doesn't happend to be a contact with ID 10000
        s = Smidgen({
            (Contact, cid): ['id', 'name'],
        })
        
        self.assertEqual(s.fields, {
            (self.ct, cid): set(['id', 'name']),
        })
        cache_key_patterns = {
            Contact: {
                'fields': {
                    'id': self.kp + '__id',
                    'name': self.kp + '__name',
                },
                'missing': self.kp + '__missing',
            }
        }
        self.assertEqual(s.cache_key_patterns, cache_key_patterns)
        self.assertEqual(s.current_state()._state, {
            (self.ct, cid): None,
        })
    
    def test_non_existant_field(self):
        print "\nnon existant fields"
        cid = Contact.objects.create().id
        s = Smidgen({
            (Contact, cid): ['id', 'unfield'],
        })
        
        self.assertEqual(s.fields, {
            (self.ct, cid): set(['id', 'unfield']),
        })
        cache_key_patterns = {
            Contact: {
                'fields': {
                    'id': self.kp + '__id',
                    'unfield': self.kp + '__unfield',
                },
                'missing': self.kp + '__missing',
            }
        }
        self.assertEqual(s.cache_key_patterns, cache_key_patterns)
        self.assertEqual(s.current_state()._state, {
            (self.ct, cid): {
                'id': cid,
                'unfield': State.NonExistantFieldValue('unfield'),
            },
        })
    
    def test_reverse_fk_field(self):
        print "\nreverse FK field"
        c = Contact.objects.create()
        s = Smidgen({
            (Contact, c.id): ['id', 'tag_set', 'for_vessels'],
        })
        
        self.assertEqual(s.fields, {
            (self.ct, c.id): set(['id', 'tag_set', 'for_vessels']),
        })
        cache_key_patterns = {
            Contact: {
                'fields': {
                    'id': self.kp + '__id',
                    'tag_set': self.kp + '__tag_set',
                    'for_vessels': self.kp + '__for_vessels',
                },
                'missing': self.kp + '__missing',
            }
        }
        self.assertEqual(s.cache_key_patterns, cache_key_patterns)
        self.assertEqual(s.current_state()._state, {
            (self.ct, c.id): {
                'id': c.id,
                'tag_set': set([]),
                'for_vessels': set([]),
            },
        })
        
        test_user = User.objects.create()
        print "\tcreating tags"
        t1 = Tag.objects.create(entry=c, user=test_user)
        t2 = Tag.objects.create(entry=Contact.objects.create(), user=test_user)
        
        print "\taccessing state"
        self.assertEqual(s.current_state()._state, {
            (self.ct, c.id): {
                'id': c.id,
                'tag_set': set([t1]),
                'for_vessels': set([]),
            },
        })
        
        print "\tdeleting tags"
        t2.delete()
        
        print "\taccessing state"
        self.assertEqual(s.current_state()._state, {
            (self.ct, c.id): {
                'id': c.id,
                'tag_set': set([t1]),
                'for_vessels': set([]),
            },
        })
        
        print "\tchanging tags"
        t1.entry = Contact.objects.create()
        t1.save()
        
        print "\taccessing state"
        self.assertEqual(s.current_state()._state, {
            (self.ct, c.id): {
                'id': c.id,
                'tag_set': set([]),
                'for_vessels': set([]),
            },
        })


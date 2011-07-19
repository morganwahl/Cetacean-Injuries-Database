import base64
from copy import copy
from itertools import chain
import uuid

from django.core.cache import cache as django_cache
from django.db.models import signals as model_signals

from django.contrib.contenttypes.models import ContentType

from . import (
    CacheDependency,
    TestList,
)

class ClearingHandler(object):
    
    def __init__(self, clearer, model, signal_name, kwargs_tests=None):
        # keys are primary key values, values are lists of cache keys to delete
        # when a signal for that instance comes in
        self.clearer = clearer
        self.model = model
        self.signal_name = signal_name
        self.kwargs_tests = kwargs_tests
        
        # {
        #   'any': {
        #     <TestList>: set([<cache_key>, <cache_key>, ...]),
        #     ...
        #   },
        #   'pks': {
        #     <pk>: {
        #       <TestList>: set([<cache_key>, <cache_key>, ...]),
        #       ...
        #     },
        #   }
        # }
        self.cache_keys = {
            'any': {},
            'pks': {}
        }
        
        signal = getattr(model_signals, signal_name)
        signal.connect(
            receiver= self,
            sender= model,
            weak= True,
            dispatch_uid= 'clean_cache__cache_clearer__%s__%s__%s' % (
                model._meta.app_label,
                model._meta.object_name.lower(),
                signal_name,
            )
        )
        
    def add_cache_key(self, cache_key, instance_tests=TestList((True,)), pk=None):
        if pk is None:
            if not instance_tests in self.cache_keys['any']:
                self.cache_keys[instance_tests] = set()
            self.cache_keys[instance_tests].add(cache_key)
        else:
            if not pk in self.cache_keys['pks']:
                self.cache_keys['pks'][pk] = {}
            if not instance_tests in self.cache_keys['pks'][pk]:
                self.cache_keys['pks'][pk][instance_tests] = set()
            self.cache_keys['pks'][pk][instance_tests].add(cache_key)
    
    def remove_cache_key(self, cache_key):
        for keys in self.cache_keys['any'].values():
            keys.discard(cache_key)
        for keys in chain(*[d.values() for d in self.cache_keys['pks'].values()]):
            keys.discard(cache_key)
    
    def __call__(self, sender, **kwargs):
        if not self.kwargs_tests.test(kwargs):
            return
        
        to_remove = set()
        inst = kwargs['instance']
        
        for testlist, keys in self.cache_keys['any'].items():
            if testlist.test(inst):
                to_remove |= keys
        
        if inst.pk in self.cache_keys['pks']:
            for testlist, keys in self.cache_keys['pks'][inst.pk].items():
                if testlist.test(inst):
                    to_remove |= keys
        
        for cache_key in to_remove:
            django_cache.delete(cache_key)
            self.clearer.remove(cache_key)
    
    def __repr__(self):
        return u"<ClearingHandler: %r->%r>" % (self.model, self.signal_name)
    
    def __unicode__(self):
        return u"ClearingHandler for %s->%s" % (self.model, self.signal_name)

class CacheClearer(object):
    
    def __init__(self):
        self.handlers = {}
    
    def add(self, cache_key, deps):

        # TODO m2m changes?
        
        for change_type in ('create', 'update', 'delete'):
            for key, tests in getattr(deps, change_type).items():
                if isinstance(key, ContentType):
                    ct = key
                    pk = None
                else:
                    ct, pk = key

                model = ct.model_class()
                
                selector = (model, change_type)
                if not selector in self.handlers:
                    signal_name, kwargs_tests = {
                        'create': ('post_save', TestList([
                            lambda kwargs: 'created' in kwargs and kwargs['created'],
                        ])),
                        'update': ('post_save', TestList([
                            lambda kwargs: 'created' in kwargs and not kwargs['created'],
                        ])),
                        'delete': ('pre_delete', TestList([True])),
                    }[change_type]
                    
                    self.handlers[selector] = ClearingHandler(self, model, signal_name, kwargs_tests)
                self.handlers[selector].add_cache_key(cache_key, instance_tests=tests, pk=pk)

    def remove(self, key):
        for h in self.handlers.values():
            h.remove_cache_key(key)

class Cache(object):
    
    def __init__(self):
        self.uuid = uuid.uuid1()
        self.prefix = base64.b64encode(self.uuid.bytes)
        self.clearer = CacheClearer()
    
    def set(self, key, value, timeout, deps):
        '''\
        'deps' is a CacheDependency instance that describes the fields that the
        cached value depends on.
        '''
        self.clearer.add(key, deps)
        # since we keep info about the entires in memory, mark the value with
        # our UUID, and add the deps info with the entry
        stored_value = (self.uuid, value)
        django_cache.set(key, stored_value, timeout)

    def get(self, key, default=None):
        stored_value = django_cache.get(key, default)
        if stored_value == default:
            return default
        
        # unpack out metadata about the value
        uuid, value = stored_value
        if uuid != self.uuid:
            # this value was stored by a different Cache instance, and thus we
            # need to ignore it.
            return default
        
        return value

cache = Cache()


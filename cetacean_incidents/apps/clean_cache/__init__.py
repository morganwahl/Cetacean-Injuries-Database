from operator import __not__, __or__

from django.core.cache import cache

from django.db import models
from django.db.models import Model, Manager
from django.db.models import signals as model_signals

from django.contrib.contenttypes.models import ContentType

CACHE_TIMEOUT = 7 * 24 * 60 * 60 # one week

class TestList(object):
    
    def __init__(self, tests):
        '''\
        'tests' is an iterable of either callables or expressions. If any of
        the expressions is True, this TestList will always be True. If any of
        the expressions are False, they are ignored. If the list has callables
        and no True expressions, the callables will be evaluated in order and
        this TestList will be True if any of them are. If any empty list is
        passed, this TestList will always be False.
        '''
        
        self.tests = (False,)
        
        for t in tests:
            if not callable(t) and bool(t):
                self.tests = (True,)
                return
            if callable(t):
                if self.tests == (False,):
                    self.tests = []
                self.tests.append(t)
        
        # if we built a list of callables, go ahead and make it a tuple
        if isinstance(self.tests, list):
            self.tests = tuple(self.tests)
        
    def test(self, arg):
        if self.tests == (False,):
            return False
        if self.tests == (True,):
            return True
        for t in self.tests:
            if t(arg):
                return True
        return False
    
    def __copy__(self):
        # TestLists are immutable, so just return self
        return self
    
    def __deepcopy__(self, memo):
        # TestLists are immutable, so just return self
        return self
    
    def __repr__(self):
        if self.tests == (False,) or self.tests == (True,):
            return "TestList(%r)" % (self.tests,)
        return "<TestList: %d callables>" % len(self.tests)
    
    def __eq__(self, other):
        return self.tests == other.tests
    
    def __ne__(self, other):
        return self.tests != other.tests
    
    def __hash__(self):
        return hash(self.tests)
    
    def __add__(self, other):
        return TestList(self.tests + other.tests)
    
    def __unicode__(self):
        if self.tests == (False,):
            return "false TestList"
        if self.tests == (True,):
            return "true TestList"
        return "%d-way TestList" % len(self.tests)

class CacheDependency(object):
    '''\
    Class for descriptions of arbitrary bits of the database that might change,
    invalidating a cache entry.
    
    'create' is a dictionary:
    
    {
        <ContentType of model>: <TestList>,
        ...
    }
    
    If the Model instance of the class indicated by the key is updated and _any_
    of the given tests pass, the cache key is invalid. A test can be a callable
    that returns a boolean given the instance created, or a boolean expression.
    
    If the dictionary passed in uses the actual model classes as keys, they
    will be converted to the above.

    'update' is a dictionary:

    {
        (<ContentType of the model>, <primary key of Model instance>): <TestList>,
        ...
    }

    If the dictionary passed in uses the actual model instances as keys, they
    will be converted to the above.
    
    'delete' is a dictionary:
    
    {
        (<ContentType of the model>, <primary key of Model instance>): <TestList>,
        ...
    }
    
    If the dictionary passed in uses the actual model instances as keys, they
    will be converted to the above.
    
    This class is mainly useful for combining the cache-dependencies.
    '''
    
    # TODO could add model_update and model_delete args
    
    @staticmethod
    def _simplify_testlist(tests):
        for t in tests:
            if not callable(t) and bool(t):
                return (True,)
        return tuple(filter(callable, tests))
            
    def __init__(self, create={}, update={}, delete={}):
        # {
        #   <ContentType of model>: <TestList>,
        #   (<ContentType>, <pk>): <TestList>,
        #   ...
        # }
        self.create = {}
        self.update = {}
        self.delete = {}
        
        for model, tests in create.items():
            if not isinstance(model, ContentType):
                if issubclass(model, Model):
                    model = ContentType.objects.get_for_model(model)
                else:
                    raise ValueError(u'create keys must be a Model subclass or ContentType instance.')
            
            if model in self.create:
                tests = self.create[model] + tests
            self.create[model] = tests
        
        for obj, tests in update.items():
            if obj is None:
                continue

            # validate and convert the key
            if isinstance(obj, Model):
                obj = (ContentType.objects.get_for_model(obj), obj.pk)
            
            if not len(obj) == 2:
                raise ValueError(u'update keys must be either Model instances or pairs.')
            
            if not isinstance(obj, tuple):
                obj = tuple(obj)
            
            if not isinstance(obj[0], ContentType):
                if issubclass(obj[0], Model):
                    obj = (ContentType.objects.get_for_model(obj[0]), obj[1])
                else:
                    raise ValueError(u'update keys that are pairs must have a Model subclass or ContentType instance as their first item.')
            
            if obj in self.update:
                tests = self.update[obj] + tests
            self.update[obj] = tests
        
        for obj, tests in delete.items():
            if obj is None:
                continue

            # validate and convert the key
            if isinstance(obj, Model):
                obj = (ContentType.objects.get_for_model(obj), obj.pk)
            
            if not len(obj) == 2:
                raise ValueError(u'delete keys must be either Model instances or pairs.')
            
            if not isinstance(obj, tuple):
                obj = tuple(obj)
            
            if not isinstance(obj[0], ContentType):
                if issubclass(obj[0], Model):
                    obj = (ContentType.objects.get_for_model(obj[0]), obj[1])
                else:
                    raise ValueError(u'delete keys that are pairs must have a Model subclass or ContentType instance as their first item.')
            
            if obj in self.delete:
                tests = self.delete[obj] + tests
            self.delete[obj] = tests

    def __or__(self, other):
        if not isinstance(other, CacheDependency):
            return NotImplemented
        
        kwargs = {
            'create': {},
            'update': {},
            'delete': {},
        }
        
        for cd in (self, other):
            for attr in ('create', 'update', 'delete'):
                for key, tests in getattr(cd, attr).items():
                    if key in kwargs[attr]:
                        tests = kwargs[attr][key] + tests
                    kwargs[attr][key] = tests

        return CacheDependency(**kwargs)
    
    def __copy__(self):
        # CacheDependencies are immutable, so just return self
        return self
    
    def __deepcopy__(self, memo):
        # CacheDependencies are immutable, so just return self
        return self
    
    def __repr__(self):
        return "CacheDependency(%r, %r, %r)" % (self.create, self.update, self.delete)


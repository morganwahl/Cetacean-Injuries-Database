from django.core.cache import cache

from django.db import models
from django.db.models import Model, Manager
from django.db.models import signals as model_signals

from django.contrib.contenttypes.models import ContentType

CACHE_TIMEOUT = 7 * 24 * 60 * 60 # one week

def register_cache_clear(
        signal_name,
        model,
        key_pattern,
        kwargs_filter=None,
        name_suffix=None,
        kwargs_map=None,
    ):
    if kwargs_filter is not None and name_suffix is None:
        raise ValueError("Need a name_suffix if a kwargs_filter was passed in.")
    if kwargs_filter is None:
        kwargs_filter = lambda kwargs: True
    if name_suffix is None:
        name_suffix = signal_name
    
    if kwargs_map is None:
        kwargs_map = lambda kwargs: {'pk': kwargs['instance'].pk}
    
    name = '__'.join((
        model._meta.app_label,
        model._meta.object_name.lower(),
        name_suffix,
        key_pattern % {'pk': 'pk'},
    ))
    
    def signal_handler(sender, **kwargs):
        # sender should be model
        if not kwargs_filter(kwargs):
            return
        cache_key = key_pattern % kwargs_map(kwargs)
        cache.delete(cache_key)
    # set a nice name for introspection's sake
    signal_handler.__name__ = '%s_handler' % name
    
    signal = getattr(model_signals, signal_name)
    
    signal.connect(
        receiver= signal_handler,
        sender= model,
        # very important to keep the signal handler from being garbage collected
        weak= False,
        # This is very important since it keeps duplicate handlers being created
        # every time register_cache_clear is called with the same args
        dispatch_uid= 'clean_cache__cache_clear__%s' % name
    )

def register_cache_clear_post_update(model, key_pattern):
    
    return register_cache_clear(
        'post_save',
        model,
        key_pattern,
        lambda kwargs: not kwargs['created'],
        'post_update',
    )
    
def register_cache_clear_post_create(model, key_pattern):
    
    return register_cache_clear(
        'post_save',
        model,
        key_pattern,
        lambda kwargs: kwargs['created'],
        'post_create',
    )

def register_cache_clear_post_delete(model, key_pattern):
    
    return register_cache_clear(
        'post_delete',
        model,
        key_pattern,
    )

def register_fk_cache_clears(model, fn, key_pattern):
    # add signal handlers to detect object
    # creation/deletion on the other end of a relation
    
    # TODO better way of doing this
    for ro in model._meta.get_all_related_objects():
        if ro.get_accessor_name() == fn:
            break
    
    reverse_fn = ro.field.name
    
    def _kwargs_filter(kwargs):
        inst = kwargs['instance']
        reverse_value = getattr(inst, reverse_fn)
        return not reverse_value is None
    def _kwargs_map(kwargs):
        inst = kwargs['instance']
        reverse_value = getattr(inst, reverse_fn)
        return {'pk': reverse_value.pk}
    
    def _pre_save_filter(kwargs):
        # don't bother with new objects
        return not kwargs['instance'].pk is None
    
    def _pre_save_map(kwargs):
        inst = kwargs['instance']
        # we actually need a new instance of the same entry to get the value
        # currently in the database
        old_inst = inst.__class__.objects.get(pk=inst.pk)
        reverse_value = getattr(old_inst, reverse_fn)
        return {'pk': reverse_value.pk}
    
    # both pre_save and post_save to catch both instances on the other side of
    # relation
    register_cache_clear(
        signal_name= 'pre_save',
        model= ro.model,
        key_pattern= key_pattern,
        kwargs_filter= _pre_save_filter,
        name_suffix= 'pre_save_check_refs',
        kwargs_map= _pre_save_map,
    )
    
    register_cache_clear(
        signal_name= 'post_save',
        model= ro.model,
        key_pattern= key_pattern,
        kwargs_filter= _kwargs_filter,
        name_suffix= 'post_save_check_refs',
        kwargs_map= _kwargs_map,
    )
    
    register_cache_clear(
        signal_name= 'post_delete',
        model= ro.model,
        key_pattern= key_pattern,
        kwargs_filter= _kwargs_filter,
        name_suffix= 'post_delete_check_refs',
        kwargs_map= _kwargs_map,
    )

class Smidgen(object):
    '''\
    Class for descriptions of arbitrary bits of state of various Model
    instances. Can produce State objects that represent the state of the bits
    at the time they're created.
    '''
    
    def __init__(self, description={}):
        # fields is keyed to pairs consisting of a ContentType and a primary key
        self.fields = {}
        # these are used by any State instance created by this Smidgen
        self.cache_key_patterns = {}
        for obj, fieldnames in description.items():
            # validate and convert the key
            if isinstance(obj, Model):
                obj = (ContentType.objects.get_for_model(obj), obj.pk)
            
            if not len(obj) == 2:
                raise ValueError("description keys must be either Model instances or pairs.")
            
            if not isinstance(obj, tuple):
                obj = tuple(obj)
            
            if not isinstance(obj[0], ContentType):
                if issubclass(obj[0], Model):
                    obj = (ContentType.objects.get_for_model(obj[0]), obj[1])
                else:
                    raise ValueError(u'''description keys that are pairs must have a Model subclass or ContentType instance as their first item.''')
            
            self.fields[obj] = set()
            
            # create cache key patterns to be used by State objects created by
            # this Smidgen. Also, register signal handlers to clear the cache of
            # those patterns
            model = obj[0].model_class()
            key_pattern = 'clean_cache__%s__%s__%%(pk)s' % (
                model._meta.app_label,
                model._meta.object_name.lower(),
            )
            # we may encound the same model more than once
            if not model in self.cache_key_patterns:
                missing_key_pattern = key_pattern + '__missing'
                self.cache_key_patterns[model] = {
                    'missing': missing_key_pattern,
                    'fields': {},
                }
                register_cache_clear_post_create(model, missing_key_pattern)

            # copy over fieldnames one at a time just to ensure what was passed in is indeed an iterable
            for fieldname in fieldnames:
                self.fields[obj].add(fieldname)

                # create cache key patterns to be used by State objects created
                # by this Smidgen. Also, register signal handlers to clear the
                # cache of those patterns
                if not fieldname in self.cache_key_patterns[model]['fields']:
                    value_key_pattern = key_pattern + '__' + fieldname
                    self.cache_key_patterns[model]['fields'][fieldname] = value_key_pattern
                    register_cache_clear_post_update(model, value_key_pattern)
                    register_cache_clear_post_delete(model, value_key_pattern)
        
    def __or__(self, other):
        if not isinstance(other, Smidgen):
            return NotImplemented
        
        new_desc = {}
        
        objs = set(self.fields.keys()) | set(other.fields.keys())
        for obj in objs:
            new_desc[obj] = set()
            if obj in self.fields:
                new_desc[obj] |= self.fields[obj]
            if obj in other.fields:
                new_desc[obj] |= other.fields[obj]
        
        return Smidgen(new_desc)
    
    def __repr__(self):
        return "Smidgen(%s)" % repr(self.fields)
    
    def current_state(self):
        return State(self)

class State(object):
    '''\
    An arbitrary bit of state of the database. The particular bit it is is can
    be described by a Smidgen.
    '''
    
    class NonExistantFieldValue(object):
        # essentially just a wrapper around a string
        
        def __init__(self, fieldname):
            self.fieldname = fieldname
        
        def __eq__(self, other):
            if not isinstance(other, State.NonExistantFieldValue):
                return False
            
            return self.fieldname == other.fieldname
        
        def __ne__(self, other):
            return not self.__eq__(other)
        
        def __hash__(self):
            return hash(self.fieldname)
        
        def __repr__(self):
            return u"NonExistantFieldValue(%s)" % repr(self.fieldname)

    def __init__(self, smidgen=None):
        # essentially just a wrapper around a dictionary keyed to Model
        # instances (really, ContentTypes and primary key pairs) whose values
        # are dictionaries keyed to fieldnames whose values are the values of
        # those fields.
        
        # Instances that don't actually exist are represented by a None value.
        
        # Fields that don't actually exist are represented by a
        # NonExistantFieldValue.
        
        if smidgen is None:
            smidgen = Smidgen()
        
        self._state = {}
        for obj, fns in smidgen.fields.items():
            ct, pk = obj
            model = ct.model_class()
            
            missing_key_pattern = smidgen.cache_key_patterns[model]['missing']
            missing_key = missing_key_pattern % {'pk': pk}
            missing = cache.get(missing_key)
            
            inst = None
            if not missing:
                try:
                    inst = model.objects.get(pk=pk)
                except model.DoesNotExist:
                    cache.set(missing_key, True, CACHE_TIMEOUT)
            
            if inst is None:
                self._state[obj] = None
                continue
            
            fields = {}
            for fn in fns:
                if not hasattr(inst, fn):
                    fields[fn] = State.NonExistantFieldValue(fn)
                    continue
                
                value_key_pattern = smidgen.cache_key_patterns[model]['fields'][fn]
                value_key = value_key_pattern % {'pk': pk}
                value = cache.get(value_key, State.NonExistantFieldValue(fn))
                
                if value == State.NonExistantFieldValue(fn):
                    value = getattr(inst, fn)
                    if isinstance(value, Manager):
                        # HACK
                        register_fk_cache_clears(model, fn, value_key_pattern)
                        
                        # use a set so State.__eq__ stays correct
                        value = set(value.all())
                    cache.set(value_key, value, CACHE_TIMEOUT)

                fields[fn] = value

            self._state[obj] = fields
    
    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        
        return self._state == other._state
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return "<State: %s>" % repr(self._state)


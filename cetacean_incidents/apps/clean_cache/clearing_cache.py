from pprint import pprint

from django.core.cache import cache

def set(key, value, timeout, deps):
    '''\
    'deps' is a Smidgen instance that describes the fields that the cached value
    depends on.
    '''
    
    new_value = (deps, deps.current_state(), value)
    pprint(('cache set', key))
    cache.set(key, new_value, timeout)

def get(key, default=None):
    value = cache.get(key, default)
    if value == default:
        #pprint(('cache miss', key))
        return default

    deps, orig_state, orig_value = value
    if deps.current_state() != orig_state:
        pprint(('cache stale', key, orig_value, deps, orig_state))
        cache.delete(key)
        return default
    
    #pprint(('cache hit', key))
    return orig_value


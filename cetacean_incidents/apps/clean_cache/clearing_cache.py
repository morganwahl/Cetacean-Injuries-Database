from django.core.cache import cache

def set(key, value, timeout, deps):
    '''\
    'deps' is a Smidgen instance that describes the fields that the cached value
    depends on.
    '''
    
    new_value = (deps, deps.current_state(), value)
    cache.set(key, new_value, timeout)

def get(key, default=None):
    value = cache.get(key, default)
    if value == default:
        return default

    deps, orig_state, orig_value = value
    if deps.current_state() != orig_state:
        cache.delete(key)
        return default
    
    return orig_value


from django import template

register = template.Library()

@register.simple_tag
def uncertain_datetime_sort_key(uncertaindatetime):
    '''\
    Include a key that can be sorted lexicographically (or numerically). a part
    of the date is None, it will sort _after_ datetimes that are otherwise 
    identical (i.e. unknown dates are considered to be less recent.)
    '''
    
    return uncertaindatetime.sortkey(unknown_is_later=True)


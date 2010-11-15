from django import template

register = template.Library()

@register.inclusion_tag('datetime_sortkey.html')
def datetime_sort_key(datetime):
    '''\
    Include a key that can be sorted lexicographically (or numerically). If
    datetime is None, the key will sort _after_ all other keys. (i.e. unknown
    date are considered to be less recent.) Datetime can be our own DateTime
    model instances, or a Python datetime object.
    '''
    
    d = {}
    if datetime is None:
        for k in ('year', 'month', 'day', 'hour', 'minute', 'second'):
            d[k] = None
    else:
        # this works with both our DateTimes and the Python built-in datetime class
        # since only ours can have None values for this attributes
        d['year'] = datetime.year if not datetime.year is None else 0
        d['month'] = datetime.month if not datetime.month is None else 0
        d['day'] = datetime.day if not datetime.day is None else 0
        # note that hours, minutes and seconds have to be offset by 1 since
        # '0' is a defined value for them.
        d['hour'] = datetime.hour + 1 if not datetime.hour is None else 0
        d['minute'] = datetime.minute + 1 if not datetime.minute is None else 0
        d['second'] = datetime.second + 1 if not datetime.second is None else 0
    
    return { 'd': d }

import re
from calendar import month_name, isleap
import datetime

def month_days(year=None):
    feb_days = 29 if year is None or isleap(year) else 28
    #             jan feb       mar apr may jun jul aug sep oct nov dec
    return (None, 31, feb_days, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

class UncertainDateTime(object):
    """Class similiar to a python datetime, except the individual fields can be
    None (to indicate 'unknown')"""
    
    # sortkey() assumes a four-character year
    # don't allow years that aren't useable in python datetimes
    MINYEAR = max(-999, datetime.MINYEAR)
    MAXYEAR = min(9999, datetime.MAXYEAR)

    MINMONTH = 1
    MAXMONTH = len(month_name) - 1 # month_name[0] is blank
    
    MINDAY = 1
    @classmethod
    def maxday(cls, year=None, month=None):
        if not month is None:
            return month_days(year)[month]
        return 31
    
    MINHOUR = 0
    MAXHOUR = 24 - 1
    
    MINMINUTE = 0
    MAXMINUTE = 60 - 1
    
    MINSECOND = 0
    MAXSECOND = 60 - 1 # not bothering with leap-seconds
    
    MINMICROSECOND = 0
    MAXMICROSECOND = 10 ** 6 - 1
    
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None):
        
        # note that years hypothetically extend to infinity in both directions,
        # thus we give an OverflowError for ones that are too large or small.
        # The other things have a finite set of values by definition, thus we
        # raise a ValueError.
        
        if not year is None:
            if not isinstance(year, int):
                raise TypeError("year must be an integer or None, not a %s" % type(year))
            if not (year >= self.MINYEAR and year <= self.MAXYEAR):
                raise OverflowError("integer year must be between %d and %d (inclusive)"  % (self.MINYEAR, self.MAXYEAR))
        self.year = year

        if not month is None:
            if not isinstance(month, int):
                raise TypeError("month must be an integer or None, not a %s" % type(month))
            if not (month >= self.MINMONTH and month <= self.MAXMONTH):
                raise ValueError("integer month must be between %d and %d (inclusive)"  % (self.MINMONTH, self.MAXMONTH))
        self.month = month

        if not day is None:
            if not isinstance(day, int):
                raise TypeError("day must be an integer or None, not a %s" % type(day))
            if not (day >= self.MINDAY and day <= self.maxday(year, month)):
                raise ValueError("integer day must be between %d and %d (inclusive) when year is %s and month is %s"  % (self.MINDAY, self.maxday(year, month), year, month))
        self.day = day

        if not hour is None:
            if not isinstance(hour, int):
                raise TypeError("hour must be an integer or None, not a %s" % type(hour))
            if not (hour >= self.MINHOUR and hour <= self.MAXHOUR):
                raise ValueError("integer hour must be between %d and %d (inclusive)"  % (self.MINHOUR, self.MAXHOUR))
        self.hour = hour

        if not minute is None:
            if not isinstance(minute, int):
                raise TypeError("minute must be an integer or None, not a %s" % type(minute))
            if not (minute >= self.MINMINUTE and minute <= self.MAXMINUTE):
                raise ValueError("integer minute must be between %d and %d (inclusive)"  % (self.MINMINUTE, self.MAXMINUTE))
        self.minute = minute

        if not second is None:
            if not isinstance(second, int):
                raise TypeError("second must be an integer or None, not a %s" % type(second))
            if not (second >= self.MINSECOND and second <= self.MAXSECOND):
                raise ValueError("integer second must be between %d and %d (inclusive)"  % (self.MINSECOND, self.MAXSECOND))
        self.second = second

        if not microsecond is None:
            if not isinstance(microsecond, int):
                raise TypeError("microsecond must be an integer or None, not a %s" % type(year))
            if not (microsecond >= self.MINMICROSECOND and microsecond <= self.MAXMICROSECOND):
                raise ValueError("integer microsecond must be between %d and %d (inclusive)"  % (self.MINMICROSECOND, self.MAXMICROSECOND))
        self.microsecond = microsecond
    
    SORTKEY_MAX_LEN = len('YYYYMMDDHHMMSSuSSSSS')
    SORTS_BEFORE_DIGITS = ' '
    SORTS_AFTER_DIGITS = 'z'

    def sortkey(self, unknown_is_later=False):
        '''\
        If unknown_is_later is True, the sortkeys returned will sort unknown
        elements of the date _after_ dates where they're known (that are other 
        wise identical). For example: 2004-03-?? 08:??:?? will sort _after_
        2004-03-20 08:??:?? but _before_ 2004-03-20 09:??:?? .
        '''
        
        parts = []
        for fieldname, width in (
            (       'year', 4),
            (      'month', 2),
            (        'day', 2),
            (       'hour', 2),
            (     'minute', 2),
            (     'second', 2),
            ('microsecond', 6),
        ):
            val = getattr(self, fieldname)
            if val is None:
                if unknown_is_later:
                    parts.append(self.SORTS_AFTER_DIGITS * width) 
                else:
                    parts.append(self.SORTS_BEFORE_DIGITS * width) 
            else:
                parts.append(('%0' + str(width) + 'd') % val)
        
        return ''.join(parts)
    
    @classmethod
    def from_sortkey(cls, key):
        '''\
        Constructs a new UncertainDateTime from a return value of another 
        UncertainDateTime's sortkey() method.
        '''

        if not isinstance(key, basestring):
            raise TypeError(
                "key passed to sortkey must be a string or unicode, not %s" 
                % type(key)
            )
        
        match = re.search(r'(.{4})(.{2})(.{2})(.{2})(.{2})(.{2})(.{6})', key)
        if not match:
            raise ValueError("key passed wasn't formatted correctly: '%s'" % key)
        args = match.groups()

        blank_re = re.compile(r'^[' + cls.SORTS_BEFORE_DIGITS + cls.SORTS_AFTER_DIGITS + ']+$')
        def string_converter(val):
            if blank_re.search(val):
                return None
            return int(val)
        args = map(string_converter, args)
        
        return cls(*args)
    
    @property
    def earliest(self):
        '''\
        Returns a python datetime that's the earliest possible point in this
        UncertainDateTime.
        '''
        
        # note that we use the minimums for a python datetime, not an 
        # UncertainDateTime
        
        (year, month, day, hour, minute, second, microsecond) = (self.year, self.month, self.day,  self.hour, self.minute, self.second, self.microsecond)
        if year is None:
            year = datetime.MINYEAR
        if month is None:
            month = 1
        if day is None:
            day = 1
        if hour is None:
            hour = 0
        if minute is None:
            minute = 0
        if second is None:
            second = 0
        if microsecond is None:
            microsecond = 0
        
        return datetime.datetime(year, month, day, hour, minute, second, microsecond)
    
    @property
    def latest(self):
        '''\
        Returns a python datetime that's the latest possible point in this
        UncertainDateTime.
        '''
        
        # note that we use the maximums for a python datetime, not an 
        # UncertainDateTime

        (year, month, day, hour, minute, second, microsecond) = (self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond)
        if year is None:
            year = datetime.MAXYEAR
        if month is None:
            month = len(month_name) - 1
        if day is None:
            day = month_days(year)[month]
        if hour is None:
            hour = 24 - 1
        if minute is None:
            minute = 60 - 1
        if second is None:
            second = 60 - 1 # not bothering with leap-seconds
        if microsecond is None:
            microsecond = 1000000 - 1
        
        result = datetime.datetime(year, month, day, hour, minute, second, microsecond)
        
        # we actually want the point at the _end_ of the range, so add one
        # microsecond to the result of the above maxing-out of each field.
        if result < datetime.datetime.max:
            result += datetime.timedelta(microseconds=1)
        
        return result

    @property
    def breadth(self):
        '''\
        The length of time that this UncertainDateTime might refer to.
        '''
        
        return self.latest - self.earliest

    def __unicode__(self, seconds=True, microseconds=True):
        d = {}
        d['year'] = u'%04d' % self.year if not self.year is None else u'?' * 4
        d['month'] = u'%02d' % self.month if not self.month is None else u'?' * 2
        d['day'] = u'%02d' % self.day if not self.day is None else u'?' * 2
        d['hour'] = u'%02d' % self.hour if not self.hour is None else u'?' * 2
        d['minute'] = u'%02d' % self.minute if not self.minute is None else u'?' * 2
        if seconds:
            d['minute'] += ((u':%02d' % self.second) if not self.second is None else u':??')
        if seconds and microseconds:
            d['minute'] += ((u'.%06d' % self.microsecond) if not self.microsecond is None else u'.??????')
        return "%(year)s-%(month)s-%(day)s %(hour)s:%(minute)s" % d
        
    def humanize(self):
        # ymd
        # 100 in <year>
        # 010 in           <month>
        # 110 in <year>    <month>
        # 001           on      ?? <day>th
        # 101 in <year> on      ?? <day>th
        # 011           on <month> <day>th
        # 111 in <year> on <month> <day>th
        
        # 1000 around <hour>
        # 0100 at        <minute> past
        # 1100 at <hour>:<minute>
        # 0010 at ??    :??            :<second>
        # 1010 at <hour>:??            :<second>
        # 0110 at ??    :<minute>      :<second>
        # 1110 at <hour>:<minute>      :<second>
        # 0001 at ??    :??            :??      .<microsecond>
        
        result = []
        if not self.year is None:
            result.append('in %04d' % self.year)
        if not self.day is None:
            result.append('on')
        if not self.month is None:
            result.append('%02d' % self.month)


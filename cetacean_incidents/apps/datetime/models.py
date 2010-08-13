'''Model to handle the various uncertainties in dates and times.'''

from django.db import models
from calendar import month_name, isleap
import datetime
import pytz

class DateTime(models.Model):
    year = models.IntegerField(
        help_text="Year is the one required field, because without it there's no point in recording the rest."
    )
    months = [(i, month_name[i])for i in range(1,len(month_name))]
    month = models.IntegerField(
        choices= months,
        blank= True,
        null= True,
    )
    day = models.IntegerField(
        blank= True,
        null= True,
    )
    
    hour = models.IntegerField(
        choices = [(i, i) for i in range(0,24)],
        blank= True,
        null= True,
        help_text= "midnight is 0, 1pm is 13, etc. Note that all datetimes are TAI (i.e. timezoneless). It's up to the editing and display interface to convert accordingly.",
    )
    minute = models.IntegerField(
        blank= True,
        null= True,
    )
    second = models.FloatField(
        blank= True,
        null= True,
    )
    
    import_notes = models.TextField(
        blank= True,
        editable= False, # note that this only means it's not editable in the admin interface or ModelForm-generated forms
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
    @property
    def earliest(self):
        '''\
        Returns a python datetime that's the earliest point in this potentially 
        vauge DateTime.
        '''
        
        (year, month, day, hour, minute, second) = (self.year, self.month, self.day,  self.hour, self.minute, self.second)
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
        
        return datetime.datetime(year, month, day, hour, minute, second, 0, pytz.utc)
    
    @property
    def latest(self):
        '''\
        Returns a python datetime that's the latest point in this potentially 
        vauge DateTime.
        '''
        
        #                   jan feb   mar apr may jun jul aug sep oct nov dec
        MONTH_DAYS = (None, 31, None, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        
        (year, month, day, hour, minute, second) = (self.year, self.month, self.day, self.hour, self.minute, self.second)
        if month is None:
            month = 12
        if day is None:
            if month == 2:
                if isleap(year):
                    day = 29
                else:
                    day = 28
            else:
                day = MONTH_DAYS[month]
        if hour is None:
            hour = 23
        if minute is None:
            minute = 59
        if second is None:
            second = 59 # not bothering with leap-seconds
        
        result = datetime.datetime(year, month, day, hour, minute, second, 0, pytz.utc)
        
        # we actually want the point at the _end_ of the range, so add one
        # microsecond to the result of the above maxing-out of each field
        result += datetime.timedelta(seconds=1)
        
        return result

    @property
    def breadth(self):
        '''\
        The length of time that this DateTime might refer to.
        '''
        
        return self.latest - self.earliest
    
    # note that giving only a year and a hour is OK, so you can indicate
    # time-of-day without knowing what day it was exactly
    def __unicode__(self):
        ret = u"%04d" % self.year
        if not self.month is None:
            ret += u"-%02d" % self.month
            if not self.day is None:
                ret += u"-%02d" % self.day
        if not self.hour is None:
            ret += u" %02dh" % self.hour
            if not self.minute is None:
                ret += u" %02dm" % self.minute
                if not self.second is None:
                    ret += u" %02ds" % self.second
        return ret
    
    class Meta:
        ordering = ('year', 'month', 'day', 'hour', 'minute', 'second')
        

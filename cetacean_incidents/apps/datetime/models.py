'''Model to handle the various uncertainties in dates and times.'''

from django.db import models
from calendar import month_name

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
                        if self.second:
                            ret += u" %02ds" % self.second
        return ret
    
    class Meta:
        ordering = ('year', 'month', 'day', 'hour', 'minute', 'second')
        

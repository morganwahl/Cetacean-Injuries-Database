'''Model to handle the various uncertainties in dates and times.'''

from django.db import models
from calendar import month_name

class DateTime(models.Model):
    year = models.IntegerField(
        help_text="Year is the one required field, because without it there's no point in recording the rest."
    )
    months = [(i, month_name[i])for i in range(1,len(month_name))]
    month = models.IntegerField(
        choices= months
        blank= True,
        null= True,
    )
    day = models.IntegerField(
        blank= True,
        null= True,
    )
    
    hour = models.IntegerField(
        choices = [(i, i) for i in range(0,24)]
        blank= True,
        null= True,
        help_text= "midnight is 0, 1pm is 13, etc."
    )
    minute = models.IntegerField(
        blank= True,
        null= True,
    )
    second = models.FloatField(
        blank= True,
        null= True,
    )
    
    class Meta:
        ording = ('year', 'month', 'day', 'hour', 'minute', 'second')
        

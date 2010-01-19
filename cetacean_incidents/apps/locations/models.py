from django.db import models

class Location(models.Model):
    '''\
    A model for incident locations.
    '''
    
    description = models.TextField(
        blank= True,
        help_text= "Describe location as best as possible."
    )

    coordinates = models.CharField(
        max_length = 127,
        blank= True,
        help_text= "Comma separated latitude, longitude. In decimal degrees with south and west as negative. 180 degrees E or W is -180.",
    )
    # TODO form validation will be essential for this field!
    roughness = models.FloatField(
        blank= True,
        help_text= "Indicate the uncertainty of the coordinates, in meters. Should be the radius of the circle around the coordinates that contains the actual location with 95% certainty. For GPS-determined coordinates, this will be a few tens of meters. For rough estimates, note that 1 mile = 1,609.344 meters.",
    )
    
    def __unicode__(self):
        if self.coordinates:
            return unicode(self.coordinates)
        
        return u"<#%s>" % unicode(self.pk)

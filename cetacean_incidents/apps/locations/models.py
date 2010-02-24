from django.db import models

class Location(models.Model):
    '''\
    A model for incident locations.
    '''
    
    description = models.TextField(
        blank= True,
        help_text= '''\
        a prose description of the location. if no coordinates were known at
        the time, this is all the location info we have; coordinates (and a
        large 'roughness') may be assigned later, for some simple mapping. Even
        if we have coordinates, the method by which they were obtained ought to
        be noted.
        '''
    )

    coordinates = models.CharField(
        max_length = 127,
        blank= True,
        help_text= '''\
        Comma separated latitude, longitude. In decimal degrees with south and
        west as negative. 180 degrees E or W is -180. conversion from/to other
        formats is handled elsewhere.
        '''
    )
    def _get_coords_pair(self):
        if self.coordinates is None:
            return None
        return map(float, self.coordinates.split(','))
    coords_pair = property(_get_coords_pair)
    
    # TODO form validation will be essential for this field!
    roughness = models.FloatField(
        blank= True,
        null= True,
        help_text= '''\
        Indicate the uncertainty of the coordinates, in meters. Should be the
        radius of the circle around the coordinates that contains the actual
        location with 95% certainty. For GPS-determined coordinates, this will
        be a few tens of meters. For rough estimates, note that 1 mile =
        1,609.344 meters (user interfaces should handle unit conversion). When
        plotting locations on a map, a cirle of this size (centered at the
        coordinates) should be used instead of a single point, so as to not give
        a false sense of accuracy.
        '''
    )

    import_notes = models.TextField(
        blank= True,
        #editable= False, # note that this only means it's not editable in the admin interface
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
    def __unicode__(self):
        if self.coordinates:
            return unicode(self.coordinates)
        
        return u"<#%s>" % unicode(self.pk)

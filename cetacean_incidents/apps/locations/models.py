from django.db import models
from utils import dec_to_dms, dms_to_dec

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
    
    # this one was tough to decide on. Using GeoDjango is overkill; my main
    # concern was not losing precision to rounding when converting from
    # degrees-minutes-seconds to decimal degrees. ideally, we would store
    # coordinates in base-30 (so that converting from DMS or decimal wouldn't
    # produce a repeating-decimal that had to be rounded off), but then when
    # somebody looks at the database itself, or a dump of this model, they
    # have to have that explained to them. My not-so-great comprimise is to use
    # a string which allows for a really high precision, base-10 decimal repre-
    # sentation. This still leaves it up to views (and/or forms) to present 
    # this data nicely, but it's at least understandable in a database dump.
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
        return tuple(map(float, self.coordinates.split(',')))
    def _set_coords_pair(self, pair):
        if not len(pair) >= 2:
            # TODO throw an exception?
            return
        self.coordinates = "%.16f,%.16f" % tuple(pair)
    coords_pair = property(_get_coords_pair, _set_coords_pair)
    def _get_dms_coords_pair(self):
        if self.coordinates is None:
            return None
        return tuple(map( dec_to_dms, self.coords_pair))
    def _set_dms_coords_pair(self, pair):
        if not len(pair) >= 2:
            # TODO throw an exception?
            return
        self.coords_pair = map(dms_to_dec, pair)
    dms_coords_pair = property(_get_dms_coords_pair, _set_dms_coords_pair)
    
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
        editable= False, # note that this only means it's not editable in the admin interface or ModelForm-generated forms
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
    def __unicode__(self):
        if self.coordinates:
            return unicode(self.coordinates)
        
        return u"<#%s>" % unicode(self.pk)

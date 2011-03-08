# -*- encoding: utf-8 -*-

import re

from django.db import models

from django.contrib.localflavor.us.models import USStateField

from cetacean_incidents.apps.countries.models import Country

from utils import (
    dec_to_dms,
    dms_to_dec,
)

class Location(models.Model):
    '''\
    A model for uncertain locations. Every observation has it's own entry in the
    Locations table.
    '''
    
    description = models.TextField(
        blank= True,
        help_text= "A prose description of the location. If no coordinates were known at the time, this is all the location info we have. Even if we have coordinates, the method by which they were obtained ought to be noted."
        
        # coordinates (and a large 'roughness') may be assigned later, for some 
        # simple mapping. 
    )
    
    country = models.ForeignKey(
        Country,
        blank= True,
        null= True,
        help_text= u"leave blank if unknown or in international waters.",
    )

    # integers for sorting
    waters = models.IntegerField(
        default= 0,
        choices= (
            (0, 'unknown'),
            (1, 'land'),
            (2, 'state waters'),   # only defined in US waters
            (3, 'federal waters'), # UNCLOS 'territorial waters' + archipelagic waters + continguous zone, + EEZ - state waters
            #(4, 'archipelagic waters'), # UNCLOS definition we don't currently care about
            #(5, 'continguous zone'),  # UNCLOS definition we don't currently care about. Note that Canada and the U.S. do have them.
            #(6, 'exclusive economic zone'), # UNCLOS definition we don't currently care about. Note that Canada and the U.S. do have them.
            #(7, 'continental shelf'), # UNCLOS definition we don't currently care about.
            (8, 'international waters'),
        ),
        help_text= u"""‘land’ is anyplace above mean-low-tide. ‘state waters’ are defined by the Submerged Lands Act (and numerous relevant court cases). Mostly, they extend 3 nm out from shore. The big exceptions are in FL, TX, and PR, and small exceptions are all over the place. ‘federal waters’ includes all the non-state waters within the 'territorial waters' and 'exclusive economic zone' of the U.S., which extends out 200 nm from shore. For the 'territorial waters' and EEZ of other countries, use 'federal waters'.""",
    )
    
    state = USStateField(
        blank= True,
        null= True,
        help_text= "If on land or in state waters, the state the observation was in. If in federal waters or the U.S. EEZ, give the nearest state. Leave blank if unknown or outside the U.S.",
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
        help_text= "Comma separated latitude, longitude. In decimal degrees with south and west as negative. 180 degrees E or W is -180. conversion from/to other formats is handled elsewhere."
    )
    def _get_coords_pair(self):
        if not self.coordinates:
            return None
        return tuple(map(float, self.coordinates.split(',')))
    def _set_coords_pair(self, pair):
        if not pair:
            self.coordinates = ''
            return
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
        if not pair:
            self.coords_pair = None
            return
        if not len(pair) >= 2:
            # TODO throw an exception?
            return
        self.coords_pair = map(dms_to_dec, pair)
    dms_coords_pair = property(_get_dms_coords_pair, _set_dms_coords_pair)
    
    def clean(self):
        # clean_coordinates
        if not self.coordinates:
            self.coordinates = ''
        else:
            (lat, lng) = re.search("(-?[\d\.]+)\s*,\s*(-?[\d\.]+)", self.coordinates).group(1, 2)

            # TODO Decimal not Float!
            
            lat = float(lat)
            lat = max(lat, -90)
            lat = min(lat, 90)
            
            lng = float(lng)
            # add 180 so that 179 E is now 359 E and 180 W is zero
            lng += 180
            # take it mod 360
            lng %= 360
            # and subtract the 180 back off
            lng -= 180
            
            self.coordinates = "%.16f,%.16f" % (lat,lng)
    
    # TODO validation will be essential for this field!
    roughness = models.FloatField(
        blank= True,
        null= True,
        help_text= "Indicate the uncertainty of the coordinates, in meters. Should be the radius of the circle around the coordinates that contains the actual location with 95% certainty. For GPS-determined coordinates, this will be a few tens of meters. For rough estimates, note that 1 mile = 1,609.344 meters (user interfaces should handle unit conversion). When plotting locations on a map, a cirle of this size (centered at the coordinates) should be used instead of a single point, so as to not give a false sense of accuracy."
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
        

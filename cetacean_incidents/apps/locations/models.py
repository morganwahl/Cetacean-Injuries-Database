from django.db import models

class LoranTd(models.Model):
    chain = models.IntegerField(
        blank= True,
        null= True,
        help_text= "the LORAN C GRI #, e.g. 9960 for the northeast U.S."
    )
    secondary_id = models.CharField(
        max_length= 1,
        blank= True,
        help_text= 'a letter or number to indicate which secondary this is ' +
            "for, i.e. W, X, Y, or Z",
    )
    time_delay = models.FloatField()
    
    def __unicode__(self):
        ret = u''
        if self.chain:
            ret += ("%d " % self.chain)
        if self.seconday_id:
            ret += ("%s " % self.secondary_id)
        ret += ("%s" % self.time_delay)
        return ret

class Location(models.Model):
    '''\
    A model for incident locations.
    '''
    
    description = models.TextField(
        blank= True,
    )

    latitude = models.FloatField(
        blank= True,
        null= True,
        help_text= "in decimal degrees with south as negative.",
    )
    longitude = models.FloatField(
        blank= True,
        null= True,
        help_text= "in decimal degrees with west as negative. " +
            "180 degrees E or W is -180",
    )
    altitude = models.FloatField(
        blank= True,
        null= True,
        help_text= "altitude (or depth, if negative) in meters from sea-level."
    )
    orig_coordinates = models.CharField(
        max_length= 127,
        blank= True,
        help_text= "the coordinates as originally given, to prevent loss of "
            "accuracy",
    )
    coordinates_method = models.CharField(
        blank= True,
        max_length= 1023,
        help_text= "how were these coordinates determined?",
    )
    
    loran_tds = models.ManyToManyField(
        'LoranTd',
        blank= True,
        null= True,
        help_text= "the Td readings for at least two secondaries",
    )
    
    country = models.CharField(
        blank= True,
        max_length= 255,
    )
    state = models.CharField(
        blank= True,
        max_length= 255,
        verbose_name= "state / province"
    )
    county = models.CharField(
        blank= True,
        max_length= 255,
        verbose_name= "county",
        help_text= "in general, use the Census's County Equivalents where " +
            " there are no counties, e.g. parishes in Louisiana"
    )
    city = models.CharField(
        blank= True,
        max_length= 255,
        verbose_name= "nearest city/town",
    )
    
    water_body = models.CharField(
        blank= True,
        max_length= 255,
        verbose_name= "body of water",
    )

    def __unicode__(self):
        if self.latitude and self.longitude:
            if self.latitude < 0:
                lat = unicode(- self.latitude)
                lat += " S"
            elif self.latitude >= 0:
                lat = unicode(self.latitude)
                if self.latitude > 0:
                    lat += " N"
            if self.longitude < 0:
                lng = unicode(- self.longitude)
                lng += " S"
            elif self.longitude >= 0:
                lng = unicode(self.longitude)
                if self.longitude > 0:
                    lng += " N"
            ret = "%s, %s" % (lat, lng)
            if self.altitude:
                ret += (", %s m" % self.altitude)
            return ret
        
        ret = u"<#%s>" % unicode(self.pk)
        if self.water_body:
            ret += (u" %s" % self.water_body)
        if self.country and self.state:
            ret = u"%s: %s" % (self.country, self.state)
        elif self.country:
            ret = unicode(self.country)
        elif self.state:
            ret = unicode(self.state)
        
        if self.county or self.city:
            if self.county:
                ret += (u": %s county" % self.county)
            if self.city:
                ret += (u": %s" % self.city)
        elif self.loran_tds.count():
            ret += (u", ".join(map( unicode, self.loran_tds.all())))
        
        return ret

from django.db import models

from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.contacts.models import Contact

class VesselInfo(models.Model):
    '''\
    Note that this _isn't_ a model for individual vessels, but for a description
    of a vessel.
    '''

    contact = models.ForeignKey(
        Contact,
        related_name= "for_vessels",
        blank= True,
        null= True,
        help_text= "The contact for further details about the vessel, if necessary.",
    )
    imo_number = models.IntegerField(
        blank= True,
        null= True,
        help_text= "The International Maritime Organization number assigned to the ship. Should be a 7-digit number usually preceded with \"IMO\"."
        # Note that this most certainly _not_ unique, since we're just trying to
        # capture data for _one_ observatioin.
    )
    name = models.CharField(
        max_length= 255,
        blank= True,
    )
    flag = models.ForeignKey(
        Country,
        blank= True,
        null= True,
    )
    description = models.TextField(
        blank= True,
    )
    def __unicode__(self):
        ret = 'unnamed vessel'
        if self.name:
            ret = "%s" % self.name
        ret += " (vessel %i" % self.id
        if self.flag:
            ret += ", %s" % self.flag.iso
        ret += ')'
        return ret

class StrikingVesselInfo(VesselInfo):
    length = models.FloatField(
        blank= True,
        null= True,
        help_text= "length of the vessel, in meters.",
    )
    draft = models.FloatField(
        blank= True,
        null= True,
        help_text= "<i>maximum</i> draft, in meters.",
    )
    tonnage = models.FloatField(
        blank= True,
        null= True,
        help_text= "Gross Tonnage (GT). This is a unitless number, although it's a function of the total volume of a ship in cubic meters. Mainly noted because so many regulations make use of it."
    )
    # how tonnage relates to volume in cubic meters:
    # import math
    # tonnage_from_volume = lambda vol: vol * ( 0.2 + 0.02 * math.log10(vol))

    captain = models.ForeignKey(
        Contact,
        related_name= "captain_of",
        blank= True,
        null= True,
        help_text= "How to contact the captain and/or officer on duty at the time of the strike.",
    )
    speed = models.FloatField(
        blank= True,
        null= True,
        help_text= "In knots, over ground, at thte time of the strike",
        # yes there's really no way to convert from over-ground to over-water,
        # but it's either one or the other. GPS gives you over-ground.
    )



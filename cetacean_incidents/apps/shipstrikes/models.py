from django.db import models
from django.core.urlresolvers import reverse

from cetacean_incidents.apps.vessels.models import VesselInfo
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.incidents.models import Case, ObservationExtension

class StrikingVesselInfo(VesselInfo):
    length = models.FloatField(
        blank= True,
        null= True,
        help_text= "Length of the vessel, in meters.",
    )
    draft = models.FloatField(
        blank= True,
        null= True,
        help_text= "Maximum draft, in meters.",
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
        help_text= "In knots, over ground, at the time of the strike",
        # yes there's really no way to convert from over-ground to over-water,
        # but it's either one or the other. GPS gives you over-ground.
    )

    import_notes = models.TextField(
        blank= True,
        editable= False, # note that this only means it's not editable in the admin interface
        help_text= "field to be filled in by import scripts for data they can't assign to a particular field",
    )
    
class Shipstrike(Case):

    @models.permalink
    def get_absolute_url(self):
        return('shipstrike_detail', [str(self.id)])

    def get_edit_url(self):
        return reverse('edit_shipstrike', args=[self.id])

class ShipstrikeObservation(ObservationExtension):

    striking_vessel = models.OneToOneField(
        StrikingVesselInfo,
        blank= True,
        null= True,
    )

    def get_observation_view_data(self):
        # avoid circular imports
        from views import get_shipstrikeobservation_view_data
        return get_shipstrikeobservation_view_data(self)

    class Meta:
        verbose_name = "Observation shipstrike-data"
        verbose_name_plural = verbose_name


from django.db import models

from cetacean_incidents.apps.vessels.models import VesselInfo
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.incidents.models import Case, Observation, _observation_post_save

class StrikingVesselInfo(VesselInfo):
    length = models.FloatField(
        blank= True,
        null= True,
        help_text= "length of the vessel, in meters.",
    )
    draft = models.FloatField(
        blank= True,
        null= True,
        help_text= "maximum draft, in meters.",
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
    
class ShipstrikeObservation(Observation):
    striking_vessel = models.OneToOneField(
        StrikingVesselInfo,
        blank= True,
        null= True,
    )

# TODO how to inherit signal handlers?
models.signals.post_save.connect(_observation_post_save, sender=ShipstrikeObservation)

class Shipstrike(Case):
    observation_model = ShipstrikeObservation

Case.register_subclass(Shipstrike)


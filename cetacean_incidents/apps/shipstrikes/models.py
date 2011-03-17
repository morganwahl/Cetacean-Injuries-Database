from django.core.urlresolvers import reverse
from django.db import models

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.incidents.models import (
    Case,
    Observation,
    ObservationExtension,
)

from cetacean_incidents.apps.vessels.models import VesselInfo

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

guard_deletes(Contact, StrikingVesselInfo, 'captain')
    
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

# TODO generalize this for all ObservationExtensions
def add_shipstrike_extension_handler(sender, **kwargs):
    # sender shoulde be Observation.cases.through
    action = kwargs['action']
    if action == 'post_add':
        reverse = kwargs['reverse']
        if not reverse:
            # observation.cases.add(<some cases>)
            # kwargs['instance'] is observation
            # kwargs['model'] is Case
            # kwargs['pk_set'] is a iterable of Case PK's
            obs = kwargs['instance']
            # do we already have an E.OE.
            try:
                obs.shipstrikes_shipstrikeobservation
                return
            except ShipstrikeObservation.DoesNotExist:
                # are any of the cases Shipstrikes
                if Shipstrike.objects.filter(pk__in=kwargs['pk_set']):
                    # be sure not to overwrite an existing extension
                    try:
                        obs.shipstrikes_shipstrikeobservation
                    except ShipstrikeObservation.DoesNotExist:
                        ShipstrikeObservation.objects.create(
                            observation_ptr=obs,
                        )
        else:
            # shipstrike.observation_set.add(<some observations>)
            # kwargs['instance'] is shipstrike
            # kwargs['model'] is Observation
            # kwargs['pk_set'] is a iterable of Observation PK's
            case = kwargs['instance']
            if not isinstance(case, Shipstrike):
                return
            # add E.OE. to any obs that don't already have them
            for o in Observation.objects.filter(pk__in=kwargs['pk_set']):
                # be sure not to overwrite an existing extension
                try:
                    o.shipstrikes_shipstrikeobservation
                except ShipstrikeObservation.DoesNotExist:
                    ShipstrikeObservation.objects.create(
                        observation_ptr=o,
                    )

models.signals.m2m_changed.connect(
    sender= Observation.cases.through,
    receiver= add_shipstrike_extension_handler,
    dispatch_uid= 'observation_cases__add_shipstrike_extension__m2m_changed',
)


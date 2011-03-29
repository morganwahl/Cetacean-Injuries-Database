from django.db import models

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.countries.models import Country

from cetacean_incidents.apps.delete_guard import guard_deletes

class VesselTag(models.Model):
    name = models.CharField(
        max_length= 512,
        unique= True,
    )
    
    def __unicode__(self):
        return self.name
        ordering = ('id')

class VesselInfo(models.Model):
    # TODO perhaps a name-change is in order? Like, observer platform?
    '''\
    Note that this _isn't_ a model for data on individual vessels, but for a
    description of a vessel.
    '''

    vessel_tags = models.ManyToManyField(
        'VesselTag',
        blank= True,
        null= True,
        verbose_name= "vessel types",
        help_text= "What all categories would this vessel fit into?",
    )
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
        verbose_name= "IMO number",
        help_text= "The International Maritime Organization number assigned to the boat. Should be a 7-digit number usually preceded with \"IMO\"."
        # Note that this most certainly _not_ unique, since we're just trying to
        # capture data for _one_ observatioin.
    )
    name = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "Vessel name",
    )
    home_port = models.CharField(
        max_length= 511,
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
        ret += " ("
        if self.id: # unsaved entries won't have IDs
            ret += "vessel %i" % self.id
        else:
            ret += "unsaved vessel"
        if self.flag:
            ret += ", "
            ret += "%s" % self.flag.iso
        ret += ')'
        return ret

guard_deletes(Contact, VesselInfo, 'contact')
guard_deletes(Country, VesselInfo, 'flag')


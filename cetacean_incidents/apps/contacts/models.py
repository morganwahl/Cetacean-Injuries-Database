from django.db import models
from django.db.models import Q

from cetacean_incidents.apps.clean_cache import Smidgen

from cetacean_incidents.apps.documents.models import Documentable

class Organization(models.Model):
    
    name = models.CharField(
        max_length= 1023,
    )
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name

class AbstractContact(models.Model):
    # This exists so GearOwner can inherit all the fields from Contact but keep
    # them in a separate table.

    name = models.CharField(
        max_length= 1023,
        blank= True,
        null= True,
        help_text= u"The contact's name. Appears in lists of contacts.",
    )
    person = models.NullBooleanField(
        blank= True,
        null= True,
        default= True,
        help_text= u"Is this a person? (i.e. not an organization)",
    )
    
    phone = models.CharField(
        max_length= 255,
        blank= True,
        verbose_name= "phone number",
    )
    
    email = models.EmailField(
        blank= True,
        verbose_name= "email address",
    )
    
    address = models.TextField(
        max_length= 1023,
        blank= True,
        help_text= "mailing address",
    )
    
    notes = models.TextField(
        blank= True,
        help_text= u"""anything to note about this contact info? e.g. office 
            hours, alternative phone numbers, etc.""",
    )
    
    def __unicode__(self):
        if self.name:
            return self.name
        
        if self.pk:
            return "<unnamed contact> (#%06d)" % self.pk
            
        return "<unnamed contact> (unsaved)"

    class Meta:
        abstract = True

class Contact(AbstractContact, Documentable):
    """A contact is a name of a person _or_ organization, preferably with some
    way of contacting them. 
    
    Note that only one each of phone, email, etc. is given so that contacts
    just have a primary phone or email to contact them at. Other ones could be
    noted in the 'notes' field, if necessary.

    """

    # should default to name. see save() func below
    sort_name = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= u"""Used in sorting contacts. If left blank, will be filled
            in with the same value as 'name'.
        """,
    )

    # TODO properties probably shouldn't do queries
    @property
    def observed_ordered(self):
        return self.observed.order_by(
            'datetime_observed',
            'datetime_reported',
        )

    # TODO properties probably shouldn't do queries
    @property
    def reported_ordered(self):
        return self.reported.order_by(
            'datetime_reported',
            'datetime_observed',
        )
    
    def observed_or_reported_ordered(self):
        observed = Q(observer= self)
        reported = Q(reporter= self)
        # doing this here avoids circular imports
        from cetacean_incidents.apps.incidents.models import Observation
        return Observation.objects.filter(observed | reported).order_by(
            'datetime_observed',
            'datetime_reported',
        )

    affiliations = models.ManyToManyField(
        Organization,
        related_name = 'contacts',
        blank= True,
        null= True,
        help_text= u"""The organization(s) that this contact is affilitated
            with, if any. For contacts that are themselves organizations, give
            a more general org. that they're part of, if any. (e.g. 'Coast
            Guard'). The idea is to track indivdual people or orgs (whichever
            makes more sense as a contact for a particular observation), but
            still group them into sets. For example, a contact might be for the
            Boston Coast Guard office, but it would have a 'Coast Guard'
            affiliation, so that one could easily answer questions like "How
            many reports did we get from the Coast Guard last year?"
        """,
    )

    def clean(self):
        # TODO using validation method to fill in default
        # TODO make 'sort_name' blank in the interface if it's the same as name
        if not self.sort_name:
            self.sort_name = self.name
    
    def get_html_options(self):
        options = super(Contact, self).get_html_options()
        
        # AbstractContact.__unicode__ uses name
        if not 'cache_deps' in options:
            options['cache_deps'] = Smidgen()
        options['cache_deps'] = Smidgen({
            self: ('name',)
        })
        
        return options
    
    @models.permalink
    def get_absolute_url(self):
        return ('contact_detail', [str(self.pk)]) 
    
    class Meta:
        ordering = ('sort_name', 'name', 'documentable_ptr')


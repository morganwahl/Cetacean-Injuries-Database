from django.db import models

class Organization(models.Model):
    
    name = models.CharField(
        max_length= 1023,
    )
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name

# This exists so GearOwner can inherit all the fields from Contact but keep them
# in a separate table.
class AbstractContact(models.Model):
    '''\
    A contact is a name of a person _or_ organization, preferably with some way
    of contacting them.
    '''
    name = models.CharField(
        max_length= 1023,
        blank= True,
        null= True,
    )
    person = models.NullBooleanField(
        blank= True,
        null= True,
        default= True,
        help_text= "Is this a person? (i.e. not an organization)"
    )
    
    # Note that only one of each thing is given so that contacts just have a 
    # primary phone or email to contact them at. Other ones could be noted in 
    # 'notes' field, if necessary.
    
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
        help_text= "anything to note about this contact info? e.g. office hours, alternative phone numbers, etc."
    )
   
    def __unicode__(self):
        if self.name:
            return self.name
        else:
            return "contact #%05d" % self.id

    class Meta:
        abstract = True

class Contact(AbstractContact):

    # should default to name. see save() func below
    sort_name = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "leave blank if same as name",
    )

    affiliations = models.ManyToManyField(
        Organization,
        related_name = 'contacts',
        blank= True,
        null= True,
        help_text= '''\
        The organization(s) that this contact is affilitated with, if any. For contacts that are themselves organizations, give a more general org. that they're part of, if any. (I.e. 'Coast Guard'). The idea is to track indivdual people or orgs (whichever makes more sense as a contact for a particular observation), but still group them into sets. I.e. a contact might be for the Boston Coast Guard office, but it would have an affiliation to simple 'Coast Guard', so that one could easily answer questions like "How many reports did we get from the Coast Guard last year?"
        ''',
    )
    
    @models.permalink
    def get_absolute_url(self):
        return ('contact_detail', [str(self.id)]) 

    class Meta:
        ordering = ('sort_name', 'name', 'id')


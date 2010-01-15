from django.db import models

class Organization(models.Model):
    
    name = models.CharField(
        max_length= 1023,
    )
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name

class Contact(models.Model):
    '''\
    A contact is a name of a person _or_ organization preferably with some way
    of contacting them.
    '''
    name = models.CharField(
        max_length= 1023,
    )
    # should default to name. see save() func below
    sort_name = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "leave blank if same as name",
    )
    person = models.BooleanField(
        default= True,
        help_text= "Is this a person? (i.e. not an organization)"
    )
    
    affiliations = models.ManyToManyField(
        Organization,
        blank= True,
        null= True,
        help_text= "The organization(s) that this contact is affilitated with, if any. For contacts that are themselves organizations, give a more general org. that they're part of, if any. (I.e. 'Coast Guard')",
        related_name = 'contacts',
    )
   
    def save(self, force_insert=False, force_update=False):
        if not self.sort_name:
            self.sort_name = self.name 
        super(Contact, self).save(force_insert, force_update) # Call the "real" save() method.
    # TODO make 'sort_name' blank in the interface if it's the same as name

    class Meta:
        ordering = ('sort_name', 'name', 'id')

    def __unicode__(self):
        return self.name

class PhoneNumber(models.Model):
    number = models.CharField(
        max_length= 255,
    )
    
    contact = models.ForeignKey(
        Contact,
        related_name= 'phone_numbers',
    )
    
    def __unicode__(self):
        return unicode(self.number)
    
class Address(models.Model):
    address = models.TextField(
        max_length= 1023,
    )

    contact = models.ForeignKey(
        Contact,
        related_name= 'addresses',
    )

    def __unicode__(self):
        return unicode(self.address)

class Email(models.Model):
    address = models.EmailField()
    
    contact = models.ForeignKey(
        Contact,
        related_name= 'email_addresses',
    )
    
    def __unicode__(self):
        return unicode(self.address)

    class Meta:
        verbose_name = 'email address'
        verbose_name_plural = 'email addresses'


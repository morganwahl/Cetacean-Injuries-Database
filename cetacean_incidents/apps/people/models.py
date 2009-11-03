from django.db import models
from django.contrib.auth.models import User

class PhoneNumber(models.Model):
    # note that contact details are part of a person's affiliations.
    number = models.CharField(
        max_length= 255,
    )
    
    def __unicode__(self):
        return unicode(self.number)
    
class Address(models.Model):
    address = models.CharField(
        max_length= 1023,
    )

    def __unicode__(self):
        return unicode(self.address)

class Organization(models.Model):
    
    name = models.CharField(
        max_length= 1023,
    )
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name

class Person(models.Model):
    name = models.CharField(
        max_length= 1023,
    )
    # should default to name
    sort_name = models.CharField(
        max_length= 1023,
        blank= True,
        help_text= "defaults to 'name'",
    )
    
    # note that contact details are part of a person's affiliations.
    phones = models.ManyToManyField(
        PhoneNumber,
        blank= True,
        null= True,
        related_name= 'personal_phone_of',
        help_text= "any personal phone numbers (for work numbers use an " +
                   "Affiliation)."
    )
    addresses = models.ManyToManyField(
        Address,
        blank= True,
        null= True,
        related_name= 'personal_address_of',
        help_text= "addresses where this person can be reached (for work " +
                   "addresses use an Affiliation)"
    )
    email = models.EmailField(
        blank= True,
    )
    
    affiliated = models.ManyToManyField(
        Organization,
        through= 'Affiliation',
        blank= True,
        null= True,
    )
    
    user = models.ForeignKey(
        User,
        blank= True,
        null= True,
        help_text= "the user-account, if any, of this person"
    )

    def save(self, force_insert=False, force_update=False):
        if not self.sort_name:
            self.sort_name = self.name 
        super(Person, self).save(force_insert, force_update) # Call the "real" save() method.

    class Meta:
        ordering = ('sort_name', 'name')
        verbose_name = 'Person'
        verbose_name_plural = 'People'

    def __unicode__(self):
        return self.name

class Affiliation(models.Model):
    person = models.ForeignKey(Person)
    org = models.ForeignKey(Organization)
    current = models.BooleanField(
        default= True,
        help_text= 'is the person currently affiliated with this organization?',
    )
    phones = models.ManyToManyField(
        PhoneNumber,
        related_name= 'affilitation_phone_of',
        help_text= "the person's phone number at this organization",
    )
    addresses = models.ManyToManyField(
        Address,
        related_name= 'affilitation_address_of',
        help_text= "the address where this person can be reached at this " +
                   "organization"
    )

    class Meta:
        unique_together = ('person', 'org')

from django.db import models

class SecuredModel(models.Model):
    '''
    An abstract model that requires a User instance before it can be
    instantiated. It checks if that user has view permissions before
    instatiating, whether they have create/change permissions before saving
    (whichever's appropriate), and whether they have delete permissions before
    deleting.
    
    It also creates the view permission when the model class is initialized.
    (The other three are automatically created by Django.)
    '''
    
    raise NotImplementedError("Adding the view permission for SecuredModels is not yet implemented!")
    
    def __init__(self, user, *args, **kwargs):
        raise NotImplementedError("Instantiating SecuredModels is not yet implemented!")
        super(SecuredModel, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        raise NotImplementedError("Saving SecuredModels is not yet implemented!")
        super(SecuredModel, self).save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting SecuredModels is not yet implemented!")
        super(SecuredModel, self).delete(*args, **kwargs)
        
    class Meta:
        abstract = True
        

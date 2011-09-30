from os import path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from django.contrib.auth.models import User

# FIXME are we duplicateing settings.MEDIA_ROOT?
from cetacean_incidents.apps.documents.models import _storage_dir, _checkdir, _storage_dir_name

# FIXME are we duplicateing settings.MEDIA_ROOT?
_manual_dir_name = 'manual'
_manual_dir = path.join(_storage_dir, _manual_dir_name)
_checkdir(_manual_dir)
_manual_url = settings.MEDIA_URL + '{0}/{1}/'.format(_storage_dir_name, _manual_dir_name)
manual_storage = FileSystemStorage(
    location= _manual_dir,
    base_url= _manual_url,
)

class Manual(models.Model):

    manual_file = models.FileField(
        storage= manual_storage,
        upload_to= '%Y/', # note that duplicates will have _<number> 
                          # appended by default so nothing gets overwritten
    )
    
    date_uploaded = models.DateTimeField(
        auto_now_add= True,
    )
    
    uploader = models.ForeignKey(
        User,
        editable= False,
    )
    
    class Meta:
        ordering = ('-date_uploaded', 'id')


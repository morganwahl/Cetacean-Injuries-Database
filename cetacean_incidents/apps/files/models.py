'''\
Model to attach files to other Models. Attachments can use files that already
exist on the filesystem, or uploaded files. Or they can merely indicate that
such a file exists, but there's currently no copy available.
'''

import os
from os import path

from django.db import models
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.conf import settings

from utils import rand_string

def _checkdir(p):
    if not path.isdir(p):
        os.mkdir(p)

_storage_dir_name = 'files'
_storage_dir = path.join(settings.MEDIA_ROOT, _storage_dir_name)
_checkdir(_storage_dir)

_repos_dir_name = 'repositories'
_repos_dir = path.join(_storage_dir, _repos_dir_name)
_checkdir(_repos_dir)
def _repo_storage_factory(repo):
    return FileSystemStorage(
        location= path.join(_repos_dir, repo),
        base_url= settings.MEDIA_URL + _storage_dir_name + '/' + _repos_dir_name + '/' + repo + '/',
    )

_uploads_dir_name = 'uploads'
_uploads_dir = path.join(_storage_dir, _uploads_dir_name)
_checkdir(_uploads_dir)
upload_storage = FileSystemStorage(
    location= _uploads_dir,
    base_url= settings.MEDIA_URL + _storage_dir_name + '/' + _uploads_dir_name + '/'
)

class AttachmentType(models.Model):
    name = models.CharField(
        max_length= 255,
    )
    description = models.TextField(
        blank= True,
    )
    
    def __unicode__(self):
        return self.name

class Attachment(models.Model):
    
    attachment_type = models.ForeignKey(
        AttachmentType,
        blank= True,
        null= True,
    )
    
    storage_type = models.PositiveIntegerField(
        choices = (
            (0, 'no file'),
            (1, 'repository'),
            (2, 'uploaded file'),
        ),
        default= 0,
    )
    
    repo = models.FilePathField(
        max_length= 255,
        path= _repos_dir,
        blank= True,
    )
    
    # can't easily use a FilePathField, since the path depends on what 
    # 'repo' is set to
    repo_path = models.CharField(
        max_length= 2048,
        blank= True,
    )
    
    uploaded_file = models.FileField(
        storage= upload_storage,
        # add the date and 24 bits of randomness to make sure there aren't name
        # collisions
        upload_to= '%Y/%m/%d/' + rand_string(24),
        blank= True,
        null= True,
    )

    def clean(self):
        # if storage_type is 1, repo and repo_path are required
        if self.storage_type == 1:
            if not self.repo:
                raise ValidationError("You must specify the repository for files stored in repositories.")
            if not self.repo_path:
                raise ValidationError("You must specify the path within the repository for files stored in repositories.")
            # check that repo_path actually exists
            _repo_storage_factory(self.repo).exists(self.repo_path)
        
        # if storage_type is 2, uploaded_file is required
        if self.storage_type == 2:
            if not self.uploaded_file:
                raise ValidationError("You must choose a file to upload (or pick a different storage type)")
        
    def save(self):
        # assumes clean() has been called

        # if storage_type isn't 1, set the repo fields to None
        if self.storage_type != 1:
            self.repo_path = None
            self.repo = None
        
        # if storage_type isn't 2, delete any uploaded file
        if self.storage_type != 2:
            if self.uploaded_file:
                self.uploaded_file.delete(save=False)
    
    def __unicode__(self):
        result = ''
        if self.storage_type == 2:
            result += 'uploaded '
        if self.storage_type == 1:
            result += 'repository '
        if self.storage_type == 0:
            result += 'hypothetical '
        
        result += 'file'
        
        return result


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
import forms

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

# based on FilePathField
class DirectoryPathField(models.FilePathField):
    description = "Directory path"
    
    def formfield(self, **kwargs):
        defaults = {
            'path': self.path,
            'match': self.match,
            'recursive': self.recursive,
            'form_class': forms.DirectoryPathField,
        }
        defaults.update(kwargs)
        return super(DirectoryPathField, self).formfield(**defaults)
    
    def get_internal_type(self):
        return "FilePathField"

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
    
    repo = DirectoryPathField(
        max_length= 255,
        path= _repos_dir,
        blank= True,
        null= True,
        verbose_name= 'repository',
    )
    
    # can't easily use a FilePathField, since the path depends on what 
    # 'repo' is set to
    repo_path = models.CharField(
        max_length= 2048,
        blank= True,
        null= True,
        verbose_name= 'path within repository',
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
            if not _repo_storage_factory(self.repo).exists(self.repo_path):
                raise ValidationError("That file doesn't exist")
        
        # if storage_type is 2, uploaded_file is required
        if self.storage_type == 2:
            if not self.uploaded_file:
                raise ValidationError("You must choose a file to upload (or pick a different storage type)")
        
    def save(self, **kwargs):
        # assumes clean() has been called

        # if storage_type isn't 1, set the repo fields to None
        if self.storage_type != 1:
            self.repo_path = None
            self.repo = None
        
        # if storage_type isn't 2, delete any uploaded file
        if self.storage_type != 2:
            if self.uploaded_file:
                self.uploaded_file.delete(save=False)
        
        return super(Attachment, self).save(**kwargs)
    
    def __unicode__(self):
        if self.storage_type == 2:
            return u'upload {0.uploaded_file}'.format(self)

        if self.storage_type == 1:
            return 'repository {1}: {0.repo_path}'.format(self, path.relpath(self.repo, _repos_dir))

        if self.storage_type == 0:
            return 'hypothetical file #{0.id:06}'.format(self)
        
        return 'file'

    class Meta:
        ordering = ('attachment_type', 'storage_type', 'repo', 'repo_path', 'uploaded_file')


'''\
Model to attach files to other Models. Attachments can use files that already
exist on the filesystem ('repository' files), or uploaded files. Or they can
merely indicate that such a file exists, but there's currently no copy
available. Note that repository files include directories.
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

_storage_dir_name = 'attachments'
_storage_dir = path.join(settings.MEDIA_ROOT, _storage_dir_name)
_checkdir(_storage_dir)

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
    
    @property
    def url(self):
        return None
    
    @property
    def path(self):
        return None
    
    @models.permalink
    def get_absolute_url(self):
        return ('view_attachment', (self.id,))
    
    def __unicode__(self):
        return 'hypothetical file #{0.id:06}'.format(self)

    class Meta:
        ordering = ('attachment_type', 'id')

_uploads_dir_name = 'uploads'
_uploads_dir = path.join(_storage_dir, _uploads_dir_name)
_checkdir(_uploads_dir)
upload_storage = FileSystemStorage(
    location= _uploads_dir,
    base_url= settings.MEDIA_URL + _storage_dir_name + '/' + _uploads_dir_name + '/'
)

class UploadedFile(Attachment):

    # this is so we can store the original filename and use arbitrary names
    # for the uploaded files
    name = models.CharField(
        max_length= 255,
    )

    uploaded_file = models.FileField(
        storage= upload_storage,
        # add the date and 24 bits of randomness to make sure there aren't name
        # collisions
        upload_to= '%Y/%m/%d/' + rand_string(24),
    )

    @property
    def url(self):
        return self.uploaded_file.url

    @property
    def path(self):
        return self.uploaded_file.path

    @models.permalink
    def get_absolute_url(self):
        return ('view_uploadedfile', (self.id,))

    def __unicode__(self):
        return u'upload {0.uploaded_file}'.format(self)

    class Meta:
        ordering = ('attachment_type', 'name', 'id')

_repos_dir_name = 'repositories'
_repos_dir = path.join(_storage_dir, _repos_dir_name)
_checkdir(_repos_dir)
def _repo_storage_factory(repo):
    return FileSystemStorage(
        location= path.join(_repos_dir, repo),
        base_url= settings.MEDIA_URL + _storage_dir_name + '/' + _repos_dir_name + '/' + repo + '/',
    )

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

class RepositoryFile(Attachment):

    repo = DirectoryPathField(
        max_length= 255,
        path= _repos_dir,
        verbose_name= 'repository',
    )
    
    # can't easily use a FilePathField, since the path depends on what 
    # 'repo' is set to
    repo_path = models.CharField(
        max_length= 2048,
        verbose_name= 'path within repository',
    )
    
    @property
    def url(self):
        return _repo_storage_factory(self.repo).url(self.repo_path)

    @property
    def path(self):
        return _repo_storage_factory(self.repo).path(self.repo_path)

    def clean(self):
        # check that repo_path actually exists
        if not _repo_storage_factory(self.repo).exists(self.repo_path):
            raise ValidationError("That file doesn't exist")

    def __unicode__(self):
        return 'repository {1}: {0.repo_path}'.format(self, path.relpath(self.repo, _repos_dir))

    class Meta:
        ordering = ('attachment_type', 'repo', 'repo_path')
        unique_together = ('repo', 'repo_path')

def _get_detailed_attachment_instance(attachment_instance):
    for subclass in (UploadedFile, RepositoryFile):
        try:
            # TODO 'id' or 'pk'?
            return subclass.objects.get(attachment_ptr=attachment_instance.id)
        except subclass.DoesNotExist:
            pass
    return attachment_instance
Attachment.detailed_instance = _get_detailed_attachment_instance

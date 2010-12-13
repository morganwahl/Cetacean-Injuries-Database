'''\
Model of 'physical' files, forms, photos, etc. They may very well be files on a computer.
'''

import os
from os import path

from django.db import models
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.conf import settings

from django.contrib.auth.models import User

from utils import rand_string
from form_fields import DirectoryPathField as DirectoryPathFormField

def _checkdir(p):
    if not path.isdir(p):
        os.mkdir(p)

_storage_dir_name = 'documents'
_storage_dir = path.join(settings.MEDIA_ROOT, _storage_dir_name)
_checkdir(_storage_dir)

class DocumentType(models.Model):
    name = models.CharField(
        max_length= 255,
    )
    description = models.TextField(
        blank= True,
    )
    
    def __unicode__(self):
        return self.name

class Document(models.Model):
    
    document_type = models.ForeignKey(
        DocumentType,
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
        return ('view_document', (self.id,))
    
    def __unicode__(self):
        return 'document #{0.id:06}'.format(self)

    class Meta:
        ordering = ('document_type', 'id')

_uploads_dir_name = 'uploads'
_uploads_dir = path.join(_storage_dir, _uploads_dir_name)
_checkdir(_uploads_dir)
upload_storage = FileSystemStorage(
    location= _uploads_dir,
    base_url= settings.MEDIA_URL + _storage_dir_name + '/' + _uploads_dir_name + '/'
)

class UploadedFile(Document):

    # this is so we can store the original filename and use arbitrary names
    # for the uploaded files
    name = models.CharField(
        max_length= 255,
    )

    uploaded_file = models.FileField(
        storage= upload_storage,
        upload_to= '%Y/%m%d/', # note that duplicates will have _<number> 
                               # appended by default so nothing gets overwritten
    )
    
    uploader = models.ForeignKey(
        User,
        editable= False,
    )
    
    datetime_uploaded = models.DateTimeField(
        auto_now_add=True,
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
        ordering = ('document_type', 'name', 'id')

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
            'form_class': DirectoryPathFormField,
        }
        defaults.update(kwargs)
        return super(DirectoryPathField, self).formfield(**defaults)
    
    def get_internal_type(self):
        return "FilePathField"

class RepositoryFile(Document):

    repo = DirectoryPathField(
        max_length= 255,
        path= _repos_dir,
        verbose_name= 'repository',
    )
    
    @property
    def repo_name(self):
        return path.relpath(self.repo, _repos_dir)
    
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
    
    @property
    def name(self):
        return self.repo_path

    @property
    def is_dir(self):
        return path.isdir(self.path)
    
    def clean(self):
        # check that repo_path actually exists
        if not _repo_storage_factory(self.repo).exists(self.repo_path):
            raise ValidationError("That file doesn't exist")

    @models.permalink
    def get_absolute_url(self):
        return ('view_repositoryfile', (self.id,))

    def __unicode__(self):
        return u'repository file: {0.repo_name} \u2018{0.repo_path}\u2019'.format(self)
    class Meta:
        ordering = ('document_type', 'repo', 'repo_path')
        unique_together = ('repo', 'repo_path')

def _get_detailed_document_instance(document_instance):
    for subclass in (UploadedFile, RepositoryFile):
        try:
            # TODO 'id' or 'pk'?
            return subclass.objects.get(document_ptr=document_instance.id)
        except subclass.DoesNotExist:
            pass
    return document_instance
Document.detailed_instance = _get_detailed_document_instance


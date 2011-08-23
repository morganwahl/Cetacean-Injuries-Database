'''\
Model of 'physical' files, forms, photos, etc. They may very well be files on a computer.
'''

import os
from os import path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

from django.contrib.auth.models import User

from cetacean_incidents.apps.clean_cache import (
    CacheDependency,
    TestList,
)

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.generic_templates.templatetags import html_filter

from form_fields import DirectoryPathField as DirectoryPathFormField
from utils import rand_string

def _checkdir(p):
    if not path.isdir(p):
        os.mkdir(p)

# FIXME are we duplicateing settings.MEDIA_ROOT?
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
    
    class Meta:
        ordering = ('name', 'id')

class Specificable(models.Model):
    
    # TODO see InheritanceManager in 
    # https://github.com/carljm/django-model-utils#readme

    def specific_class(self):
        return self.specific_instance().__class__

    def specific_instance(self):
        '''\
        Returns the equivalent instance of the most-specific subclass of this
        instance's class.
        '''
        inst = None
        for subclass in self.__class__.__subclasses__():
            if subclass.objects.filter(pk=self.pk).exists():
                inst = subclass.objects.get(pk=self.pk)
                break
        if inst is None:
            return self
        return inst.specific_instance()
    
    class Meta:
        abstract = True

class Documentable(Specificable):
    '''\
    Any class you want to attach documents to should inherit from this one.
    '''
    
    # TODO could this be a property in a Meta class?
    def get_html_options(self):
        t = u'documentable.html'

        # TODO belongs in import app
        
        # avoid circular imports
        from cetacean_incidents.apps.csv_import import IMPORT_TAGS
        from cetacean_incidents.apps.tags.models import Tag
        
        c = {'needs_review': False}
        deps = CacheDependency(
            create= {
                Tag: TestList([
                    lambda inst: inst.entry == self,
                ])
            },
        )
        
        for tag in self.tag_set.all():
            deps |= CacheDependency(
                update= {
                    tag: TestList([True]),
                }
            )
            
            if not c['needs_review'] and tag.tag_text in IMPORT_TAGS:
                c['needs_review'] = True
                c['media_url'] = settings.MEDIA_URL
                deps |= CacheDependency(
                    delete= {
                        tag: TestList([True]),
                    }
                )
        
        return {
            'template': t,
            'context': c,
            'use_cache': True, # cache by default, since we hit the database to check for import tags
            'cache_deps': deps,
        }
    
    def __unicode__(self):
        if not self.id:
            return "<new Documentable>"
        return "Documentable entry #%06d" % self.id
    
# remove stale cache entries
def _documentable_post_save(sender, **kwargs):
    # sender should be Documentable
    
    if kwargs['created']:
        return
    
    documentable = kwargs['instance']
    cache_keys = html_filter.cache_keys(documentable)
    cache.delete_many(cache_keys)
        
models.signals.post_save.connect(
    sender= Documentable,
    receiver= _documentable_post_save,
    dispatch_uid= 'cache_clear__documentable_html__documentable__post_save',
)

class Document(Specificable):
    
    document_type = models.ForeignKey(
        DocumentType,
        blank= True,
        null= True,
    )
    
    attached_to = models.ForeignKey(
        Documentable,
        related_name= 'documents',
        blank= True,
        null= True,
        editable= False,
    )
    
    visible_to = models.ManyToManyField(
        User,
        related_name= 'can_view_documents',
        blank= True,
        null= True,
        verbose_name= 'restrict access to these users',
        help_text= 'Note that selecting no users implies that this document is visible to all users.',
    )
    
    def can_be_seen_by(self, user):
        if not self.visible_to.exists():
            return True
        if user.is_superuser:
            return True
        else:
            return user in self.visible_to.all()
    
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
        id_string = '#{0.id:06}'.format(self) if self.id else '(no ID)'
        doctype_string = unicode(self.document_type) if self.document_type else u'document'
        return u'%s %s' % (doctype_string, id_string)
    
    class Meta:
        ordering = ('document_type', 'id')

guard_deletes(DocumentType, Document, 'document_type')
guard_deletes(Documentable, Document, 'attached_to')

_uploads_dir_name = 'uploads'
_uploads_dir = path.join(_storage_dir, _uploads_dir_name)
_checkdir(_uploads_dir)
_uploads_url = settings.MEDIA_URL + '{0}/{1}/'.format(_storage_dir_name, _uploads_dir_name)
upload_storage = FileSystemStorage(
    location= _uploads_dir,
    base_url= _uploads_url,
)

class UploadedFile(Document):
    
    # TODO this could be moved to Document itself
    @classmethod
    def transmute_document(cls, doc, **kwargs):
        '''
        Turns a Document instance that isn't already an instance of one of
        Document's subclasses into an UploadedFile instance. Note that the given
        document's fields are copied into the returned UploadedFile, so any
        changes to the Document given will be overwritten when the UploadedFile
        is saved.
        '''
        
        if doc.specific_class() != Document:
            raise ValueError
        
        new_args = {}
        # TODO is this the correct Meta field to use? It doesn't include 
        # ManyToMany fields, but that's actually what we want here.
        for f in doc._meta.fields:
            new_args[f.attname] = getattr(doc, f.attname)
        new_args.update(kwargs)
        
        return UploadedFile(**new_args)
    
    # this is so we can store the original filename and use arbitrary names
    # for the uploaded files
    name = models.CharField(
        max_length= 255,
        blank= True,
        help_text= 'if left blank, the name of the uploaded file will be filled in',
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

    def clean(self):
        # it'd be nice if forms did this via JS, but that's just not do-able
        # in HTML.
        if self.name == '':
            self.name = path.basename(self.uploaded_file.name)

    @models.permalink
    def get_absolute_url(self):
        return ('view_uploadedfile', (self.id,))

    def __unicode__(self):
        return u'upload {0.uploaded_file}'.format(self)

    class Meta:
        ordering = ('document_type', 'name', 'id')

guard_deletes(User, UploadedFile, 'uploader')

_repos_dir_name = 'repositories'
_repos_dir = path.join(_storage_dir, _repos_dir_name)
_checkdir(_repos_dir)
_repos_url = settings.MEDIA_URL + _storage_dir_name + '/' + _repos_dir_name + '/'
def _repo_storage_factory(repo):
    return FileSystemStorage(
        location= path.join(_repos_dir, repo),
        base_url= _repos_url + repo + '/',
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
        max_length= 2000,
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


from django import forms

from django.contrib.auth.models import User

from cetacean_incidents.apps.merge_form.forms import MergeForm

from models import (
    Document,
    Documentable,
    RepositoryFile,
    UploadedFile,
)

class DocumentModelForm(forms.Form):
    '''\
    This form just has a select widget to choose a subclass of Document.
    '''
    
    # TODO get types from models?
    model_choices = []
    model_classes = {}
    # TODO disable RepositoryFile for now (until RepositoryFile.url is fixed)
    #for cls in (Document, UploadedFile, RepositoryFile):
    for cls in (Document, UploadedFile):
        model_choices.append( (cls.__name__, cls._meta.verbose_name) )
        model_classes[cls.__name__] = cls
    model_choices = tuple(model_choices)
    
    storage_type = forms.ChoiceField(
        choices= model_choices,
        required= True,
        initial= Document.__name__,
        widget= forms.RadioSelect,
    )

class DocumentForm(forms.ModelForm):
    
    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add visible_to to Meta.widgets.
    _f = Document._meta.get_field('visible_to')
    visible_to = forms.ModelMultipleChoiceField(
        queryset= User.objects.all(),
        required= _f.blank != True,
        widget= forms.CheckboxSelectMultiple,
        help_text= u'Note that selecting no users implies that this document is visible to all users.',
        label= _f.verbose_name.capitalize(),
    )
    
    # TODO don't allow users to make a document invisible to themselves
    
    class Meta:
        model = Document

class UploadedFileForm(DocumentForm):
    
    class Meta(DocumentForm.Meta):
        model = UploadedFile

class RepositoryFileForm(DocumentForm):
    
    class Meta(DocumentForm.Meta):
        model = RepositoryFile

class NewDocumentForm(DocumentForm):
    
    is_uploadedfile = forms.BooleanField(
        required= False,
        initial= False,
        label= "Is it an uploaded file?",
        help_text= "Do you want to upload a copy of this document?",
    )
    
    class Meta:
        model = Document
    
class NewUploadedFileForm(forms.ModelForm):
    """
    A form for UploadedFiles intended to be used along with NewDocumentForm.
    """
    
    class Meta:
        model = UploadedFile
        exclude = NewDocumentForm.base_fields.keys()

# Not intended for actual instantiation, just puts the duplicate-document 
# removal code in one place
class DocumentableMergeForm(MergeForm):

    def save(self, commit=True):
        result = super(DocumentableMergeForm, self).save(commit)
        
        # remove duplicate documents that don't have an uploaded file
        doc_types_seen = set()
        for d in result.documents.all():
            d = d.specific_instance()
            # only handle vanilla Documents
            if not isinstance(d, Document):
                continue
            if d.document_type in doc_types_seen:
                d.delete()
            else:
                doc_types_seen.add(d.document_type)
        
        return result

    class Meta:
        model = Documentable
        

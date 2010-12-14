from django import forms

from models import Document, UploadedFile, RepositoryFile

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
    
    class Meta:
        model = Document

class UploadedFileForm(DocumentForm):
    
    class Meta(DocumentForm.Meta):
        model = UploadedFile

class RepositoryFileForm(DocumentForm):
    
    class Meta(DocumentForm.Meta):
        model = RepositoryFile


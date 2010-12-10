from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

import os
from os import path

from django.contrib.auth.decorators import login_required

from django.core.files import File
from forms import DocumentModelForm, DocumentForm, UploadedFileForm, RepositoryFileForm

from models import Document, UploadedFile, RepositoryFile

@login_required
def view_document(request, a):
    if not isinstance(a, Document):
        a = Document.objects.get(id=a)
    a = a.detailed_instance()
    
    if isinstance(a, UploadedFile):
        return redirect(view_uploadedfile, a.id, permanent=True)
    if isinstance(a, RepositoryFile):
        return redirect(view_repositoryfile, a.id, permanent=True)
    
    return render_to_response(
        'documents/view_document.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_uploadedfile(request, a):
    if not isinstance(a, UploadedFile):
        a = UploadedFile.objects.get(id=a)
    
    return render_to_response(
        'documents/view_uploadedfile.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_repositoryfile(request, a):
    if not isinstance(a, RepositoryFile):
        a = RepositoryFile.objects.get(id=a)
    
    return render_to_response(
        'documents/view_repositoryfile.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request),
    )

# utility methods for use with Document forms
def _get_documentforms(request):
    form_classes = {
        'model': DocumentModelForm,
        'document': DocumentForm,
        'uploaded_file': UploadedFileForm,
        'repository_file': RepositoryFileForm,
    }
    
    form_kwargs = {}
    for name in form_classes.keys():
        form_kwargs[name] = {
            'prefix': name,
        }
    
    if request.method == 'POST':
        for name in form_classes.keys():
            form_kwargs[name]['data'] = request.POST
        form_kwargs['uploaded_file']['files'] = request.FILES
    
    forms = {}
    for name, cls in form_classes.items():
        forms[name] = cls(**form_kwargs[name])
    
    return forms

def _save_documentforms(request, forms):
    if forms['model'].is_valid():
        docform = {
            'Document': forms['document'],
            'UploadedFile': forms['uploaded_file'],
            'RepositoryFile': forms['repository_file'],
        }[forms['model'].cleaned_data['storage_type']]
        
        if docform.is_valid():
            doc = docform.save(commit=False)
            if forms['model'].cleaned_data['storage_type'] == 'UploadedFile':
                doc.uploader = request.user
            doc.save()
            docform.save_m2m()
            
            return doc


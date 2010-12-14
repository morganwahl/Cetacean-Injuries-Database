from django.core.files import File
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

import os
from os import path

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

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

@login_required
@permission_required('documents.change_document')
def edit_document(request, document_id):
    
    d = Document.objects.get(id=document_id).detailed_instance()
    
    form_class = {
        Document: DocumentForm,
        UploadedFile: UploadedFileForm,
        RepositoryFile: RepositoryFileForm,
    }[d.__class__]
    
    if request.method == 'POST':
        form = form_class(data=request.POST, instance=d)
        if form.is_valid():
            return redirect(form.save())
    else:
        form = form_class(instance=d)
    
    return render_to_response(
        'documents/edit_document.html',
        {
            'd': d,
            'form': form,
            'media': form.media,
        },
        context_instance = RequestContext(request),
    )

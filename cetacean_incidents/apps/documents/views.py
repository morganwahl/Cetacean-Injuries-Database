from django.core.files import File
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.conf import settings

import os
from os import path

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

from forms import DocumentModelForm, DocumentForm, UploadedFileForm, RepositoryFileForm

from models import Document, UploadedFile, RepositoryFile

@login_required
def view_document(request, d):
    if not isinstance(d, Document):
        d = Document.objects.get(id=d)
    d = d.specific_instance()
    
    if isinstance(d, UploadedFile):
        return redirect(view_uploadedfile, d.id, permanent=True)
    if isinstance(d, RepositoryFile):
        return redirect(view_repositoryfile, d.id, permanent=True)
    
    return render_to_response(
        'documents/view_document.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_uploadedfile(request, d):
    if not isinstance(d, UploadedFile):
        d = UploadedFile.objects.get(id=d)
    
    return render_to_response(
        'documents/view_uploadedfile.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_repositoryfile(request, d):
    if not isinstance(d, RepositoryFile):
        d = RepositoryFile.objects.get(id=d)
    
    return render_to_response(
        'documents/view_repositoryfile.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('documents.change_document')
def edit_document(request, document_id):
    
    d = Document.objects.get(id=document_id).specific_instance()
    
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
    
@login_required
@permission_required('documents.delete_document')
def delete_document(request, document_id):
    
    d = Document.objects.get(id=document_id)
    
    # requests that alter data must be posts
    if request.method == 'POST':
        # for now, don't delete the uploaded file
        d.delete()
        
        return render_to_response(
            'documents/document_deleted.html',
            {'d': d},
            context_instance= RequestContext(request),
        )

    return redirect(d)

from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

import os
from os import path

from django.core.files import File

from models import Document, UploadedFile, RepositoryFile

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


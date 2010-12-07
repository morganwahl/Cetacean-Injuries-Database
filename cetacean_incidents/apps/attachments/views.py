from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

import os
from os import path

from django.core.files import File

from models import Attachment, UploadedFile, RepositoryFile

def view_attachment(request, a):
    if not isinstance(a, Attachment):
        a = Attachment.objects.get(id=a)
    a = a.detailed_instance()
    
    if isinstance(a, UploadedFile):
        return redirect(view_uploadedfile, a.id, permanent=True)
    
    return render_to_response(
        'attachments/view_attachment.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request)
    )

def view_uploadedfile(request, a):
    if not isinstance(a, UploadedFile):
        a = UploadedFile.objects.get(id=a)
    
    return render_to_response(
        'attachments/view_uploadedfile.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request),
    )


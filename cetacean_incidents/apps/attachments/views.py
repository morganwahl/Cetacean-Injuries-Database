from django.shortcuts import render_to_response
from django.template import RequestContext

import os
from os import path

from django.core.files import File

from models import Attachment

def view_attachment(request, a_id):
    a = Attachment.objects.get(id=a_id)
    
    a_path = a.path
    if path.isdir(a_path):
        files = []
        for f in os.listdir(a_path):
            f = open(path.join(a_path, f), 'rb')
            f = File(f)
            files.append(f)
        
        return render_to_response(
            'attachments/view_directory.html',
            {
                'attachment': a,
                'files': files,
            },
            context_instance= RequestContext(request),
        )
    
    return render_to_response(
        'attachments/view_file.html',
        {
            'attachment': a,
        },
        context_instance= RequestContext(request)
    )

def view_repo_file

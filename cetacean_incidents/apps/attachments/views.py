from django.shortcuts import render_to_response
from django.template import RequestContext

import os
from os import path

from django.core.files import File

from models import Attachment

def view_attachment(request, a):
    if not isinstance(a, Attachment):
        a = Attachment.objects.get(id=a)
    
    
    return render_to_response(
        'attachments/view_attachment.html',
        {
            'a': a,
        },
        context_instance= RequestContext(request)
    )


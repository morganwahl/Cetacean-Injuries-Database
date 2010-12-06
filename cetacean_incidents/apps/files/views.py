from django.shortcuts import render_to_response
from django.template import RequestContext

from models import Attachment

def view_attachment(request, attachment_id):
    attachment = Attachment.objects.get(id=attachment_id)
    return render_to_response(
        'files/view_attachment.html',
        {
            'attachment': attachment,
        },
        context_instance= RequestContext(request)
    )


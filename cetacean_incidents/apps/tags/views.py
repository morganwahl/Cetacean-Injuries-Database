from django.forms import Form
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

from models import Tag

@login_required
@permission_required('tags.delete_tag')
def delete_tag(request, tag_id):
    
    tag = Tag.objects.get(id=tag_id)
    
    if request.method == 'POST':
        # use a dummy form just to verify the CSRF token
        form = Form(request.POST)
        if form.is_valid():
            tag.delete()

    return redirect(tag.entry.specific_instance())


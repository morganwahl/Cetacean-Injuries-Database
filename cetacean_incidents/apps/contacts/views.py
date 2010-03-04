from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from models import Contact
from forms import ContactForm

@login_required
def _create_or_edit_contact(request, contact_id=None):
    if not contact_id is None:
        # we're editing an existing contact
        contact = Contact.objects.get(id=contact_id)
        template = 'contacts/edit_contact.html'
    else:
        # we're creating a new contact
        contact = None # the default for ContactForm(instance=)
        template = 'contacts/create_contact.html'
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            return redirect('contact_detail', contact.id)
    else:
        form = ContactForm(instance=contact)
    return render_to_response(
        template,
        {
            'contact': contact,
            'form': form,
        },
        context_instance= RequestContext(request),
    )

@login_required
def create_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)

@login_required
def edit_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)


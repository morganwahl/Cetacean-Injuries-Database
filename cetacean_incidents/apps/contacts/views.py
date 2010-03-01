from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from models import Contact
from forms import ContactForm

@login_required
def create_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            new_contact = form.save()
            return redirect('contact_detail', new_contact.id)
    else:
        form = ContactForm()
    return render_to_response(
        'contacts/create_contact.html',
        {
            'form': form,
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_contact(request, contact_id):
    contact = Contact.objects.get(id=contact_id)
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            return redirect('contact_detail', contact.id)
    else:
        form = ContactForm(instance=contact)
    return render_to_response(
        'contacts/edit_contact.html',
        {
            'contact': contact,
            'form': form,
        },
        context_instance= RequestContext(request),
    )


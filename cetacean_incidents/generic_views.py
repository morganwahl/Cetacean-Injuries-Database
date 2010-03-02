from django.views.generic.list_detail import object_list as old_object_list
from django.views.generic.list_detail import object_detail as old_object_detail
from django.contrib.auth.decorators import login_required

@login_required
def object_list(*args, **kwargs):
    return old_object_list(*args, **kwargs)

@login_required
def object_detail(*args, **kwargs):
    return old_object_detail(*args, **kwargs)


from django.views.generic.list_detail import object_list as old_object_list
from django.views.generic.list_detail import object_detail as old_object_detail
from django.views.generic.simple import direct_to_template as old_direct_to_template
from django.contrib.auth.decorators import login_required

@login_required
def object_list(*args, **kwargs):
    return old_object_list(*args, **kwargs)

@login_required
def object_detail(*args, **kwargs):
    return old_object_detail(*args, **kwargs)

@login_required
def direct_to_template(*args, **kwargs):
    return old_direct_to_template(*args, **kwargs)


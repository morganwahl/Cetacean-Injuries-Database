'''\
Before delete an instance of a Model, check that references to it are removed
to prevent cascading deletes by the database back-end.
'''

from django.db import models

class CascadedDeleteError(Exception):
    
    def __init__(self, instance_to_delete, referring_instance, field_name):
        self.instance_to_delete = instance_to_delete
        self.referring_instance = referring_instance
        self.field_name = field_name

    def __unicode__(self):
        return "Can't delete %r: referenced by %r on field '%s'" % (
            self.instance_to_delete,
            self.referring_instance,
            self.field_name,
        )

def guard_deletes(model, referring_model, field_name):
    def handler(sender, **kwargs):
        instance = kwargs['instance']
        referrers = referring_model.objects.filter(**{field_name: instance})
        if referrers.exists():
            raise CascadedDeleteError(
                instance,
                referrers[0],
                field_name,
            )

    models.signals.pre_delete.connect(
        handler,
        sender=model,
        dispatch_uid= u"delete_guard__%s__%s_%s" % (
            model._meta.db_table,
            referring_model._meta.db_table,
            field_name,
        ),
        weak= False,
    )


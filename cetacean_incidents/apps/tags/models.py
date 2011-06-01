from django.db import models

from django.contrib.auth.models import User

from cetacean_incidents.apps.delete_guard import guard_deletes

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.generic_templates.templatetags import html_filter

class Tag(models.Model):
    
    entry = models.ForeignKey(
        Documentable,
    )
    
    user = models.ForeignKey(
        User,
    )
    
    datetime_tagged = models.DateTimeField(
        auto_now_add=True,
    )
    
    tag_text = models.CharField(
        db_index=True,
        max_length=1024,
    )

    def __unicode__(self):
        return u"tag on %s: \u201c%s\u201d" % (self.entry.specific_instance(), self.tag_text)

# Allow deletion of a Documentable to casecade to Tags view Tags.entry
guard_deletes(User, Tag, 'user')


# TODO this is somewhat misplaced as the code that makes html_filter produce
# these cache entries is elsewhere

# remove stale cache entries
def _tag_post_save_or_post_delete(sender, **kwargs):
    # sender should be Tag
    
    tag = kwargs['instance']

    # avoid circular imports
    from cetacean_incidents.apps.csv_import import IMPORT_TAGS
    if not tag.tag_text in IMPORT_TAGS:
        return

    cache_keys = html_filter.cache_keys(tag.entry)
    cache.delete_many(cache_keys)

models.signals.post_save.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__documentable_html__tag__post_save',
)
models.signals.post_delete.connect(
    sender= Tag,
    receiver=  _tag_post_save_or_post_delete,
    dispatch_uid= 'cache_clear__documentable_html__tag__post_delete',
)


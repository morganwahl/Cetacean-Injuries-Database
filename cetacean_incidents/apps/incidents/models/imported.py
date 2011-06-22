from django.db import models

class Importable(models.Model):
    '''\
    Mix-in class for imported entries.
    '''

    import_notes = models.TextField(
        blank= True,
        editable= False,
        help_text= u"""Used by import scripts to add notes to the entries they create.""",
    )
    
    class Meta:
        abstract = True


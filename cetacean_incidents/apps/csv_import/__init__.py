CURRENT_IMPORT_TAG = u"This entry was created by an automated import and has not yet been reviewed by a human. See 'Import Notes' for details."

IMPORT_TAGS = set((
    CURRENT_IMPORT_TAG,
    u"This entry was created by an automated import has not yet been reviewed by a human. See 'Import Notes' for details.",
))

class UnrecognizedFieldError(ValueError):
    
    # require a column name
    def __init__(self, column_name, *args, **kwargs):
        super(UnrecognizedFieldError, self).__init__(u'"%s"' % column_name, *args, **kwargs)


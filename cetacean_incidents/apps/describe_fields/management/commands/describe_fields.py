from django.core.management.base import (
    AppCommand,
    CommandError,
)
from django.db import models

type_names = {
    models.AutoField: 'autogenerated id',
    models.BooleanField: 'true/false',
    models.CharField: 'text',
    models.DateField: 'date',
    models.ForeignKey: 'reference to one entry in another table',
    models.EmailField: 'email',
    models.OneToOneField: 'unique reference to one entry in another table',
    models.IntegerField: 'integer',
    models.TextField: 'text',
    models.NullBooleanField: 'true/false/null',
    models.ManyToManyField: 'reference to multiple entries in another table',
}

class Command(AppCommand):
    help = 'Prints a human-readable description of the app\'s fields.'

    def handle_app(self, app, **options):
        for c in models.get_models(app):
            m = c._meta
            
            if m.abstract:
                continue

            print "----- %s -----" % (c.__name__)
            
            if m.verbose_name != c.__name__.lower():
                print "display-name: \"%s\"" % unicode(m.verbose_name)
            if m.verbose_name_plural != m.verbose_name + 's':
                print "display-name plural: \"%s\"" % unicode(m.verbose_name_plural)
            
            if m.db_table != "%s_%s" % (m.app_label, c.__name__.lower()):
                print "table name: \"%s\"" % m.db_table
            
            if c.__doc__:
                print
                print c.__doc__
            
            print
            
            for f in m.many_to_many + m.local_fields:
                if isinstance(f, models.AutoField):
                    continue
            
                #f_type = type_names[f.__class__]
                f_type = unicode(f.description) % {
                    'max_length': f.max_length,
                }
                
                print "\"%s\" %s" % (f.attname, f_type)
                if f.rel:
                    print "\treferences %s" % f.rel.to.__name__
                
                if f.verbose_name != f.attname:
                    print "\tdisplay-name: \"%s\"" % unicode(f.verbose_name)
                
                if f.max_length:
                    print "\tmax length: %d" % f.max_length
                
                if f.choices:
                    print "\tchoices:"
                    for choice in f.choices:
                        print "\t\t\"%s\" (stored as \"%s\")" % (
                            choice[1],
                            choice[0],
                        )

                if f.default != models.fields.NOT_PROVIDED:
                    print "\tdefault: %s" % f.default
                
                if not f.blank:
                    print "\tcan't be left blank"
                
                if not f.null:
                    print "\tcan't be made null"
                
                if f.help_text:
                    print "\thelp text:"
                    print "\t\t%s" % f.help_text
                    
                print
            
        print

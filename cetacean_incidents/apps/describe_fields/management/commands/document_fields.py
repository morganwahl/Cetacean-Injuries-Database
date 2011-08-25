from django.core.management.base import (
    AppCommand,
    CommandError,
)
from django.db import models, connection
from django.utils.datastructures import SortedDict

from lxml import etree

DOCBOOK_NAMESPACE = u'http://docbook.org/ns/docbook'
XML_NAMESPACE = u'http://www.w3.org/XML/1998/namespace'
#DOC = "{%s}" % DOCBOOK_NAMESPACE
#XML = "{%s}" % XML_NAMESPACE
#NS = {None : DOCBOOK_NAMESPACE, 'xml': XML_NAMESPACE}
DOC = ''

def _py_id(obj):
    qualified_name = u'{0}.{1}'.format(obj.__module__, obj.__name__)
    return u'py_' + qualified_name

def _add_varlist_entry(varlist, term_contents, item_contents):
    entry = etree.SubElement(varlist, DOC + 'varlistentry')
    term = etree.SubElement(entry, DOC + 'term')
    item = etree.SubElement(entry, DOC + 'listitem')
    para = etree.SubElement(item, DOC + 'para')
    if isinstance(term_contents, basestring):
        term.text = term_contents
    else:
        term.append(term_contents)
    if isinstance(item_contents, basestring):
        para.text = item_contents
    else:
        para.append(item_contents)

def _dict_section(title, props):
    section = etree.Element(DOC + 'section')
    title_element = etree.SubElement(section, DOC + 'title')
    title_element.text = title

    varlist = etree.Element(DOC + 'variablelist')

    for name, item in props.items():
        _add_varlist_entry(varlist, name, item)

    if len(varlist):
        section.append(varlist)

    return section

def _model_section(model):
    meta = model._meta
    title = u'Model: ' + meta.verbose_name.capitalize()
    props = SortedDict()

    if meta.verbose_name_plural != meta.verbose_name + u's':
        props['plural'] = meta.verbose_name_plural

    if model.__name__ != meta.verbose_name.capitalize():
        classname = etree.XML('<classname>{0}</classname>'.format(model.__name__))
        props['Python name'] = classname

    dbname = etree.XML('<database class="table">{0}</database>'.format(meta.db_table))
    props['database table'] = dbname

    if model.__doc__:
        props['programming description'] = model.__doc__

    section = _dict_section(title, props)
    section.set('{%s}id' % XML_NAMESPACE, _py_id(model))

    for f in meta.many_to_many + meta.local_fields:
        if isinstance(f, models.AutoField):
            continue
        section.append(_field_section(f))

    return section

def _field_section(field):
    title = u'Field: ' + field.verbose_name
    props = SortedDict()

    if field.attname != field.verbose_name:
        name = etree.XML('<code>{0}</code>'.format(field.attname))
        props['Python name'] = name
    
    # field Python type
    props['type'] = unicode(field.description % {'max_length': field.max_length})
    
    if field.rel:
        other_model = field.rel.to
        qualified_name = '{0}.{1}'.format(other_model.__module__, other_model.__name__)
        link_id = _py_id(other_model)
        link = etree.XML('<link linkend="{1}">{2} ({0})</link>'.format(
            qualified_name,
            link_id,
            other_model._meta.verbose_name.capitalize(),
        ))
        props['references'] = link

    # field SQL type
    props['database type'] = etree.XML(
        '<database class="datatype">{0}</database>'.format(
            unicode(field.db_type())
        )
    )
    
    # field choices
    if field.choices:
        choicelist = etree.Element(DOC + 'variablelist')
        for choice in field.choices:
            entry = etree.XML("""
                <varlistentry>
                  <term><literal>{0}</literal></term>
                  <listitem><simpara>{1}</simpara></listitem>
                </varlistentry>
            """.format(*choice))
            choicelist.append(entry)
        props['choices'] = choicelist
    
    if not field.has_default():
        val = etree.XML('<code>{0!r}</code>'.format(field.get_default()))
        props['default value'] = val

    if field.__doc__:
        props['programming description'] = field.__doc__

    if field.help_text:
        props['help-text'] = unicode(field.help_text)

    return _dict_section(title, props)

class Command(AppCommand):
    help = 'Outputs a docbook file documenting the app\'s fields.'

    def handle_app(self, app, **options):
        
        #section = etree.Element(DOC + 'section', version='5.0', nsmap=NS)
        section = etree.Element('section')
        sectiontitle = etree.SubElement(section, DOC + 'title')

        for c in models.get_models(app):
            m = c._meta
            
            if m.abstract:
                continue
            
            if not sectiontitle.text:
                sectiontitle.text = u'Model group: ' + m.app_label.capitalize()
            
            section.append(_model_section(c))
            
            continue

        print etree.tostring(section, xml_declaration=False, encoding='utf-8', pretty_print=True)


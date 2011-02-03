from django.test import TestCase

from django.template import Template, Context
from django.template.loader import render_to_string

from tabs import Tab, Tabs

class TabTestCase(TestCase):

    def setUp(self):
        self.template_text = "The tab's body. <b>Yadda Yadda.</b>"
        self.tab = Tab(
            'some_html_id',
            Template(self.template_text),
        )
    
    def test_tab(self):
        self.assertEqual(
            self.tab.render_js(),
            render_to_string("tab_js.js", {'tab': self.tab}),
        )
        self.assertEqual(
            self.tab.render_tab(),
            render_to_string("tab_li.html", {'tab': self.tab}),
        )
        self.assertEqual(
            self.tab.render_body(),
            self.template_text,
        )

class TabsTestCase(TestCase):
    
    def setUp(self):
        self.template_texts = (
            "The tab's body. <b>Yadda Yadda.</b>",
            "Another tabs body; some_var is {{ some_var }}",
        )
        self.tabs = (
            Tab(
                'some_html_id',
                Template(self.template_texts[0]),
            ),
            Tab(
                'some_other_id',
                Template(self.template_texts[1]),
                Context({'some_var': u'hoho'}),
                html_display= 'Some other ID<br>second line!!',
            ),
        )
            
    
    def test_tabs(self):
        
        t = Tabs(self.tabs)
        self.assertEqual(
            t.render(),
            render_to_string("tabs.html", {'tabs': self.tabs}),
        )
        

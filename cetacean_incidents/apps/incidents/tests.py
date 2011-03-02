from unittest import TestSuite, defaultTestLoader

import models
import forms
import templatetags

def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromModule(models.tests))
    suite.addTest(defaultTestLoader.loadTestsFromModule(forms.tests))
    suite.addTest(defaultTestLoader.loadTestsFromModule(templatetags.tests))
    return suite
    

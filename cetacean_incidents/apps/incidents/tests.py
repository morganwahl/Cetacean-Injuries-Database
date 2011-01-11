from unittest import TestSuite, defaultTestLoader

import models
import forms

def suite():
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromModule(models.tests))
    suite.addTest(defaultTestLoader.loadTestsFromModule(forms.tests))
    return suite
    

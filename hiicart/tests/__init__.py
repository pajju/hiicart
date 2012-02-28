import unittest

import comp, google, core, auditing, paypal_express

__tests__ = [comp, google, core, auditing, paypal_express]

def suite():
    suite = unittest.TestSuite()
    tests = []
    for test in __tests__:
        tl = unittest.TestLoader().loadTestsFromModule(test)
        tests += tl._tests
    suite._tests = tests
    return suite

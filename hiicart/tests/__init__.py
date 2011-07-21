import unittest

import comp, google, core, auditing, paypal_express_checkout

__tests__ = [comp, google, core, auditing, paypal_express_checkout]

def suite():
    suite = unittest.TestSuite()
    tests = []
    for test in __tests__:
        tl = unittest.TestLoader().loadTestsFromModule(test)
        tests += tl._tests
    suite._tests = tests
    return suite

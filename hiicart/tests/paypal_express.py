import base

class PaypalExpressCheckoutTestCase(base.HiiCartTestCase):
    """Paypal Express Checkout tests"""
    
    def test_submit(self):
        """Submit a cart to express checkout."""
        self.assertEquals(self.cart.state, "OPEN")
        result = self.cart.submit("paypal_express")
        self.assertEqual(result.type, "url")
        self.assertNotEquals(result.url, None)
        self.assertEquals(self.cart.state, "SUBMITTED")

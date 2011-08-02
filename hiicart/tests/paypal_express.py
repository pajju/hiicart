import base

STORE_SETTINGS = {
        'API_USERNAME': 'sdk-three_api1.sdk.com',
        'API_PASSWORD': 'QFZCWN5HZM8VBG7Q',
        'API_SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
        'RETURN_URL': 'http://goodsietest.com/return_url',
        'CANCEL_URL': 'http://goodsietest.com/cancel_url',
        'FINALIZE_URL': 'http://goodsietest.com/finalize_url',
        'COMPLETE_URL': 'http://goodsietest.com/complete_url'
        }

class PaypalExpressCheckoutTestCase(base.HiiCartTestCase):
    """Paypal Express Checkout tests"""

    def test_submit(self):
        """Submit a cart to express checkout."""
        self.cart.hiicart_settings.update(STORE_SETTINGS)
        self.assertEquals(self.cart.state, "OPEN")
        result = self.cart.submit("paypal_express", False, {'request': None})
        self.assertEqual(result.type, "url")
        self.assertNotEqual(result.url, None)
        self.assertEqual(self.cart.state, "SUBMITTED")

    def test_submit_recurring(self):
        """Test submitting a cart with recurring items to express checkout"""
        self.cart.hiicart_settings.update(STORE_SETTINGS)
        item = self._add_recurring_item()
        self.assertEquals(self.cart.state, "OPEN")
        result = self.cart.submit("paypal_express", False, {'request': None})
        self.assertEqual(result.type, "url")
        self.assertEqual(self.cart.state, "SUBMITTED")

        token = result.session_args['hiicart_paypal_express_token']
        self.assertNotEqual(token, None)

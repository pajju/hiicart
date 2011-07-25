from hiicart.gateway.paypal.ipn import PaypalIPN
from hiicart.gateway.paypal_express_checkout.settings import SETTINGS as default_settings

class PaypalExpressCheckoutIPN(PaypalIPN):
    """Paypal Express Checkout IPN handler"""

    def __init__(self, cart):
        """Inherit everything from PaypalIPN, except our cart and settings are different."""
        super(PaypalIPN, self).__init__('paypal_express_checkout', cart, default_settings)

        

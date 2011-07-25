import hmac
import random
import time

from django.template import Context, loader
from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, PaymentResult
from hiicart.gateway.authorizenet.forms import PaymentForm
#from hiicart.gateway.authorizenet.ipn import AuthorizeNetIPN
from hiicart.gateway.authorizenet.settings import SETTINGS as default_settings

POST_URL = "https://secure.authorize.net/gateway/transact.dll"
POST_TEST_URL = "https://test.authorize.net/gateway/transact.dll"


class AuthorizeNetGateway(PaymentGatewayBase):
    """Payment Gateway for Authorize.net."""

    def __init__(self, cart):
        super(AuthorizeNetGateway, self).__init__("authorizenet", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY", 
                                "MERCHANT_PRIVATE_KEY"])

    def _is_valid(self):
        """Return True if gateway is valid."""
        return True

    @property
    def submit_url(self):
        """Submit URL for current environment."""
        if self.settings["LIVE"]:
            return POST_URL
        else:
            return POST_TEST_URL

    def submit(self, collect_address=False, cart_settings_kwargs=None, submit=False):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return PaymentForm()

    def start_transaction(self, request):
        sequence = random.randint(10000, 99999)
        timestamp = int(time.time())
        hash_message = "%s^%s^%s^%s^" % (self.settings['MERCHANT_ID'],
                                         sequence, timestamp, self.cart.total)
        fp_hash = hmac.new(str(self.settings['MERCHANT_KEY']), hash_message)
        data = {'submit_url': self.submit_url,
                'x_fp_hash': fp_hash.hexdigest(),
                'x_fp_sequence': sequence,
                'x_invoice_num': self.cart.cart_uuid,
                'x_amount': self.cart.total,
                'x_login': self.settings['MERCHANT_ID'],
                'x_relay_url': request.build_absolute_uri(request.path)}
        return data

    def confirm_payment(self, request):
        """
        Confirms payment result with AuthorizeNet.
        """
        for key in request.POST:
            print key, request.POST[key]

import hmac
import random
import time

from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, PaymentResult
from hiicart.gateway.authorizenet.forms import PaymentForm
from hiicart.gateway.authorizenet.ipn import AuthorizeNetIPN
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

    def has_payment_result(self, request):
        return 'response_code' in request.GET

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
                                         timestamp, timestamp, self.cart.total)
        fp_hash = hmac.new(str(self.settings['MERCHANT_KEY']), hash_message)
        data = {'submit_url': self.submit_url,
                'return_url': request.build_absolute_uri(request.path),
                'cart_id': self.cart.cart_uuid,
                'x_invoice_num': timestamp,
                'x_fp_hash': fp_hash.hexdigest(),
                'x_fp_sequence': timestamp,
                'x_fp_timestamp': timestamp,
                'x_amount': self.cart.total,
                'x_login': self.settings['MERCHANT_ID'],
                'x_relay_url': self.settings['IPN_URL'],
                'x_relay_response': 'TRUE',
                'x_method': 'CC',
                'x_type': 'AUTH_CAPTURE',
                'x_version': '3.1'}
        if not self.settings['LIVE']:
            data['x_test_request'] = 'TRUE'
        return data

    def confirm_payment(self, request):
        """
        Confirms payment result with AuthorizeNet.
        """
        try:
            response_code = request.GET['response_code']
            response_text = request.GET['response_text']
        except:
            return PaymentResult(transaction_id=None, success=False,
                                 status=None, errors="Failed to process transaction")
        if response_code == "1":
            return PaymentResult(transaction_id=0, success=True,
                                 status="APPROVED")
        return PaymentResult(transaction_id=0, success=False, 
                             status="DECLINED", errors=response_text)
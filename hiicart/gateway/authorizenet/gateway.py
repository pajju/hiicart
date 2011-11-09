import hmac
import random
import time

from django.contrib.sessions.backends.db import SessionStore
from hiicart.models import PaymentResponse
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
        response = self.get_response()
        if response:
            return True
        return False

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
                'return_url': self.settings['RETURN_URL'] or request.build_absolute_uri(request.path),
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

    def get_response(self):
        """Get a payment result if it exists."""
        result = PaymentResponse.objects.filter(cart=self.cart)
        if result:
            return result[0]
        return None

    def set_response(self, data):
        """Store payment result for confirm_payment."""
        response = PaymentResponse()
        response.cart = self.cart
        response.response_code = data['x_response_reason_code']
        response.response_text = data['x_response_reason_text']
        response.save()

    def confirm_payment(self, request):
        """
        Confirms payment result with AuthorizeNet.
        """
        response = self.get_response()
        if response:
            if response.response_code == 1:
                result = PaymentResult('transaction', transaction_id=0, success=True,
                                       status="APPROVED")
            else:
                result = PaymentResult('transaction', transaction_id=0, success=False, 
                                       status="DECLINED", errors=response.response_text)
            response.delete()
        else:
            result = PaymentResult('transaction', transaction_id=None, success=False,
                                   status=None, errors="Failed to process transaction")
        return result

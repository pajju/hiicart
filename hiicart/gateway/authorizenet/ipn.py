import hashlib

from datetime import datetime
from decimal import Decimal
from hiicart.gateway.base import IPNBase, PaymentResult
from hiicart.gateway.authorizenet.settings import SETTINGS as default_settings
from hiicart.models import CART_TYPES

BRAINTREE_STATUS = {"PAID": ["settled"],
                    "PENDING": ["authorized", "authorizing",
                                "submitted_for_settlement"],
                    "FAILED": ["failed", "gateway_rejected",
                               "processor_declined", "settlement_failed"],
                    "CANCELLED": ["voided"]}


class AuthorizeNetIPN(IPNBase):
    """Authorize.net IPN Handler."""

    def __init__(self, cart):
        super(AuthorizeNetIPN, self).__init__("authorizenet", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY", 
                                "MERCHANT_PRIVATE_KEY"])

    def confirm_ipn_data(self, data):
        """
        Confirm the data coming from Authorize.net
        """
        message = "%s%s%s%s" % (self.settings['MERCHANT_PRIVATE_KEY'],
                                self.settings['MERCHANT_ID'],
                                self.settings['MERCHANT_KEY'],
                                self.cart.total)
        m = hashlib.md5(message)
        return data['x_MD5_Hash'] == m.hexdigest()

    def _record_payment(self, data):
        """Create a new payment record."""
        if not self.cart:
            return
        if data['x_response_code'] == '1':
            state = "PAID"
        elif data['x_response_code'] == '4':
            state = "PENDING"
        else:
            return
        payment = self.cart.payments.filter(transaction_id=data['x_trans_id'])
        if payment:
            if payment[0].state != state:
                payment[0].state = state
                payment[0].save()
                return payment[0]
        else:
            payment = self._create_payment(data['x_amount'],
                                           data['x_trans_id'], state)
            payment.save()
            return payment

    def accept_payment(self, data):
        """Save a new order using details from a transaction."""
        if not self.cart:
            return
        self.cart.ship_first_name = data["x_ship_to_first_name"] or self.cart.ship_first_name
        self.cart.ship_last_name = data["x_ship_to_last_name"] or self.cart.ship_last_name
        self.cart.ship_street1 = data["x_ship_to_address"] or self.cart.ship_street1
        #self.cart.ship_street2 = transaction.shipping["extended_address"] or self.cart.ship_street2
        self.cart.ship_city = data["x_ship_to_city"] or self.cart.ship_city
        self.cart.ship_state = data["x_ship_to_state"] or self.cart.ship_state
        self.cart.ship_postal_code = data["x_ship_to_zip"] or self.cart.ship_postal_code
        self.cart.ship_country = data["x_ship_to_country"] or self.cart.ship_country
        self.cart.bill_first_name = data["x_first_name"] or self.cart.bill_first_name
        self.cart.bill_last_name = data["x_last_name"] or self.cart.bill_last_name
        self.cart.bill_street1 = data["x_address"] or self.cart.bill_street1
        #self.cart.bill_street2 = transaction.billing["extended_address"] or self.cart.bill_street2
        self.cart.bill_city = data["x_city"] or self.cart.bill_city
        self.cart.bill_state = data["x_state"] or self.cart.bill_state
        self.cart.bill_postal_code = data["x_zip"] or self.cart.bill_postal_code
        self.cart.bill_country = data["x_country"] or self.cart.bill_country
        self.cart._cart_state = "SUBMITTED"
        self.cart.save()
        self._record_payment(data)
